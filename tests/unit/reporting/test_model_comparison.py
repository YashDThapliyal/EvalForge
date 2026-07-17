from __future__ import annotations

import json
from pathlib import Path

from evalforge.config import ExperimentConfig
from evalforge.execution.experiment import ExperimentRunner
from evalforge.reporting.comparison import generate_model_comparison
from tests.support import FixtureScenarioProposer, UnresolvedTestAgent


def _runner(tmp_path: Path, *, seed: int, model: str) -> ExperimentRunner:
    config = ExperimentConfig(
        seed=seed,
        scenarios_per_source=1,
        agent="openai",
        model=model,
        output_dir=str(tmp_path / "runs"),
        random_proposer="openai",
        random_proposer_model="test-proposer-model",
        failure_directed_proposer="bounded_mutation",
        input_cost_per_million=1.0,
        cached_input_cost_per_million=0.1,
        cache_write_cost_per_million=1.25,
        output_cost_per_million=2.0,
    )
    return ExperimentRunner(
        config,
        agent_factory=UnresolvedTestAgent,
        random_proposer=FixtureScenarioProposer(),
    )


def test_model_comparison_is_generated_from_real_episode_artifacts(tmp_path: Path) -> None:
    first = _runner(tmp_path, seed=1, model="provider-model-a").run()
    second = _runner(tmp_path, seed=2, model="provider-model-b").run()
    output = tmp_path / "comparison"
    result = generate_model_comparison([first.artifact_dir, second.artifact_dir], output)
    assert "provider-model-a" in result.markdown
    assert "provider-model-b" in result.markdown
    assert "Provider API calls" in result.markdown
    assert "FD children" in result.markdown
    assert (output / "report.html").exists()
    payload = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    assert len(payload["models"]) == 2
    assert all(item["evaluated_episodes"] == 3 for item in payload["models"])
    assert all("failure_directed_children" in item for item in payload["models"])
