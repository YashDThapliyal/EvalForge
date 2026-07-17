"""Deterministic equal-budget three-source experiment runner."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import yaml
from pydantic import BaseModel

from evalforge.agents.anthropic_agent import AnthropicAgent
from evalforge.agents.base import Agent
from evalforge.agents.openai_agent import OpenAIAgent
from evalforge.config import ExperimentConfig
from evalforge.domain.scenario import ScenarioSpec, SourceMethod
from evalforge.execution.artifacts import atomic_write
from evalforge.execution.episode import EpisodeResult, persist_episode, run_episode
from evalforge.reporting.metrics import ExperimentMetrics, SourceMetrics, compute_source_metrics
from evalforge.scenarios.failure_directed import FailureDirectedScenarioGenerator
from evalforge.scenarios.loader import load_scenarios, write_scenario
from evalforge.scenarios.manual import FAMILIES
from evalforge.scenarios.openai_proposer import OpenAIScenarioProposer
from evalforge.scenarios.random_generator import (
    GenerationResult,
    GenerationStats,
    RandomScenarioGenerator,
    ScenarioProposer,
)
from evalforge.scenarios.validator import ScenarioValidator
from evalforge.serialization import canonical_json
from evalforge.verification.engine import verify_episode
from evalforge.verification.taxonomy import classify_failure


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

    def __init__(
        self,
        config: ExperimentConfig,
        *,
        agent_factory: Callable[[], Agent] | None = None,
        random_proposer: ScenarioProposer | None = None,
    ):
        self.config = config
        self._injected_agent_factory = agent_factory
        self._injected_random_proposer = random_proposer

    def run(self) -> ExperimentResult:
        """Execute the complete live-provider comparison with deterministic ordering."""

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
        manual = self._select_manual(load_scenarios(Path("scenarios/manual")), budget)
        manual_stats = GenerationStats(attempted=budget, accepted=len(manual))
        random_result = self._random_scenarios(budget)
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
                    "model": self.config.model,
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

    def _select_manual(self, scenarios: list[ScenarioSpec], budget: int) -> list[ScenarioSpec]:
        """Select reviewed scenarios round-robin by family for meaningful quick coverage."""

        if self.config.manual_selection_strategy != "stratified-v1":
            raise ValueError(
                f"Unsupported manual selection strategy: {self.config.manual_selection_strategy}"
            )
        by_family = {
            family: [
                scenario for scenario in scenarios if scenario.metadata.get("family") == family
            ]
            for family in FAMILIES
        }
        selected: list[ScenarioSpec] = []
        round_index = 0
        while len(selected) < budget:
            added = False
            for family in FAMILIES:
                family_scenarios = by_family[family]
                if round_index < len(family_scenarios):
                    selected.append(family_scenarios[round_index])
                    added = True
                    if len(selected) == budget:
                        return selected
            if not added:
                break
            round_index += 1
        return selected

    def _run_source(
        self, root: Path, source: str, scenarios: list[ScenarioSpec]
    ) -> list[EpisodeResult]:
        episodes: list[EpisodeResult] = []
        for index, scenario in enumerate(scenarios):
            scenario.max_agent_steps = self.config.max_agent_steps
            write_scenario(root / "scenarios" / source / f"{scenario.scenario_id}.yaml", scenario)
            episode_id = f"{source}-{index:03d}-{scenario.scenario_id}"
            episodes.append(self._run_or_resume(root, scenario, episode_id))
        return episodes

    def _run_failure_directed(
        self, root: Path, budget: int
    ) -> tuple[list[ScenarioSpec], list[EpisodeResult], GenerationStats]:
        scenarios: list[ScenarioSpec] = []
        episodes: list[EpisodeResult] = []
        attempted = rejected = duplicates = 0
        candidates: list[tuple[ScenarioSpec, EpisodeResult]] = []
        while len(scenarios) < budget:
            failures = [pair for pair in candidates if pair[1].failure is not None]
            if failures:
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
            else:
                candidate = self._failure_directed_seed(len(scenarios))
                attempted += 1
            index = len(scenarios)
            candidate.max_agent_steps = self.config.max_agent_steps
            write_scenario(
                root / "scenarios" / "failure_directed" / f"{candidate.scenario_id}.yaml",
                candidate,
            )
            episode_id = f"failure_directed-{index:03d}-{candidate.scenario_id}"
            episode = self._run_or_resume(root, candidate, episode_id)
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

    def _failure_directed_seed(self, index: int) -> ScenarioSpec:
        """Return deterministic validated seeds until this model reveals a target failure."""

        pool = self._select_manual(load_scenarios(Path("scenarios/manual")), 50)
        if index >= len(pool):
            raise RuntimeError("Validated failure-directed seed pool is exhausted")
        seed = pool[index].model_copy(deep=True)
        seed.scenario_id = f"fd_seed_{seed.scenario_id}_{index:03d}"
        seed.source_method = SourceMethod.FAILURE_DIRECTED
        seed.parent_scenario_id = None
        seed.parent_failure_signature = None
        return seed

    def _run_or_resume(self, root: Path, scenario: ScenarioSpec, episode_id: str) -> EpisodeResult:
        """Reuse an exact completed model outcome, but retry provider/API runtime errors."""

        episode_dir = root / "episodes" / episode_id
        episode_path = episode_dir / "episode.json"
        if episode_path.exists():
            existing = EpisodeResult.model_validate_json(episode_path.read_text(encoding="utf-8"))
            if (
                existing.scenario_id == scenario.scenario_id
                and existing.public_request.model_dump() == scenario.public_view().model_dump()
                and existing.starting_world == scenario.initial_world
                and existing.agent_model == self.config.model
                and (
                    existing.runtime_status != "agent_runtime_error"
                    or _is_model_protocol_error(existing)
                )
            ):
                existing.verification = verify_episode(scenario, existing)
                existing.failure = classify_failure(scenario, existing, existing.verification)
                persist_episode(episode_dir, scenario, existing)
                return existing
        return run_episode(
            scenario,
            self._agent(),
            artifact_dir=episode_dir,
            episode_id=episode_id,
        )

    def _experiment_id(self) -> str:
        digest = hashlib.sha256(canonical_json(self.config).encode()).hexdigest()[:10]
        return f"evalforge-seed{self.config.seed}-b{self.config.scenarios_per_source}-{digest}"

    def _agent(self) -> Agent:
        if self._injected_agent_factory is not None:
            return self._injected_agent_factory()
        if self.config.agent == "openai":
            return OpenAIAgent(
                model=self.config.model,
                max_output_tokens=self.config.max_output_tokens,
                input_cost_per_million=self.config.input_cost_per_million,
                cached_input_cost_per_million=self.config.cached_input_cost_per_million,
                cache_write_cost_per_million=self.config.cache_write_cost_per_million,
                output_cost_per_million=self.config.output_cost_per_million,
            )
        if self.config.agent == "anthropic":
            return AnthropicAgent(
                model=self.config.model,
                max_output_tokens=self.config.max_output_tokens,
                input_cost_per_million=self.config.input_cost_per_million,
                cached_input_cost_per_million=self.config.cached_input_cost_per_million,
                cache_write_cost_per_million=self.config.cache_write_cost_per_million,
                output_cost_per_million=self.config.output_cost_per_million,
            )
        raise ValueError(f"Unsupported experiment agent: {self.config.agent}")

    def _random_proposer(self) -> ScenarioProposer:
        """Return the explicit live proposer or an explicitly injected test double."""

        if self._injected_random_proposer is not None:
            return self._injected_random_proposer
        if self.config.random_proposer == "openai":
            return OpenAIScenarioProposer(model=self.config.random_proposer_model)
        raise ValueError(f"Unsupported random proposer: {self.config.random_proposer}")

    def _random_scenarios(self, budget: int) -> GenerationResult:
        """Generate live proposals or load one explicitly shared validated corpus."""

        if self.config.random_scenarios_path is None:
            return RandomScenarioGenerator(self._random_proposer()).generate(
                count=budget, seed=self.config.seed
            )
        path = Path(self.config.random_scenarios_path)
        scenarios = load_scenarios(path)
        if len(scenarios) != budget:
            raise RuntimeError(
                f"Shared random corpus must contain exactly {budget} scenarios; "
                f"found {len(scenarios)} under {path}"
            )
        validator = ScenarioValidator()
        for scenario in scenarios:
            if scenario.source_method is not SourceMethod.RANDOM:
                raise RuntimeError(f"Shared scenario {scenario.scenario_id} is not random")
            validation = validator.validate(scenario)
            if not validation.valid:
                codes = ", ".join(sorted(validation.codes))
                raise RuntimeError(f"Shared scenario {scenario.scenario_id} is invalid: {codes}")
        stats_path = path / "generation_stats.json"
        stats = (
            GenerationStats.model_validate_json(stats_path.read_text(encoding="utf-8"))
            if stats_path.exists()
            else GenerationStats(attempted=budget, accepted=budget)
        )
        if stats.accepted != budget:
            raise RuntimeError("Shared random generation statistics do not match the corpus")
        return GenerationResult(accepted=scenarios, stats=stats)


def _is_model_protocol_error(episode: EpisodeResult) -> bool:
    """Identify a persisted model-protocol failure that must not be resampled."""

    return any(error.startswith("AgentProtocolError:") for error in episode.runtime_errors)
