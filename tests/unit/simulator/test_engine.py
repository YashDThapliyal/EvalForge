from __future__ import annotations

from copy import deepcopy

from evalforge.domain.trace import OutcomeStatus
from evalforge.domain.world import Permission, default_world
from evalforge.simulator.engine import Simulator
from evalforge.simulator.faults import FaultKind, FaultSpec


def test_inspect_is_read_only_and_invalid_id_is_structured() -> None:
    world = default_world()
    before = world.model_copy(deep=True)
    simulator = Simulator(world)
    event = simulator.execute("operator", "inspect_service", {"service_id": "payments-api"})
    assert event.actual_outcome.status is OutcomeStatus.SUCCESS
    assert simulator.world == before

    missing = simulator.execute("operator", "inspect_service", {"service_id": "missing"})
    assert missing.actual_outcome.error_code == "SERVICE_NOT_FOUND"
    assert missing.visible_observation.model_dump().keys() == {"status", "message", "data"}


def test_permission_denial_precedes_mutation() -> None:
    world = default_world()
    world.permissions["viewer"] = [Permission.READ_SERVICE]
    simulator = Simulator(world)
    before_hash = simulator.state_hash
    event = simulator.execute("viewer", "restart_service", {"service_id": "payments-api"})
    assert not event.permission_decision.allowed
    assert event.actual_outcome.error_code == "PERMISSION_DENIED"
    assert event.state_before_hash == event.state_after_hash == before_hash
    assert event.state_diff.changes == []


def test_mutations_are_scoped_and_idempotent_where_declared() -> None:
    world = default_world()
    world.services["payments-api"].health = "unhealthy"
    world.services["payments-api"].current_version = "v2"
    simulator = Simulator(world)
    other = deepcopy(simulator.world.services["checkout-api"])

    rollback = simulator.execute(
        "operator",
        "rollback_deployment",
        {"service_id": "payments-api", "target_version": "v1", "idempotency_key": "rb-1"},
    )
    assert rollback.actual_outcome.status is OutcomeStatus.SUCCESS
    assert simulator.world.services["payments-api"].current_version == "v1"
    assert simulator.world.services["payments-api"].health == "healthy"
    assert simulator.world.services["checkout-api"] == other

    simulator.execute(
        "operator",
        "update_config",
        {"service_id": "payments-api", "key": "timeout", "value": 60},
    )
    assert simulator.world.services["payments-api"].config["timeout"] == 60
    assert set(simulator.world.services["payments-api"].config) == {"timeout", "retries"}

    first = simulator.execute(
        "operator",
        "open_incident",
        {"service_id": "payments-api", "severity": "high", "summary": "Degraded"},
    )
    second = simulator.execute(
        "operator",
        "open_incident",
        {"service_id": "payments-api", "severity": "high", "summary": "Degraded"},
    )
    assert first.side_effect_id != second.side_effect_id
    assert len(simulator.world.incidents) == 2

    keyed = Simulator(default_world())
    keyed.execute(
        "operator",
        "open_incident",
        {
            "service_id": "payments-api",
            "severity": "high",
            "summary": "Degraded",
            "idempotency_key": "inc-1",
        },
    )
    replay = keyed.execute(
        "operator",
        "open_incident",
        {
            "service_id": "payments-api",
            "severity": "high",
            "summary": "Degraded",
            "idempotency_key": "inc-1",
        },
    )
    assert len(keyed.world.incidents) == 1
    assert replay.actual_outcome.data["idempotent_replay"] is True


def test_faults_separate_actual_outcome_from_observation() -> None:
    lost = FaultSpec(
        fault_id="lost-1",
        kind=FaultKind.CONFIRMATION_LOST,
        tool_name="restart_service",
        occurrence=1,
    )
    world = default_world()
    world.services["payments-api"].health = "unhealthy"
    simulator = Simulator(world, [lost])
    event = simulator.execute("operator", "restart_service", {"service_id": "payments-api"})
    assert event.actual_outcome.status is OutcomeStatus.SUCCESS
    assert simulator.world.services["payments-api"].health == "healthy"
    assert event.visible_observation.status == "uncertain"
    visible = event.visible_observation.model_dump()
    assert "actual_outcome" not in visible and "fault_ids_applied" not in visible

    ambiguous = Simulator(
        default_world(),
        [
            FaultSpec(
                fault_id="amb-1",
                kind=FaultKind.AMBIGUOUS_RESPONSE,
                tool_name="rollback_deployment",
                occurrence=1,
            )
        ],
    )
    before = ambiguous.state_hash
    event = ambiguous.execute(
        "operator", "rollback_deployment", {"service_id": "payments-api"}
    )
    assert event.actual_outcome.status is OutcomeStatus.FAILURE
    assert event.visible_observation.status == "uncertain"
    assert ambiguous.state_hash == before


def test_seeded_fault_replay_and_diffs_are_stable() -> None:
    faults = [
        FaultSpec(
            fault_id="lost-1",
            kind=FaultKind.CONFIRMATION_LOST,
            tool_name="restart_service",
            occurrence=1,
        )
    ]
    traces = []
    for _ in range(2):
        simulator = Simulator(default_world(), faults, seed=19)
        traces.append(
            simulator.execute(
                "operator",
                "restart_service",
                {"service_id": "payments-api", "idempotency_key": "r-1"},
            ).model_dump(mode="json", exclude={"call_id"})
        )
    assert traces[0] == traces[1]
    assert traces[0]["state_diff"]["changes"]

