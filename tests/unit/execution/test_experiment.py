from __future__ import annotations

from pathlib import Path

import yaml

from evalforge.config import ExperimentConfig
from evalforge.execution.experiment import ExperimentRunner


def test_equal_budget_deterministic_offline_experiment(tmp_path: Path) -> None:
    config = ExperimentConfig(seed=7, scenarios_per_source=3, output_dir=str(tmp_path))
    first = ExperimentRunner(config).run()
    second = ExperimentRunner(config).run()
    assert first.experiment_id == second.experiment_id
    assert first.metrics == second.metrics
    assert set(first.metrics.sources) == {"manual", "random", "failure_directed"}
    assert {item.evaluated for item in first.metrics.sources.values()} == {3}
    assert len(first.episode_ids) == 9
    assert (first.artifact_dir / "manifest.json").exists()
    assert (first.artifact_dir / "config.resolved.yaml").exists()
    assert (first.artifact_dir / "metrics.json").exists()
    resolved = yaml.safe_load(
        (first.artifact_dir / "config.resolved.yaml").read_text(encoding="utf-8")
    )
    assert resolved["seed"] == 7


def test_failure_directed_lineage_uses_only_prior_own_run_failures(tmp_path: Path) -> None:
    config = ExperimentConfig(seed=19, scenarios_per_source=4, output_dir=str(tmp_path))
    result = ExperimentRunner(config).run()
    fd = result.scenario_order["failure_directed"]
    prior: set[str] = set()
    for index, scenario in enumerate(fd):
        if index:
            assert scenario.parent_scenario_id in prior
            assert scenario.parent_failure_signature is not None
        prior.add(scenario.scenario_id)
    assert result.generation_stats["failure_directed"].accepted == 4
    assert result.metrics.sources["failure_directed"].evaluated == 4
