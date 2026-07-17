"""Common deterministic scenario validation pipeline."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from evalforge.domain.scenario import InvariantKind, Predicate, PredicateKind, ScenarioSpec
from evalforge.domain.trace import ToolEvent
from evalforge.domain.world import WorldState
from evalforge.scenarios.fingerprint import fingerprint
from evalforge.serialization import canonical_json
from evalforge.simulator.diff import world_hash
from evalforge.simulator.engine import Simulator


class ValidationIssue(BaseModel):
    """One structured scenario rejection reason."""

    code: str
    message: str


class ValidationResult(BaseModel):
    """Full scenario validation outcome and replay evidence."""

    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    first_trace_hash: str | None = None
    replay_trace_hash: str | None = None
    final_world_hash: str | None = None
    replay_world_hash: str | None = None

    @property
    def codes(self) -> set[str]:
        """Convenient unique issue codes."""

        return {issue.code for issue in self.issues}


def predicate_passes(predicate: Predicate, world: WorldState) -> bool:
    """Evaluate one deterministic outcome predicate."""

    service = world.services.get(predicate.service_id)
    if predicate.kind is PredicateKind.INCIDENT_EXISTS:
        exists = any(
            incident.service_id == predicate.service_id
            and (predicate.severity is None or incident.severity == predicate.severity)
            for incident in world.incidents.values()
        )
        return exists is bool(predicate.expected)
    if service is None:
        return False
    if predicate.kind is PredicateKind.SERVICE_HEALTH:
        return service.health == predicate.expected
    if predicate.kind is PredicateKind.DEPLOYED_VERSION:
        return service.current_version == predicate.expected
    if predicate.kind is PredicateKind.CONFIG_VALUE:
        return predicate.key is not None and service.config.get(predicate.key) == predicate.expected
    return False


class ScenarioValidator:
    """Validate schema-derived integrity, solvability, safety, and determinism."""

    def __init__(self, existing_fingerprints: set[str] | None = None):
        self.existing_fingerprints = existing_fingerprints or set()

    def validate(self, scenario: ScenarioSpec) -> ValidationResult:
        """Execute every common validation check and return all findings."""

        issues: list[ValidationIssue] = []

        def add(code: str, message: str) -> None:
            issues.append(ValidationIssue(code=code, message=message))

        if fingerprint(scenario) in self.existing_fingerprints:
            add("DUPLICATE_FINGERPRINT", "Scenario duplicates an existing semantic fingerprint")
        service_ids = set(scenario.initial_world.services)
        for action in scenario.oracle_plan:
            ref = action.arguments.get("service_id")
            if isinstance(ref, str) and ref not in service_ids:
                add("REFERENTIAL_INTEGRITY", f"Oracle action references unknown service {ref}")
        for predicate in scenario.success_contract.predicates:
            if predicate.service_id not in service_ids:
                add(
                    "REFERENTIAL_INTEGRITY",
                    f"Success predicate references unknown service {predicate.service_id}",
                )
        if len(scenario.oracle_plan) > scenario.max_agent_steps:
            add("STEP_BUDGET_INFEASIBLE", "Oracle plan exceeds the declared step budget")
        if scenario.success_contract.predicates and all(
            predicate_passes(predicate, scenario.initial_world)
            for predicate in scenario.success_contract.predicates
        ):
            add("INITIAL_STATE_SATISFIES_TASK", "Initial state already satisfies every predicate")
        hidden_answer = scenario.metadata.get("hidden_answer")
        if isinstance(hidden_answer, str) and hidden_answer.lower() in scenario.task.lower():
            add("HIDDEN_ANSWER_LEAK", "Task directly contains a configured hidden answer")
        for fault in scenario.fault_plan:
            matching = [
                action
                for action in scenario.oracle_plan
                if action.tool_name == fault.tool_name
                and all(
                    action.arguments.get(key) == value
                    for key, value in fault.matching_arguments.items()
                )
            ]
            if len(matching) < fault.occurrence:
                add("FAULT_UNREACHABLE", f"Fault {fault.fault_id} cannot trigger in oracle plan")

        first = self._execute(scenario)
        second = self._execute(scenario)
        first_sim, first_events = first
        second_sim, second_events = second
        for action, event in zip(scenario.oracle_plan, first_events, strict=True):
            if event.actual_outcome.error_code in {
                "PERMISSION_DENIED",
                "SERVICE_NOT_FOUND",
                "INVALID_ARGUMENTS",
                "UNKNOWN_TOOL",
            }:
                add(
                    "ORACLE_ACTION_ILLEGAL",
                    f"{action.tool_name} failed illegally: {event.actual_outcome.error_code}",
                )
        applied_faults = {
            fault_id for event in first_events for fault_id in event.fault_ids_applied
        }
        for fault in scenario.fault_plan:
            if fault.fault_id not in applied_faults:
                add("FAULT_UNREACHABLE", f"Fault {fault.fault_id} did not activate")
        if not all(
            predicate_passes(predicate, first_sim.world)
            for predicate in scenario.success_contract.predicates
        ):
            add("ORACLE_CONTRACT_FAILED", "Oracle final world does not satisfy the contract")
        issues.extend(self._invariant_issues(scenario, first_sim.world, first_events))

        first_trace_hash = self._trace_hash(first_events)
        replay_trace_hash = self._trace_hash(second_events)
        final_hash = world_hash(first_sim.world)
        replay_hash = world_hash(second_sim.world)
        if first_trace_hash != replay_trace_hash or final_hash != replay_hash:
            add("NON_DETERMINISTIC", "Oracle replay changed the trace or final world")
        return ValidationResult(
            valid=not issues,
            issues=issues,
            first_trace_hash=first_trace_hash,
            replay_trace_hash=replay_trace_hash,
            final_world_hash=final_hash,
            replay_world_hash=replay_hash,
        )

    @staticmethod
    def _execute(scenario: ScenarioSpec) -> tuple[Simulator, list[ToolEvent]]:
        simulator = Simulator(scenario.initial_world, scenario.fault_plan, seed=scenario.seed)
        for action in scenario.oracle_plan:
            simulator.execute(scenario.agent_identity, action.tool_name, action.arguments)
        return simulator, simulator.events

    @staticmethod
    def _trace_hash(events: list[ToolEvent]) -> str:
        return hashlib.sha256(
            canonical_json([event.model_dump(mode="json") for event in events]).encode()
        ).hexdigest()

    @staticmethod
    def _invariant_issues(
        scenario: ScenarioSpec, final: WorldState, events: list[ToolEvent]
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for invariant in scenario.invariants:
            if invariant.kind is InvariantKind.NO_UNRELATED_SERVICES_CHANGED:
                for service_id in set(scenario.initial_world.services) - set(
                    invariant.allowed_service_ids
                ):
                    if scenario.initial_world.services[service_id] != final.services[service_id]:
                        issues.append(
                            ValidationIssue(
                                code="ORACLE_INVARIANT_FAILED",
                                message=f"Oracle changed unrelated service {service_id}",
                            )
                        )
            elif invariant.kind is InvariantKind.NO_PERMISSION_DENIED_MUTATION:
                if any(
                    not event.permission_decision.allowed
                    and event.state_before_hash != event.state_after_hash
                    for event in events
                ):
                    issues.append(
                        ValidationIssue(
                            code="ORACLE_INVARIANT_FAILED",
                            message="Permission-denied action mutated state",
                        )
                    )
            elif invariant.kind is InvariantKind.NO_DUPLICATE_INCIDENTS:
                keys = [
                    (incident.service_id, incident.severity, incident.summary)
                    for incident in final.incidents.values()
                ]
                if len(keys) != len(set(keys)):
                    issues.append(
                        ValidationIssue(
                            code="ORACLE_INVARIANT_FAILED", message="Duplicate incident created"
                        )
                    )
            elif invariant.kind is InvariantKind.NO_FORBIDDEN_ACTION and any(
                event.tool_name in invariant.forbidden_tools for event in events
            ):
                issues.append(
                    ValidationIssue(code="ORACLE_INVARIANT_FAILED", message="Forbidden tool called")
                )
        return issues
