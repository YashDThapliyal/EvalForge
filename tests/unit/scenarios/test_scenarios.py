from __future__ import annotations

from pathlib import Path

from evalforge.domain.scenario import Predicate, PredicateKind
from evalforge.scenarios.fingerprint import fingerprint, near_fingerprint
from evalforge.scenarios.loader import load_scenario, write_scenario
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.scenarios.validator import ScenarioValidator


def test_scenario_yaml_round_trip_and_public_view(tmp_path: Path) -> None:
    scenario = build_manual_scenario("lost_confirmation", 0)
    path = tmp_path / "scenario.yaml"
    write_scenario(path, scenario)
    loaded = load_scenario(path)
    assert loaded == scenario
    public = loaded.public_view().model_dump(mode="json")
    dumped = str(public)
    for hidden in (
        "initial_world",
        "fault_plan",
        "oracle_plan",
        "success_contract",
        "parent_scenario_id",
        "failure",
    ):
        assert hidden not in dumped


def test_invalid_reference_postcondition_and_unreachable_fault_are_rejected() -> None:
    validator = ScenarioValidator()
    invalid_ref = build_manual_scenario("bad_deployment", 0)
    invalid_ref.oracle_plan[0].arguments["service_id"] = "does-not-exist"
    assert "REFERENTIAL_INTEGRITY" in validator.validate(invalid_ref).codes

    wrong_contract = build_manual_scenario("bad_deployment", 0)
    wrong_contract.success_contract.predicates = [
        Predicate(
            kind=PredicateKind.DEPLOYED_VERSION,
            service_id="payments-api",
            expected="v-does-not-exist",
        )
    ]
    assert "ORACLE_CONTRACT_FAILED" in validator.validate(wrong_contract).codes

    unreachable = build_manual_scenario("lost_confirmation", 0)
    unreachable.fault_plan[0].occurrence = 9
    assert "FAULT_UNREACHABLE" in validator.validate(unreachable).codes


def test_nontriviality_leakage_and_deterministic_replay() -> None:
    validator = ScenarioValidator()
    valid = build_manual_scenario("ambiguous_rollback", 0)
    result = validator.validate(valid)
    assert result.valid, result.issues
    assert result.first_trace_hash == result.replay_trace_hash
    assert result.final_world_hash == result.replay_world_hash

    trivial = build_manual_scenario("bad_deployment", 0)
    trivial.initial_world.services["payments-api"].current_version = "v1"
    trivial.initial_world.services["payments-api"].health = "healthy"
    assert "INITIAL_STATE_SATISFIES_TASK" in validator.validate(trivial).codes

    leaking = build_manual_scenario("bad_deployment", 0)
    leaking.metadata["hidden_answer"] = "v1"
    leaking.task += " Set it to v1."
    assert "HIDDEN_ANSWER_LEAK" in validator.validate(leaking).codes


def test_fingerprints_ignore_superficial_metadata_but_detect_structure() -> None:
    first = build_manual_scenario("bad_deployment", 0)
    second = first.model_copy(deep=True)
    second.scenario_id = "renamed"
    second.title = "Reworded title"
    second.metadata["created_at"] = "later"
    assert fingerprint(first) == fingerprint(second)
    assert near_fingerprint(first) == near_fingerprint(second)
    result = ScenarioValidator(existing_fingerprints={fingerprint(first)}).validate(second)
    assert "DUPLICATE_FINGERPRINT" in result.codes


def test_incorrect_config_has_agent_visible_diagnostic_evidence() -> None:
    scenario = build_manual_scenario("incorrect_config", 2)
    logs = "\n".join(scenario.initial_world.logs["identity-api"])
    assert "timeout" in logs
    assert "expected 30" in logs
    assert "observed 7" in logs
