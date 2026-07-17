from __future__ import annotations

from pathlib import Path

from evalforge.scenarios.loader import load_scenarios
from evalforge.scenarios.validator import ScenarioValidator


def test_fifty_checked_in_manual_scenarios_validate() -> None:
    scenarios = load_scenarios(Path("scenarios/manual"))
    assert len(scenarios) == 50
    assert len({scenario.scenario_id for scenario in scenarios}) == 50
    for scenario in scenarios:
        result = ScenarioValidator().validate(scenario)
        assert result.valid, (scenario.scenario_id, result.issues)

    tags = {tag for scenario in scenarios for tag in scenario.tags}
    required = {
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
    }
    assert required <= tags
