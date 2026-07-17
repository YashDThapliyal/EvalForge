"""Tool transition engine with strict truth/observation separation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from evalforge.domain.trace import (
    ActualOutcome,
    OutcomeStatus,
    ToolEvent,
    ToolObservation,
)
from evalforge.domain.world import Deployment, Incident, JsonValue, WorldState
from evalforge.simulator.diff import state_diff, world_hash
from evalforge.simulator.faults import FaultKind, FaultSpec
from evalforge.simulator.permissions import decide_permission

Transition = Callable[[str, dict[str, JsonValue], str], tuple[ActualOutcome, str | None]]


class Simulator:
    """Execute auditable operations against an isolated local world copy."""

    def __init__(self, world: WorldState, faults: list[FaultSpec] | None = None, seed: int = 0):
        self.world = world.model_copy(deep=True)
        self.faults = [fault.model_copy(deep=True) for fault in faults or []]
        self.seed = seed
        self.events: list[ToolEvent] = []
        self._occurrences: Counter[str] = Counter()
        self._transitions: dict[str, Transition] = {
            "inspect_service": self._inspect_service,
            "read_logs": self._read_logs,
            "restart_service": self._restart_service,
            "rollback_deployment": self._rollback_deployment,
            "update_config": self._update_config,
            "open_incident": self._open_incident,
        }

    @property
    def state_hash(self) -> str:
        """Current canonical state hash."""

        return world_hash(self.world)

    @staticmethod
    def compute_state_hash(world: WorldState) -> str:
        """Hash a supplied world with the simulator's canonical algorithm."""

        return world_hash(world)

    def execute(self, actor_id: str, tool_name: str, arguments: dict[str, JsonValue]) -> ToolEvent:
        """Authorize, execute truth, transform observation, and record one event."""

        step = len(self.events) + 1
        call_id = f"evt-{step:04d}"
        before = self.world.model_copy(deep=True)
        before_hash = world_hash(before)
        decision = decide_permission(self.world, actor_id, tool_name)
        side_effect_id: str | None = None
        applied: list[FaultSpec] = []

        if not decision.allowed:
            actual = ActualOutcome(
                status=OutcomeStatus.FAILURE,
                message=decision.reason,
                error_code="PERMISSION_DENIED",
            )
        elif tool_name not in self._transitions:
            actual = ActualOutcome(
                status=OutcomeStatus.FAILURE,
                message=f"Unknown tool: {tool_name}",
                error_code="UNKNOWN_TOOL",
            )
        else:
            self._occurrences[tool_name] += 1
            occurrence = self._occurrences[tool_name]
            applied = [
                fault for fault in self.faults if fault.matches(tool_name, arguments, occurrence)
            ]
            blocking = next(
                (
                    fault
                    for fault in applied
                    if fault.kind
                    in {
                        FaultKind.ACTION_FAILS,
                        FaultKind.AMBIGUOUS_RESPONSE,
                        FaultKind.MISLEADING_SUCCESS_RESPONSE,
                        FaultKind.TRANSIENT_FAILURE_THEN_SUCCESS,
                    }
                ),
                None,
            )
            if blocking is not None:
                actual = ActualOutcome(
                    status=OutcomeStatus.FAILURE,
                    message=f"Injected {blocking.kind.value} prevented the action",
                    error_code=blocking.kind.value,
                )
            else:
                actual, side_effect_id = self._transitions[tool_name](actor_id, arguments, call_id)
                if any(fault.kind is FaultKind.PARTIAL_SIDE_EFFECT for fault in applied):
                    actual = actual.model_copy(
                        update={
                            "status": OutcomeStatus.PARTIAL,
                            "message": f"Partial side effect: {actual.message}",
                        }
                    )
        observation = self._visible_observation(actual, applied)
        after_hash = world_hash(self.world)
        event = ToolEvent(
            call_id=call_id,
            step_index=step,
            tool_name=tool_name,
            arguments=arguments,
            actor_id=actor_id,
            permission_decision=decision,
            actual_outcome=actual,
            visible_observation=observation,
            state_before_hash=before_hash,
            state_after_hash=after_hash,
            state_diff=state_diff(before, self.world),
            side_effect_id=side_effect_id,
            fault_ids_applied=[fault.fault_id for fault in applied],
        )
        self.events.append(event)
        return event

    def _visible_observation(
        self, actual: ActualOutcome, faults: list[FaultSpec]
    ) -> ToolObservation:
        kind = faults[0].kind if faults else None
        if kind in {FaultKind.CONFIRMATION_LOST, FaultKind.AMBIGUOUS_RESPONSE}:
            return ToolObservation(
                status="uncertain", message="The operation result could not be confirmed."
            )
        if kind is FaultKind.MISLEADING_SUCCESS_RESPONSE:
            return ToolObservation(status="success", message="Operation completed successfully.")
        if kind is FaultKind.STALE_READ:
            return ToolObservation(
                status="success", message="Cached service observation", data={"health": "unhealthy"}
            )
        if kind is FaultKind.CONFLICTING_MONITORING:
            return ToolObservation(
                status="uncertain",
                message="Monitoring sources disagree.",
                data={"primary": "healthy", "secondary": "unhealthy"},
            )
        return ToolObservation(
            status=actual.status.value,
            message=actual.message,
            data=actual.data,
        )

    def _service(self, arguments: dict[str, JsonValue]) -> tuple[str, object | None]:
        raw = arguments.get("service_id")
        service_id = raw if isinstance(raw, str) else ""
        return service_id, self.world.services.get(service_id)

    def _inspect_service(
        self, actor_id: str, arguments: dict[str, JsonValue], call_id: str
    ) -> tuple[ActualOutcome, str | None]:
        del actor_id, call_id
        service_id, service = self._service(arguments)
        if service is None:
            return self._missing_service(service_id), None
        model = self.world.services[service_id]
        return (
            ActualOutcome(
                status=OutcomeStatus.SUCCESS,
                message=f"Inspected {service_id}",
                data={
                    "service_id": service_id,
                    "health": model.health,
                    "current_version": model.current_version,
                    "config": model.config,
                },
            ),
            None,
        )

    def _read_logs(
        self, actor_id: str, arguments: dict[str, JsonValue], call_id: str
    ) -> tuple[ActualOutcome, str | None]:
        del actor_id, call_id
        service_id, service = self._service(arguments)
        if service is None:
            return self._missing_service(service_id), None
        raw_limit = arguments.get("limit", 20)
        limit = raw_limit if isinstance(raw_limit, int) else 20
        return (
            ActualOutcome(
                status=OutcomeStatus.SUCCESS,
                message=f"Read logs for {service_id}",
                data={"logs": self.world.logs.get(service_id, [])[-limit:]},
            ),
            None,
        )

    def _restart_service(
        self, actor_id: str, arguments: dict[str, JsonValue], call_id: str
    ) -> tuple[ActualOutcome, str | None]:
        del actor_id
        service_id, service = self._service(arguments)
        if service is None:
            return self._missing_service(service_id), None
        replay = self._idempotent_replay("restart_service", arguments)
        if replay is not None:
            return replay
        self.world.services[service_id].health = "healthy"
        side_effect_id = f"restart-{call_id}"
        self._record_effect(side_effect_id, "restart_service", service_id, arguments)
        return self._success("Service restarted", side_effect_id, arguments)

    def _rollback_deployment(
        self, actor_id: str, arguments: dict[str, JsonValue], call_id: str
    ) -> tuple[ActualOutcome, str | None]:
        del actor_id
        service_id, service_obj = self._service(arguments)
        if service_obj is None:
            return self._missing_service(service_id), None
        replay = self._idempotent_replay("rollback_deployment", arguments)
        if replay is not None:
            return replay
        service = self.world.services[service_id]
        raw_target = arguments.get("target_version")
        target = raw_target if isinstance(raw_target, str) else service.known_good_version
        old = service.current_version
        service.current_version = target
        service.health = "healthy"
        deployment_id = f"dep-{service_id}-rollback-{call_id}"
        self.world.deployments[deployment_id] = Deployment(
            deployment_id=deployment_id,
            service_id=service_id,
            from_version=old,
            to_version=target,
            status="rolled_back",
            created_at_step=len(self.events) + 1,
            rollback_target=target,
        )
        service.last_deployment_id = deployment_id
        side_effect_id = f"rollback-{call_id}"
        self._record_effect(side_effect_id, "rollback_deployment", service_id, arguments)
        return self._success("Deployment rolled back", side_effect_id, arguments)

    def _update_config(
        self, actor_id: str, arguments: dict[str, JsonValue], call_id: str
    ) -> tuple[ActualOutcome, str | None]:
        del actor_id
        service_id, service = self._service(arguments)
        if service is None:
            return self._missing_service(service_id), None
        key = arguments.get("key")
        if not isinstance(key, str) or "value" not in arguments:
            return self._invalid_arguments("key and value are required"), None
        replay = self._idempotent_replay("update_config", arguments)
        if replay is not None:
            return replay
        self.world.services[service_id].config[key] = arguments["value"]
        side_effect_id = f"config-{call_id}"
        self._record_effect(side_effect_id, "update_config", service_id, arguments)
        return self._success("Configuration updated", side_effect_id, arguments)

    def _open_incident(
        self, actor_id: str, arguments: dict[str, JsonValue], call_id: str
    ) -> tuple[ActualOutcome, str | None]:
        service_id, service = self._service(arguments)
        if service is None:
            return self._missing_service(service_id), None
        severity = arguments.get("severity")
        summary = arguments.get("summary")
        if not isinstance(severity, str) or not isinstance(summary, str):
            return self._invalid_arguments("severity and summary are required"), None
        replay = self._idempotent_replay("open_incident", arguments)
        if replay is not None:
            return replay
        incident_id = f"inc-{len(self.world.incidents) + 1:04d}"
        side_effect_id = f"incident-{call_id}"
        self.world.incidents[incident_id] = Incident(
            incident_id=incident_id,
            service_id=service_id,
            severity=severity,
            summary=summary,
            opened_by=actor_id,
            linked_action_ids=[side_effect_id],
        )
        self._record_effect(side_effect_id, "open_incident", service_id, arguments)
        outcome = ActualOutcome(
            status=OutcomeStatus.SUCCESS,
            message="Incident opened",
            data={"incident_id": incident_id, "side_effect_id": side_effect_id},
        )
        self._save_idempotency("open_incident", arguments, side_effect_id)
        return outcome, side_effect_id

    def _record_effect(
        self,
        side_effect_id: str,
        tool_name: str,
        service_id: str,
        arguments: dict[str, JsonValue],
    ) -> None:
        self.world.action_history.append(side_effect_id)
        self.world.side_effects[side_effect_id] = {
            "tool_name": tool_name,
            "service_id": service_id,
        }
        self._save_idempotency(tool_name, arguments, side_effect_id)

    def _idempotent_replay(
        self, tool_name: str, arguments: dict[str, JsonValue]
    ) -> tuple[ActualOutcome, str | None] | None:
        key = arguments.get("idempotency_key")
        if not isinstance(key, str):
            return None
        side_effect_id = self.world.idempotency_records.get(f"{tool_name}:{key}")
        if side_effect_id is None:
            return None
        return (
            ActualOutcome(
                status=OutcomeStatus.SUCCESS,
                message="Idempotent replay; prior effect returned",
                data={"idempotent_replay": True, "side_effect_id": side_effect_id},
            ),
            side_effect_id,
        )

    def _save_idempotency(
        self, tool_name: str, arguments: dict[str, JsonValue], side_effect_id: str
    ) -> None:
        key = arguments.get("idempotency_key")
        if isinstance(key, str):
            self.world.idempotency_records[f"{tool_name}:{key}"] = side_effect_id

    @staticmethod
    def _success(
        message: str, side_effect_id: str, arguments: dict[str, JsonValue]
    ) -> tuple[ActualOutcome, str | None]:
        return (
            ActualOutcome(
                status=OutcomeStatus.SUCCESS,
                message=message,
                data={"side_effect_id": side_effect_id, "idempotent_replay": False},
            ),
            side_effect_id,
        )

    @staticmethod
    def _missing_service(service_id: str) -> ActualOutcome:
        return ActualOutcome(
            status=OutcomeStatus.FAILURE,
            message=f"Service not found: {service_id}",
            error_code="SERVICE_NOT_FOUND",
        )

    @staticmethod
    def _invalid_arguments(message: str) -> ActualOutcome:
        return ActualOutcome(
            status=OutcomeStatus.FAILURE,
            message=message,
            error_code="INVALID_ARGUMENTS",
        )
