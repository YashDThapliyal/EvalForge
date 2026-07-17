"""Markdown experiment report regenerated only from saved artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import cast

import yaml

from evalforge.execution.artifacts import atomic_write
from evalforge.reporting.metrics import ExperimentMetrics

SOURCE_ORDER = ("manual", "random", "failure_directed")
SOURCE_LABELS = {
    "manual": "Manual",
    "random": "Random",
    "failure_directed": "Failure-directed",
}


def generate_markdown_report(experiment: Path) -> str:
    """Regenerate the complete Markdown report without rerunning an agent."""

    manifest = _read_json(experiment / "manifest.json")
    config = cast(
        dict[str, object], yaml.safe_load((experiment / "config.resolved.yaml").read_text())
    )
    metrics = ExperimentMetrics.model_validate(_read_json(experiment / "metrics.json"))
    failures = [
        _read_json(path) for path in sorted((experiment / "episodes").rglob("failure.json"))
    ]
    lines = [
        "# EvalForge Experiment Report",
        "",
        f"Experiment: `{manifest['experiment_id']}`  ",
        f"Tested agent: `{manifest.get('agent', config.get('agent', 'unknown'))}`",
        "",
        "## Experiment configuration",
        "",
        f"- Seed: `{config['seed']}`",
        f"- Accepted scenario budget per source: `{config['scenarios_per_source']}`",
        f"- Maximum agent steps: `{config['max_agent_steps']}`",
        "",
        "## Scenario generation and validation",
        "",
        "| Source | Attempted | Accepted valid | Rejected | Duplicates | Validation rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for source in SOURCE_ORDER:
        item = metrics.sources[source]
        lines.append(
            f"| {SOURCE_LABELS[source]} | {item.attempted_scenarios} | "
            f"{item.accepted_valid_scenarios} | {item.rejected_scenarios} | "
            f"{item.duplicate_scenarios} | {item.validation_rate:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Source comparison",
            "",
            "| Metric | Manual | Random | Failure-directed |",
            "|---|---:|---:|---:|",
        ]
    )
    comparison = (
        ("Evaluated episodes", "evaluated", "d"),
        ("Unique failure signatures", "unique_failure_signatures", "d"),
        ("Severity-weighted discoveries", "severity_weighted_discoveries", "d"),
        ("Failures per 10 tests", "failures_per_10_tests", ".2f"),
        ("Average tool calls", "average_tool_calls", ".2f"),
    )
    for label, field, style in comparison:
        values = [getattr(metrics.sources[source], field) for source in SOURCE_ORDER]
        formatted = [format(value, style) for value in values]
        lines.append(f"| {label} | {' | '.join(formatted)} |")
    lines.extend(["", "## Success rates", ""])
    for source in SOURCE_ORDER:
        item = metrics.sources[source]
        lines.append(
            f"- {SOURCE_LABELS[source]}: task success {item.task_success_rate:.1%}; "
            f"full stress-test success {item.stress_test_success_rate:.1%}."
        )
    lines.extend(["", "## Unique failure discoveries", ""])
    for source in SOURCE_ORDER:
        item = metrics.sources[source]
        lines.append(
            f"- {SOURCE_LABELS[source]}: {item.unique_failure_signatures} unique; "
            f"{item.high_critical_failure_signatures} high/critical; "
            f"weighted score {item.severity_weighted_discoveries}."
        )
    lines.extend(["", "## Severity breakdown", ""])
    for source in SOURCE_ORDER:
        breakdown = metrics.sources[source].severity_breakdown
        rendered = ", ".join(f"{key}={value}" for key, value in breakdown.items()) or "none"
        lines.append(f"- {SOURCE_LABELS[source]}: {rendered}.")
    lines.extend(["", "## Discovery curves", ""])
    for source in SOURCE_ORDER:
        curve = ", ".join(str(value) for value in metrics.sources[source].discovery_curve)
        lines.append(f"- {SOURCE_LABELS[source]} cumulative unique discoveries: `{curve}`")
    lines.extend(["", "## Top failure modes", ""])
    counts = Counter(str(item["primary_code"]) for item in failures)
    if counts:
        for index, (code, count) in enumerate(counts.most_common(10), 1):
            lines.append(f"{index}. `{code}` — {count} episode(s)")
    else:
        lines.append("No failed episodes.")
    lines.extend(["", "## Validation rejection reasons", ""])
    stats = cast(dict[str, dict[str, object]], manifest.get("generation_stats", {}))
    reasons_found = False
    for source in SOURCE_ORDER:
        reasons = cast(dict[str, int], stats.get(source, {}).get("rejection_reasons", {}))
        if reasons:
            reasons_found = True
            lines.append(
                f"- {SOURCE_LABELS[source]}: "
                + ", ".join(f"{key}={value}" for key, value in sorted(reasons.items()))
            )
    if not reasons_found:
        lines.append("No validation rejections in this run.")
    lines.extend(["", "## Scenario lineage summary", ""])
    children = [item for item in failures if item.get("parent_scenario_id")]
    lines.append(
        f"Failure-directed failed descendants with recorded parent lineage: {len(children)}."
    )
    lines.extend(["", "Failed episode details:", ""])
    for path in sorted((experiment / "episodes").rglob("failure.json")):
        episode_id = path.parent.name
        lines.append(f"- [{episode_id}](failures/{episode_id}.html)")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Results describe this deterministic scripted baseline and these scenario "
            "families only.",
            "- Raw counts and rates are reported; no statistical-significance claim is made.",
            "- The simulator is intentionally local and does not model every production-cloud "
            "behavior.",
            "",
        ]
    )
    report = "\n".join(lines)
    atomic_write(experiment / "report.md", report)
    return report


def _read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
