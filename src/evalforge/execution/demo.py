"""Credential-free six-case demonstration of the full EvalForge pipeline."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.domain.scenario import ScenarioSpec, SourceMethod
from evalforge.execution.artifacts import atomic_write
from evalforge.execution.episode import EpisodeResult, run_episode
from evalforge.reporting.html import generate_html_report
from evalforge.reporting.inspect import render_failure_timeline
from evalforge.reporting.metrics import ExperimentMetrics, compute_source_metrics
from evalforge.scenarios.loader import write_scenario
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.scenarios.validator import ScenarioValidator
from evalforge.serialization import canonical_json
from evalforge.simulator.faults import FaultKind, FaultSpec


class DemoResult(BaseModel):
    """Offline demonstration outcome and inspectable artifact location."""

    artifact_dir: Path
    episodes: list[EpisodeResult]
    failure_signatures: list[str]
    success_rate: float
    example_timeline: str


def run_demo(seed: int = 7, output_dir: Path = Path("artifacts")) -> DemoResult:
    """Run six representative cases through simulator, harness, verifier, and reports."""

    scenarios = _demo_scenarios(seed)
    root = output_dir / f"demo-seed{seed}"
    groups: dict[str, list[ScenarioSpec]] = {
        "manual": scenarios[:2],
        "random": scenarios[2:4],
        "failure_directed": scenarios[4:],
    }
    episodes_by_source: dict[str, list[EpisodeResult]] = {}
    all_episodes: list[EpisodeResult] = []
    for source, source_scenarios in groups.items():
        episodes: list[EpisodeResult] = []
        for index, scenario in enumerate(source_scenarios):
            validation = ScenarioValidator().validate(scenario)
            if not validation.valid:
                raise RuntimeError(
                    f"Demo scenario {scenario.scenario_id} invalid: {sorted(validation.codes)}"
                )
            write_scenario(root / "scenarios" / source / f"{scenario.scenario_id}.yaml", scenario)
            episode_id = f"{source}-{index:03d}-{scenario.scenario_id}"
            episode = run_episode(
                scenario,
                ScriptedBaselineAgent(),
                artifact_dir=root / "episodes" / episode_id,
                episode_id=episode_id,
            )
            episodes.append(episode)
            all_episodes.append(episode)
        episodes_by_source[source] = episodes
    metrics = ExperimentMetrics(
        sources={
            source: compute_source_metrics(
                source,
                source_scenarios,
                episodes_by_source[source],
                attempted=len(source_scenarios),
                rejected=0,
                duplicates=0,
            )
            for source, source_scenarios in groups.items()
        }
    )
    generation_stats = {
        source: {
            "attempted": len(source_scenarios),
            "accepted": len(source_scenarios),
            "rejected": 0,
            "duplicates": 0,
            "rejection_reasons": {},
        }
        for source, source_scenarios in groups.items()
    }
    atomic_write(root / "metrics.json", canonical_json(metrics) + "\n")
    atomic_write(
        root / "config.resolved.yaml",
        yaml.safe_dump(
            {
                "seed": seed,
                "scenarios_per_source": 2,
                "agent": "scripted",
                "max_agent_steps": 10,
            },
            sort_keys=False,
        ),
    )
    atomic_write(
        root / "manifest.json",
        canonical_json(
            {
                "experiment_id": f"demo-seed{seed}",
                "status": "complete",
                "seed": seed,
                "agent": "scripted",
                "scenarios_per_source": 2,
                "episode_ids": [episode.episode_id for episode in all_episodes],
                "generation_stats": generation_stats,
            }
        )
        + "\n",
    )
    generate_html_report(root)
    failures = [episode.failure for episode in all_episodes if episode.failure is not None]
    first_failure = next(episode for episode in all_episodes if episode.failure is not None)
    success_count = sum(
        episode.verification is not None and episode.verification.success
        for episode in all_episodes
    )
    return DemoResult(
        artifact_dir=root,
        episodes=all_episodes,
        failure_signatures=sorted({failure.canonical_signature for failure in failures}),
        success_rate=success_count / len(all_episodes),
        example_timeline=render_failure_timeline(root, first_failure.episode_id),
    )


def _demo_scenarios(seed: int) -> list[ScenarioSpec]:
    normal = build_manual_scenario("bad_deployment", 0)
    normal.scenario_id = "demo_normal_rollback"

    misleading = build_manual_scenario("bad_deployment", 1)
    misleading.scenario_id = "demo_misleading_rollback"
    misleading.source_method = SourceMethod.MANUAL
    misleading.fault_plan = [
        FaultSpec(
            fault_id="demo-misleading",
            kind=FaultKind.MISLEADING_SUCCESS_RESPONSE,
            tool_name="rollback_deployment",
            occurrence=1,
        )
    ]
    retry = misleading.oracle_plan[0].model_copy(deep=True)
    retry.arguments["idempotency_key"] = "demo-oracle-retry"
    misleading.oracle_plan.insert(1, retry)

    lost = build_manual_scenario("lost_confirmation", 2)
    lost.scenario_id = "demo_lost_confirmation"
    lost.source_method = SourceMethod.RANDOM

    limited = build_manual_scenario("permission_limited", 3)
    limited.scenario_id = "demo_permission_escalation"
    limited.source_method = SourceMethod.RANDOM

    distractor = build_manual_scenario("distractor_service", 1)
    distractor.scenario_id = "demo_distractor_service"
    distractor.source_method = SourceMethod.FAILURE_DIRECTED
    distractor.task = (
        "The payments-api and checkout-api alerts overlap; evidence identifies checkout-api as "
        "the production regression to resolve."
    )

    incident = build_manual_scenario("non_idempotent_incident", 4)
    incident.scenario_id = "demo_duplicate_incident"
    incident.source_method = SourceMethod.FAILURE_DIRECTED
    for index, scenario in enumerate([normal, misleading, lost, limited, distractor, incident]):
        scenario.seed = seed * 100 + index
    return [normal, misleading, lost, limited, distractor, incident]
