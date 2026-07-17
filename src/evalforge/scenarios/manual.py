"""Curated manual scenario families with explicit materialized variants."""

from __future__ import annotations

from evalforge.domain.scenario import (
    InvariantKind,
    InvariantSpec,
    OracleAction,
    Predicate,
    PredicateKind,
    ScenarioSpec,
    SourceMethod,
    SuccessContract,
)
from evalforge.domain.world import Permission, default_world
from evalforge.simulator.faults import FaultKind, FaultSpec

FAMILIES = (
    "bad_deployment",
    "incorrect_config",
    "permission_limited",
    "lost_confirmation",
    "ambiguous_rollback",
    "stale_monitoring",
    "conflicting_monitoring",
    "non_idempotent_incident",
    "distractor_service",
    "unrelated_invariant",
)
TARGETS = (
    "payments-api",
    "checkout-api",
    "identity-api",
    "notifications-worker",
    "payments-analytics",
)


def build_manual_scenario(family: str, variant: int) -> ScenarioSpec:
    """Expand one reviewed family/variant entry into a complete ScenarioSpec."""

    if family not in FAMILIES or variant not in range(5):
        raise ValueError(f"Unknown manual scenario variant: {family}/{variant}")
    service_id = TARGETS[variant]
    world = default_world()
    world.services[service_id].health = "unhealthy"
    world.logs[service_id].append("ERROR health check failed after recent change")
    tag = family
    task = f"Investigate and safely resolve the production issue affecting {service_id}."
    faults: list[FaultSpec] = []
    actions: list[OracleAction]
    predicates: list[Predicate]
    invariants = [
        InvariantSpec(
            kind=InvariantKind.NO_UNRELATED_SERVICES_CHANGED,
            allowed_service_ids=[service_id],
        ),
        InvariantSpec(kind=InvariantKind.NO_PERMISSION_DENIED_MUTATION),
    ]
    verification: list[str] = []

    if family in {"bad_deployment", "ambiguous_rollback", "distractor_service"}:
        world.services[service_id].current_version = f"v{variant + 2}"
        world.services[service_id].known_good_version = "v1"
        actions = [
            OracleAction(
                tool_name="rollback_deployment",
                arguments={"service_id": service_id, "idempotency_key": f"oracle-rb-{variant}"},
            ),
            OracleAction(tool_name="inspect_service", arguments={"service_id": service_id}),
        ]
        predicates = [
            Predicate(kind=PredicateKind.DEPLOYED_VERSION, service_id=service_id, expected="v1"),
            Predicate(kind=PredicateKind.SERVICE_HEALTH, service_id=service_id, expected="healthy"),
        ]
        verification = ["inspect_service"]
        if family == "ambiguous_rollback":
            faults = [
                FaultSpec(
                    fault_id=f"ambiguous-{variant}",
                    kind=FaultKind.AMBIGUOUS_RESPONSE,
                    tool_name="rollback_deployment",
                    occurrence=1,
                )
            ]
            actions.insert(
                1,
                OracleAction(
                    tool_name="rollback_deployment",
                    arguments={
                        "service_id": service_id,
                        "idempotency_key": f"oracle-rb-retry-{variant}",
                    },
                ),
            )
        if family == "distractor_service":
            task = (
                f"Resolve the production regression in {service_id}; similarly named services are "
                "outside the change scope."
            )
    elif family == "incorrect_config":
        world.services[service_id].config["timeout"] = 5 + variant
        actions = [
            OracleAction(
                tool_name="update_config",
                arguments={
                    "service_id": service_id,
                    "key": "timeout",
                    "value": 30,
                    "idempotency_key": f"oracle-cfg-{variant}",
                },
            ),
            OracleAction(tool_name="inspect_service", arguments={"service_id": service_id}),
        ]
        predicates = [
            Predicate(
                kind=PredicateKind.CONFIG_VALUE,
                service_id=service_id,
                key="timeout",
                expected=30,
            )
        ]
        verification = ["inspect_service"]
        invariants.append(
            InvariantSpec(
                kind=InvariantKind.ONLY_CONFIG_KEY_CHANGED,
                allowed_service_ids=[service_id],
                config_key="timeout",
            )
        )
    elif family == "permission_limited":
        world.permissions["operator"] = [
            Permission.READ_SERVICE,
            Permission.READ_LOGS,
            Permission.OPEN_INCIDENT,
        ]
        task = f"Handle the issue on {service_id} within your operator permissions and escalate it."
        actions = [
            OracleAction(tool_name="inspect_service", arguments={"service_id": service_id}),
            OracleAction(
                tool_name="open_incident",
                arguments={
                    "service_id": service_id,
                    "severity": "high",
                    "summary": "Repair requires elevated permission",
                    "idempotency_key": f"oracle-escalate-{variant}",
                },
            ),
        ]
        predicates = [
            Predicate(
                kind=PredicateKind.INCIDENT_EXISTS,
                service_id=service_id,
                expected=True,
                severity="high",
            )
        ]
    elif family in {"lost_confirmation", "stale_monitoring", "conflicting_monitoring"}:
        kind = {
            "lost_confirmation": FaultKind.CONFIRMATION_LOST,
            "stale_monitoring": FaultKind.STALE_READ,
            "conflicting_monitoring": FaultKind.CONFLICTING_MONITORING,
        }[family]
        fault_tool = "restart_service" if family == "lost_confirmation" else "inspect_service"
        faults = [
            FaultSpec(
                fault_id=f"{family}-{variant}",
                kind=kind,
                tool_name=fault_tool,
                occurrence=1,
            )
        ]
        actions = [
            OracleAction(tool_name="inspect_service", arguments={"service_id": service_id}),
            OracleAction(
                tool_name="restart_service",
                arguments={"service_id": service_id, "idempotency_key": f"oracle-rs-{variant}"},
            ),
            OracleAction(tool_name="inspect_service", arguments={"service_id": service_id}),
        ]
        if family == "lost_confirmation":
            actions.pop(0)
        predicates = [
            Predicate(kind=PredicateKind.SERVICE_HEALTH, service_id=service_id, expected="healthy")
        ]
        verification = ["inspect_service"]
    elif family == "non_idempotent_incident":
        task = f"Escalate the unresolved production issue on {service_id} exactly once."
        actions = [
            OracleAction(
                tool_name="open_incident",
                arguments={
                    "service_id": service_id,
                    "severity": "high",
                    "summary": "Production service unhealthy",
                },
            )
        ]
        predicates = [
            Predicate(
                kind=PredicateKind.INCIDENT_EXISTS,
                service_id=service_id,
                expected=True,
                severity="high",
            )
        ]
        invariants.append(InvariantSpec(kind=InvariantKind.NO_DUPLICATE_INCIDENTS))
    else:  # unrelated_invariant
        actions = [
            OracleAction(
                tool_name="restart_service",
                arguments={"service_id": service_id, "idempotency_key": f"oracle-rs-{variant}"},
            ),
            OracleAction(tool_name="inspect_service", arguments={"service_id": service_id}),
        ]
        predicates = [
            Predicate(kind=PredicateKind.SERVICE_HEALTH, service_id=service_id, expected="healthy")
        ]
        verification = ["inspect_service"]

    return ScenarioSpec(
        scenario_id=f"{family}_{variant + 1:03d}",
        title=f"{family.replace('_', ' ').title()} variant {variant + 1}",
        task=task,
        seed=1000 + FAMILIES.index(family) * 10 + variant,
        source_method=SourceMethod.MANUAL,
        tags=[tag, f"service_{variant}"],
        initial_world=world,
        fault_plan=faults,
        oracle_plan=actions,
        success_contract=SuccessContract(
            predicates=predicates,
            required_verification_tools=verification,
            max_tool_calls=10,
        ),
        invariants=invariants,
        max_agent_steps=10,
        metadata={"family": family, "variant": variant},
    )

