from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from evalforge.config import ExperimentConfig
from evalforge.execution.experiment import ExperimentRunner
from evalforge.scenarios.loader import write_scenario
from tests.support import (
    LIVE_CONFIG_FIELDS,
    FixtureScenarioProposer,
    UnresolvedTestAgent,
)


def _runner(tmp_path: Path, *, seed: int, budget: int) -> ExperimentRunner:
    config = ExperimentConfig(
        seed=seed,
        scenarios_per_source=budget,
        output_dir=str(tmp_path),
        **LIVE_CONFIG_FIELDS,  # type: ignore[arg-type]
    )
    return ExperimentRunner(
        config,
        agent_factory=UnresolvedTestAgent,
        random_proposer=FixtureScenarioProposer(),
    )


def test_equal_budget_experiment_is_deterministic_with_explicit_test_doubles(
    tmp_path: Path,
) -> None:
    first = _runner(tmp_path, seed=7, budget=3).run()
    second = _runner(tmp_path, seed=7, budget=3).run()
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
    manual_families = {str(item.metadata["family"]) for item in first.scenario_order["manual"]}
    assert len(manual_families) == 3


def test_quick_manual_budget_is_stratified_across_all_families(tmp_path: Path) -> None:
    result = _runner(tmp_path, seed=7, budget=12).run()
    families = [str(item.metadata["family"]) for item in result.scenario_order["manual"]]
    assert len(set(families[:10])) == 10


def test_failure_directed_lineage_uses_only_prior_own_run_failures(tmp_path: Path) -> None:
    result = _runner(tmp_path, seed=19, budget=4).run()
    fd = result.scenario_order["failure_directed"]
    prior: set[str] = set()
    for index, scenario in enumerate(fd):
        if index:
            assert scenario.parent_scenario_id in prior
            assert scenario.parent_failure_signature is not None
        prior.add(scenario.scenario_id)
    assert result.generation_stats["failure_directed"].accepted == 4
    assert result.metrics.sources["failure_directed"].evaluated == 4


def test_adaptive_source_uses_more_validated_seeds_when_no_failure_exists(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    runner = _runner(tmp_path, seed=7, budget=4)

    def passing_episode(*args: object, **kwargs: object) -> object:
        episode_id = str(kwargs["episode_id"])
        return SimpleNamespace(episode_id=episode_id, failure=None)

    monkeypatch.setattr("evalforge.execution.experiment.run_episode", passing_episode)
    scenarios, episodes, stats = runner._run_failure_directed(tmp_path, 4)
    assert len(scenarios) == len(episodes) == stats.accepted == 4
    assert len({scenario.scenario_id for scenario in scenarios}) == 4
    assert all(scenario.parent_scenario_id is None for scenario in scenarios)


def test_experiment_can_reuse_one_validated_random_corpus_across_models(
    tmp_path: Path,
) -> None:
    shared = tmp_path / "shared-random"
    proposer = FixtureScenarioProposer()
    for attempt in range(3):
        scenario = proposer.propose(attempt, 7)
        write_scenario(shared / f"{scenario.scenario_id}.yaml", scenario)

    class ExplodingProposer:
        def propose(self, attempt: int, seed: int):  # type: ignore[no-untyped-def]
            del attempt, seed
            raise AssertionError("shared corpus should prevent a new proposal call")

    config = ExperimentConfig(
        seed=7,
        scenarios_per_source=3,
        output_dir=str(tmp_path / "runs"),
        random_scenarios_path=str(shared),
        **LIVE_CONFIG_FIELDS,  # type: ignore[arg-type]
    )
    result = ExperimentRunner(
        config,
        agent_factory=UnresolvedTestAgent,
        random_proposer=ExplodingProposer(),
    ).run()
    assert [scenario.scenario_id for scenario in result.scenario_order["random"]] == [
        proposer.propose(attempt, 7).scenario_id for attempt in range(3)
    ]
