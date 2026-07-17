"""Cross-model comparison generated only from completed experiment artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from jinja2 import Environment
from pydantic import BaseModel

from evalforge.execution.artifacts import atomic_write
from evalforge.reporting.metrics import SEVERITY_WEIGHTS, ExperimentMetrics
from evalforge.serialization import canonical_json


class ModelComparisonMetrics(BaseModel):
    """Aggregated metrics for one tested provider model."""

    experiment_id: str
    agent: str
    model: str
    budget_per_source: int
    evaluated_episodes: int
    task_success_rate: float
    stress_test_success_rate: float
    unique_failure_signatures: int
    severity_weighted_discoveries: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    provider_api_calls: int
    estimated_cost_usd: float
    runtime_error_episodes: int
    failure_directed_children: int
    artifact_dir: str


class ModelComparisonArtifact(BaseModel):
    """Machine-readable model comparison payload."""

    equal_budget_per_source: int
    models: list[ModelComparisonMetrics]


@dataclass(frozen=True)
class ComparisonResult:
    """Generated comparison and output location."""

    artifact: ModelComparisonArtifact
    markdown: str
    output_dir: Path


def generate_model_comparison(experiments: list[Path], output: Path) -> ComparisonResult:
    """Compare two or more completed runs without rerunning providers."""

    if len(experiments) < 2:
        raise ValueError("At least two completed experiments are required")
    rows = [_aggregate(path) for path in experiments]
    budgets = {row.budget_per_source for row in rows}
    if len(budgets) != 1:
        raise ValueError("Model comparison requires equal accepted budgets per source")
    artifact = ModelComparisonArtifact(equal_budget_per_source=budgets.pop(), models=rows)
    markdown = _markdown(artifact)
    output.mkdir(parents=True, exist_ok=True)
    atomic_write(output / "comparison.json", canonical_json(artifact) + "\n")
    atomic_write(output / "report.md", markdown)
    html = (
        Environment(autoescape=True)
        .from_string(
            """<!doctype html><html><head><meta charset="utf-8"><title>EvalForge model comparison</title>
<style>body{font:15px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#18202a}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd3da;padding:.5rem;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#eef2f5}pre{white-space:pre-wrap;background:#f6f8fa;padding:1rem}</style></head><body>
<h1>EvalForge Live Model Comparison</h1><p>Equal accepted budget: {{ artifact.equal_budget_per_source }} scenarios per source.</p>
<table><thead><tr><th>Model</th><th>Episodes</th><th>Task success</th><th>Stress success</th><th>Unique failures</th><th>Weighted discoveries</th><th>FD children</th><th>Input tokens</th><th>Output tokens</th><th>API calls</th><th>Estimated cost</th><th>Provider runtime errors</th></tr></thead><tbody>
{% for row in artifact.models %}<tr><td>{{ row.agent }} / {{ row.model }}</td><td>{{ row.evaluated_episodes }}</td><td>{{ '%.1f%%'|format(row.task_success_rate * 100) }}</td><td>{{ '%.1f%%'|format(row.stress_test_success_rate * 100) }}</td><td>{{ row.unique_failure_signatures }}</td><td>{{ row.severity_weighted_discoveries }}</td><td>{{ row.failure_directed_children }}</td><td>{{ row.input_tokens }}</td><td>{{ row.output_tokens }}</td><td>{{ row.provider_api_calls }}</td><td>${{ '%.4f'|format(row.estimated_cost_usd) }}</td><td>{{ row.runtime_error_episodes }}</td></tr>{% endfor %}
</tbody></table><h2>Method</h2><pre>{{ markdown }}</pre></body></html>"""
        )
        .render(artifact=artifact, markdown=markdown)
    )
    atomic_write(output / "report.html", html)
    return ComparisonResult(artifact=artifact, markdown=markdown, output_dir=output)


def _aggregate(experiment: Path) -> ModelComparisonMetrics:
    manifest = _json(experiment / "manifest.json")
    if manifest.get("status") != "complete":
        raise ValueError(f"Experiment is not complete: {experiment}")
    config = cast(
        dict[str, object], yaml.safe_load((experiment / "config.resolved.yaml").read_text())
    )
    metrics = ExperimentMetrics.model_validate(_json(experiment / "metrics.json"))
    sources = list(metrics.sources.values())
    evaluated = sum(item.evaluated for item in sources)
    task_successes = sum(round(item.task_success_rate * item.evaluated) for item in sources)
    stress_successes = sum(
        round(item.stress_test_success_rate * item.evaluated) for item in sources
    )
    signature_severity: dict[str, str] = {}
    for path in sorted((experiment / "episodes").rglob("failure.json")):
        failure = _json(path)
        signature = str(failure["canonical_signature"])
        severity = str(failure["severity"])
        previous = signature_severity.get(signature)
        if previous is None or SEVERITY_WEIGHTS[severity] > SEVERITY_WEIGHTS[previous]:
            signature_severity[signature] = severity
    runtime_errors = 0
    for path in sorted((experiment / "episodes").rglob("episode.json")):
        episode = _json(path)
        if episode.get("runtime_status") == "agent_runtime_error":
            runtime_errors += 1
    directed_children = 0
    for path in sorted((experiment / "scenarios" / "failure_directed").glob("*.yaml")):
        scenario = cast(dict[str, object], yaml.safe_load(path.read_text(encoding="utf-8")))
        if scenario.get("parent_scenario_id") is not None:
            directed_children += 1
    budget = config.get("scenarios_per_source")
    if not isinstance(budget, int):
        raise ValueError(f"Resolved experiment budget is invalid: {experiment}")
    return ModelComparisonMetrics(
        experiment_id=str(manifest["experiment_id"]),
        agent=str(manifest.get("agent", config.get("agent", "unknown"))),
        model=str(manifest.get("model", config.get("model", "unknown"))),
        budget_per_source=budget,
        evaluated_episodes=evaluated,
        task_success_rate=task_successes / evaluated if evaluated else 0.0,
        stress_test_success_rate=stress_successes / evaluated if evaluated else 0.0,
        unique_failure_signatures=len(signature_severity),
        severity_weighted_discoveries=sum(
            SEVERITY_WEIGHTS[severity] for severity in signature_severity.values()
        ),
        input_tokens=sum(item.input_tokens for item in sources),
        cached_input_tokens=sum(item.cached_input_tokens for item in sources),
        output_tokens=sum(item.output_tokens for item in sources),
        provider_api_calls=sum(item.provider_api_calls for item in sources),
        estimated_cost_usd=sum(item.estimated_cost_usd for item in sources),
        runtime_error_episodes=runtime_errors,
        failure_directed_children=directed_children,
        artifact_dir=str(experiment.resolve()),
    )


def _markdown(artifact: ModelComparisonArtifact) -> str:
    lines = [
        "# EvalForge Live Model Comparison",
        "",
        f"Equal accepted budget: {artifact.equal_budget_per_source} scenarios per source.",
        "",
        "| Provider / model | Episodes | Task success | Stress success | Unique failures | "
        "Weighted discoveries | FD children | Input tokens | Output tokens | Provider API calls | "
        "Estimated cost | Provider runtime errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in artifact.models:
        lines.append(
            f"| {row.agent} / `{row.model}` | {row.evaluated_episodes} | "
            f"{row.task_success_rate:.1%} | {row.stress_test_success_rate:.1%} | "
            f"{row.unique_failure_signatures} | {row.severity_weighted_discoveries} | "
            f"{row.failure_directed_children} | {row.input_tokens} | {row.output_tokens} | "
            f"{row.provider_api_calls} | "
            f"${row.estimated_cost_usd:.4f} | {row.runtime_error_episodes} |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            "Each model received the same public scenario tasks and strict tool schemas. Hidden "
            "faults, actual outcomes, oracle plans, and verifier predicates were not provided. "
            "The comparison uses equal accepted scenario budgets and deterministic verification; "
            "invalid generated scenarios do not consume the evaluation budget.",
            "",
            "Costs are estimates from recorded provider token usage and the explicit rates saved "
            "in each resolved experiment configuration.",
            "",
        ]
    )
    return "\n".join(lines)


def _json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
