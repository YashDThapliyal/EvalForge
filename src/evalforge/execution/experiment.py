"""Deterministic equal-budget three-source experiment runner."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel

from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.config import ExperimentConfig
from evalforge.domain.scenario import ScenarioSpec, SourceMethod
from evalforge.execution.artifacts import atomic_write
from evalforge.execution.episode import EpisodeResult, run_episode
from evalforge.reporting.metrics import ExperimentMetrics, SourceMetrics, compute_source_metrics
from evalforge.scenarios.failure_directed import FailureDirectedScenarioGenerator
from evalforge.scenarios.loader import load_scenarios, write_scenario
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.scenarios.random_generator import (
    GenerationStats,
    ProgrammaticProposer,
    RandomScenarioGenerator,
)
from evalforge.serialization import canonical_json


class ExperimentResult(BaseModel):
    """In-memory summary and paths for a completed experiment."""

    experiment_id: str
    artifact_dir: Path
    metrics: ExperimentMetrics
    episode_ids: list[str]
    scenario_order: dict[str, list[ScenarioSpec]]
    generation_stats: dict[str, GenerationStats]


class ExperimentRunner:
    """Run manual, random, and adaptive failure-directed sources fairly."""

    def __init__(self, config: ExperimentConfig):
        self.config = config

    def run(self) -> ExperimentResult:
        """Execute the complete offline comparison with deterministic ordering."""

        experiment_id = self._experiment_id()
        root = Path(self.config.output_dir) / experiment_id
        root.mkdir(parents=True, exist_ok=True)
        atomic_write(
            root / "manifest.json",
            canonical_json(
                {"experiment_id": experiment_id, "status": "running", "seed": self.config.seed}
            )
            + "\n",
        )
        atomic_write(
            root / "config.resolved.yaml",
            yaml.safe_dump(self.config.model_dump(mode="json"), sort_keys=False),
        )
        budget = self.config.scenarios_per_source
        manual = load_scenarios(Path("scenarios/manual"))[:budget]
        manual_stats = GenerationStats(attempted=budget, accepted=len(manual))
        random_result = RandomScenarioGenerator(ProgrammaticProposer()).generate(
            count=budget, seed=self.config.seed
        )
        if len(manual) != budget or len(random_result.accepted) != budget:
            raise RuntimeError("Unable to fill the accepted scenario budget")

        scenario_order: dict[str, list[ScenarioSpec]] = {
            "manual": manual,
            "random": random_result.accepted,
        }
        episodes_by_source: dict[str, list[EpisodeResult]] = {
            "manual": self._run_source(root, "manual", manual),
            "random": self._run_source(root, "random", random_result.accepted),
        }
        fd_scenarios, fd_episodes, fd_stats = self._run_failure_directed(root, budget)
        scenario_order["failure_directed"] = fd_scenarios
        episodes_by_source["failure_directed"] = fd_episodes
        generation_stats = {
            "manual": manual_stats,
            "random": random_result.stats,
            "failure_directed": fd_stats,
        }
        source_metrics: dict[str, SourceMetrics] = {}
        for source, scenarios in scenario_order.items():
            stats = generation_stats[source]
            source_metrics[source] = compute_source_metrics(
                source,
                scenarios,
                episodes_by_source[source],
                attempted=stats.attempted,
                rejected=stats.rejected,
                duplicates=stats.duplicates,
            )
        metrics = ExperimentMetrics(sources=source_metrics)
        atomic_write(root / "metrics.json", canonical_json(metrics) + "\n")
        episode_ids = [
            episode.episode_id
            for source in ("manual", "random", "failure_directed")
            for episode in episodes_by_source[source]
        ]
        atomic_write(
            root / "manifest.json",
            canonical_json(
                {
                    "experiment_id": experiment_id,
                    "status": "complete",
                    "seed": self.config.seed,
                    "agent": self.config.agent,
                    "scenarios_per_source": budget,
                    "episode_ids": episode_ids,
                    "generation_stats": {
                        key: value.model_dump(mode="json")
                        for key, value in generation_stats.items()
                    },
                }
            )
            + "\n",
        )
        from evalforge.reporting.html import generate_html_report

        generate_html_report(root)
        return ExperimentResult(
            experiment_id=experiment_id,
            artifact_dir=root,
            metrics=metrics,
            episode_ids=episode_ids,
            scenario_order=scenario_order,
            generation_stats=generation_stats,
        )

    def _run_source(
        self, root: Path, source: str, scenarios: list[ScenarioSpec]
    ) -> list[EpisodeResult]:
        episodes: list[EpisodeResult] = []
        for index, scenario in enumerate(scenarios):
            scenario.max_agent_steps = self.config.max_agent_steps
            write_scenario(root / "scenarios" / source / f"{scenario.scenario_id}.yaml", scenario)
            episode_id = f"{source}-{index:03d}-{scenario.scenario_id}"
            episodes.append(
                run_episode(
                    scenario,
                    ScriptedBaselineAgent(),
                    artifact_dir=root / "episodes" / episode_id,
                    episode_id=episode_id,
                )
            )
        return episodes

    def _run_failure_directed(
        self, root: Path, budget: int
    ) -> tuple[list[ScenarioSpec], list[EpisodeResult], GenerationStats]:
        scenarios: list[ScenarioSpec] = []
        episodes: list[EpisodeResult] = []
        attempted = rejected = duplicates = 0
        seed = build_manual_scenario("lost_confirmation", self.config.seed % 5)
        seed.scenario_id = f"fd_seed_{self.config.seed}"
        seed.source_method = SourceMethod.FAILURE_DIRECTED
        seed.parent_scenario_id = None
        seed.parent_failure_signature = None
        candidates: list[tuple[ScenarioSpec, EpisodeResult]] = []
        while len(scenarios) < budget:
            if not scenarios:
                candidate = seed
                attempted += 1
            else:
                failures = [pair for pair in candidates if pair[1].failure is not None]
                if not failures:
                    raise RuntimeError("Adaptive source found no prior own-run failure to target")
                parent, parent_episode = failures[(len(scenarios) - 1) % len(failures)]
                if parent_episode.failure is None:
                    raise RuntimeError("Failure target unexpectedly absent")
                generated = FailureDirectedScenarioGenerator().generate(
                    parent,
                    parent_episode.failure,
                    count=1,
                    seed=self.config.seed + len(scenarios),
                )
                attempted += generated.stats.attempted
                rejected += generated.stats.rejected
                duplicates += generated.stats.duplicates
                if not generated.accepted:
                    raise RuntimeError("Unable to generate a valid failure-directed child")
                candidate = generated.accepted[0]
            index = len(scenarios)
            candidate.max_agent_steps = self.config.max_agent_steps
            write_scenario(
                root / "scenarios" / "failure_directed" / f"{candidate.scenario_id}.yaml",
                candidate,
            )
            episode_id = f"failure_directed-{index:03d}-{candidate.scenario_id}"
            episode = run_episode(
                candidate,
                ScriptedBaselineAgent(),
                artifact_dir=root / "episodes" / episode_id,
                episode_id=episode_id,
            )
            scenarios.append(candidate)
            episodes.append(episode)
            candidates.append((candidate, episode))
        return (
            scenarios,
            episodes,
            GenerationStats(
                attempted=attempted,
                accepted=len(scenarios),
                rejected=rejected,
                duplicates=duplicates,
            ),
        )

    def _experiment_id(self) -> str:
        digest = hashlib.sha256(canonical_json(self.config).encode()).hexdigest()[:10]
        return f"evalforge-seed{self.config.seed}-b{self.config.scenarios_per_source}-{digest}"
