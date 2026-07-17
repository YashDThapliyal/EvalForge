from __future__ import annotations

from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.execution.episode import run_episode
from evalforge.reporting.metrics import compute_source_metrics
from evalforge.scenarios.manual import build_manual_scenario


def test_metrics_match_episode_fixtures_and_discovery_curve_is_monotonic() -> None:
    scenarios = [
        build_manual_scenario("bad_deployment", 0),
        build_manual_scenario("lost_confirmation", 0),
        build_manual_scenario("non_idempotent_incident", 0),
    ]
    episodes = [run_episode(item, ScriptedBaselineAgent()) for item in scenarios]
    metrics = compute_source_metrics(
        "manual", scenarios, episodes, attempted=3, rejected=0, duplicates=0
    )
    assert metrics.evaluated == 3
    assert metrics.total_failure_episodes == sum(item.failure is not None for item in episodes)
    assert metrics.unique_failure_signatures == len(
        {item.failure.canonical_signature for item in episodes if item.failure is not None}
    )
    assert metrics.discovery_curve == sorted(metrics.discovery_curve)
    assert metrics.average_tool_calls == sum(len(item.events) for item in episodes) / 3
