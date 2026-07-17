from __future__ import annotations

from pathlib import Path

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
