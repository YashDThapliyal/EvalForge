from __future__ import annotations

from pathlib import Path

from evalforge.agents.base import ProviderUsage
from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.execution.episode import run_episode
from evalforge.scenarios.manual import build_manual_scenario


def test_full_scripted_episode_is_reconstructable(tmp_path: Path) -> None:
    scenario = build_manual_scenario("lost_confirmation", 0)
    result = run_episode(scenario, ScriptedBaselineAgent(), artifact_dir=tmp_path)
    assert result.starting_world == scenario.initial_world
    assert result.events
    assert result.final is not None
    assert result.final_world != result.starting_world
    assert (tmp_path / "episode.json").exists()


def test_episode_persists_live_provider_identity_and_usage(tmp_path: Path) -> None:
    agent = ScriptedBaselineAgent()
    agent.provider = "test-provider"  # type: ignore[attr-defined]
    agent.model = "test-model"  # type: ignore[attr-defined]
    agent.usage = ProviderUsage(  # type: ignore[attr-defined]
        provider="test-provider",
        model="test-model",
        input_tokens=100,
        output_tokens=20,
        api_calls=2,
        estimated_cost_usd=0.01,
    )
    result = run_episode(build_manual_scenario("bad_deployment", 0), agent, artifact_dir=tmp_path)
    assert result.agent_provider == "test-provider"
    assert result.agent_model == "test-model"
    assert result.provider_usage is not None
    assert result.provider_usage.input_tokens == 100
