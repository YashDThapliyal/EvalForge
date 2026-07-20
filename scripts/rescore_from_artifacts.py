"""Re-score saved episodes with the current verifier, without provider calls.

This exists because a verifier correction must be applied to the episodes that
were actually executed. Re-running `evalforge experiment` would instead let the
corrected pass/fail signal feed failure-directed lineage, changing which
scenarios get generated and requiring new paid episodes -- a different
experiment, not a correction of this one.

Every scenario, trace, and final world here is read from disk exactly as run.
Only verification, failure classification, and the metrics derived from them are
recomputed.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from evalforge.execution.artifacts import atomic_write
from evalforge.execution.episode import EpisodeResult, persist_episode
from evalforge.reporting.metrics import ExperimentMetrics, SourceMetrics, compute_source_metrics
from evalforge.scenarios.loader import load_scenarios
from evalforge.serialization import canonical_json
from evalforge.verification.engine import verify_episode
from evalforge.verification.taxonomy import classify_failure

SOURCES = ("manual", "random", "failure_directed")


def _source_of(episode_id: str) -> str:
    if episode_id.startswith("failure_directed"):
        return "failure_directed"
    return episode_id.split("-")[0]


def rescore_experiment(experiment: Path) -> dict[str, tuple[float, float]]:
    """Recompute verification, failures, and metrics for one saved experiment."""

    manifest = json.loads((experiment / "manifest.json").read_text(encoding="utf-8"))
    previous = ExperimentMetrics.model_validate(
        json.loads((experiment / "metrics.json").read_text(encoding="utf-8"))
    )

    scenarios_by_source: dict[str, list] = {source: [] for source in SOURCES}
    episodes_by_source: dict[str, list[EpisodeResult]] = {source: [] for source in SOURCES}

    for episode_id in manifest["episode_ids"]:
        episode_dir = experiment / "episodes" / episode_id
        scenario = load_scenarios(episode_dir / "scenario.yaml")[0]
        episode = EpisodeResult.model_validate_json(
            (episode_dir / "episode.json").read_text(encoding="utf-8")
        )
        episode.verification = verify_episode(scenario, episode)
        episode.failure = classify_failure(scenario, episode, episode.verification)
        persist_episode(episode_dir, scenario, episode)
        if episode.failure is None:
            (episode_dir / "failure.json").unlink(missing_ok=True)

        source = _source_of(episode_id)
        scenarios_by_source[source].append(scenario)
        episodes_by_source[source].append(episode)

    source_metrics: dict[str, SourceMetrics] = {}
    for source in SOURCES:
        stats = manifest["generation_stats"][source]
        source_metrics[source] = compute_source_metrics(
            source,
            scenarios_by_source[source],
            episodes_by_source[source],
            attempted=stats["attempted"],
            rejected=stats["rejected"],
            duplicates=stats["duplicates"],
        )
    atomic_write(
        experiment / "metrics.json",
        canonical_json(ExperimentMetrics(sources=source_metrics)) + "\n",
    )
    return {
        source: (
            previous.sources[source].stress_test_success_rate,
            source_metrics[source].stress_test_success_rate,
        )
        for source in SOURCES
    }


def main(experiments: list[Path]) -> None:
    """Re-score each named experiment directory in place."""

    for experiment in experiments:
        deltas = rescore_experiment(experiment)
        typer.echo(f"{experiment.name}")
        for source, (before, after) in deltas.items():
            marker = "" if abs(after - before) < 1e-9 else "  <- changed"
            typer.echo(f"  {source:<18} {before:6.1%} -> {after:6.1%}{marker}")


if __name__ == "__main__":
    typer.run(main)
