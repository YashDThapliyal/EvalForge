"""Bounded data-only mutation operators for failure-directed children."""

from __future__ import annotations

from evalforge.domain.scenario import ScenarioSpec
from evalforge.domain.world import MonitoringObservation

OPERATORS = (
    "change_service_names",
    "add_distractor_service",
    "alter_permissions",
    "change_fault_observation_mode",
    "move_failure_to_different_tool",
    "make_operation_non_idempotent",
    "add_conflicting_monitoring_evidence",
    "change_confirmation_mode",
    "vary_root_cause",
    "combine_primary_secondary",
)


def mutation_operator_names() -> tuple[str, ...]:
    """Return every contract-supported controlled mutation family."""

    return OPERATORS


def add_distractor_service(scenario: ScenarioSpec, index: int) -> None:
    """Add a similarly named protected service without changing target semantics."""

    target_id = scenario.success_contract.predicates[0].service_id
    target = scenario.initial_world.services[target_id]
    distractor_id = f"{target_id}-shadow-{index}"
    distractor = target.model_copy(deep=True)
    distractor.service_id = distractor_id
    distractor.health = "healthy"
    distractor.current_version = distractor.known_good_version
    distractor.last_deployment_id = None
    scenario.initial_world.services[distractor_id] = distractor
    scenario.initial_world.logs[distractor_id] = ["Shadow service operating normally"]
    scenario.initial_world.monitoring.append(
        MonitoringObservation(source="primary", service_id=distractor_id, health="healthy")
    )


def vary_root_cause(scenario: ScenarioSpec, index: int) -> None:
    """Vary hidden causal evidence while preserving the required reasoning pattern."""

    target_id = scenario.success_contract.predicates[0].service_id
    scenario.initial_world.logs[target_id].append(
        f"ERROR variant root cause marker {index}: dependency saturation"
    )
    scenario.initial_world.services[target_id].config["diagnostic_variant"] = index


def apply_safe_mutation(scenario: ScenarioSpec, index: int) -> list[str]:
    """Apply one or two oracle-safe material mutations selected deterministically."""

    choice = index % 3
    if choice == 0:
        add_distractor_service(scenario, index)
        return ["add_distractor_service"]
    if choice == 1:
        vary_root_cause(scenario, index)
        return ["vary_root_cause"]
    add_distractor_service(scenario, index)
    vary_root_cause(scenario, index)
    return ["combine_primary_secondary", "add_distractor_service"]
