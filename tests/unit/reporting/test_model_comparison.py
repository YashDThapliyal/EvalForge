from __future__ import annotations

import json
from pathlib import Path

from evalforge.config import ExperimentConfig
from evalforge.execution.experiment import ExperimentRunner
from evalforge.reporting.comparison import generate_model_comparison


def test_model_comparison_is_generated_from_real_episode_artifacts(tmp_path: Path) -> None:
    first = ExperimentRunner(
        ExperimentConfig(
            seed=1,
            scenarios_per_source=1,
            agent="scripted",
            model="baseline-a",
            output_dir=str(tmp_path / "runs"),
        )
    ).run()
    second = ExperimentRunner(
        ExperimentConfig(
            seed=2,
            scenarios_per_source=1,
            agent="scripted",
            model="baseline-b",
            output_dir=str(tmp_path / "runs"),
        )
    ).run()
    output = tmp_path / "comparison"
    result = generate_model_comparison([first.artifact_dir, second.artifact_dir], output)
    assert "baseline-a" in result.markdown
    assert "baseline-b" in result.markdown
    assert "Provider API calls" in result.markdown
    assert (output / "report.html").exists()
    payload = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    assert len(payload["models"]) == 2
    assert all(item["evaluated_episodes"] == 3 for item in payload["models"])
