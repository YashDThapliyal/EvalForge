from __future__ import annotations

from evalforge.agents.base import AgentFinal, ClaimType, FinalClaim, ToolCall
from evalforge.agents.replay import ReplayAgent
from evalforge.execution.episode import run_episode
from evalforge.scenarios.failure_directed import FailureDirectedScenarioGenerator
from evalforge.scenarios.fingerprint import fingerprint
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.scenarios.mutators import mutation_operator_names
from evalforge.scenarios.validator import ScenarioValidator


def test_all_bounded_mutation_operator_families_are_declared() -> None:
    assert set(mutation_operator_names()) == {
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
    }


def test_failure_directed_children_are_valid_material_deterministic_descendants() -> None:
    parent = build_manual_scenario("lost_confirmation", 0)
    episode = run_episode(
        parent,
        ReplayAgent(
            [ToolCall(tool_name="restart_service", arguments={"service_id": "payments-api"})],
            AgentFinal(
                status="resolved",
                summary="Restarted",
                claims=[
                    FinalClaim(
                        claim_type=ClaimType.SERVICE_HEALTH,
                        service_id="payments-api",
                        value="healthy",
                    )
                ],
            ),
        ),
    )
    assert episode.failure is not None
    first = FailureDirectedScenarioGenerator().generate(parent, episode.failure, count=6, seed=17)
    second = FailureDirectedScenarioGenerator().generate(parent, episode.failure, count=6, seed=17)
    assert first.stats.accepted == 6
    assert [fingerprint(item) for item in first.accepted] == [
        fingerprint(item) for item in second.accepted
    ]
    for child in first.accepted:
        assert child.parent_scenario_id == parent.scenario_id
        assert child.parent_failure_signature == episode.failure.canonical_signature
        assert child.source_method == "failure_directed"
        assert fingerprint(child) != fingerprint(parent)
        assert 1 <= len(child.metadata["mutations"]) <= 3  # type: ignore[arg-type]
        assert child.metadata["target_failure_signature"] == episode.failure.canonical_signature
        assert ScenarioValidator().validate(child).valid
