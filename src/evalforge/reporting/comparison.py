"""Cross-model comparison generated only from completed experiment artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
    infrastructure_error_episodes: int
    protocol_error_episodes: int
    infrastructure_eligible_episodes: int
    task_success_rate_excluding_infrastructure_errors: float
    stress_test_success_rate_excluding_infrastructure_errors: float
    failure_directed_children: int
    artifact_dir: str


class SourceComparisonMetrics(BaseModel):
    """Cross-model discovery metrics for one scenario source."""

    source: str
    evaluated_episodes: int
    stress_test_success_rate: float
    unique_failure_signatures: int
    severity_weighted_discoveries: int


@dataclass
class _SourceBucket:
    evaluated: int = 0
    successes: int = 0
    signatures: dict[str, str] = field(default_factory=dict)


class ModelComparisonArtifact(BaseModel):
    """Machine-readable model comparison payload."""

    equal_budget_per_source: int
    models: list[ModelComparisonMetrics]
    sources: list[SourceComparisonMetrics]


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
    artifact = ModelComparisonArtifact(
        equal_budget_per_source=budgets.pop(),
        models=rows,
        sources=_aggregate_sources(experiments),
    )
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
<table><thead><tr><th>Model</th><th>Episodes</th><th>Task success</th><th>Stress success</th><th>Unique failures</th><th>Weighted discoveries</th><th>FD children</th><th>Input tokens</th><th>Output tokens</th><th>API calls</th><th>Estimated cost</th><th>Agent runtime errors</th></tr></thead><tbody>
{% for row in artifact.models %}<tr><td>{{ row.agent }} / {{ row.model }}</td><td>{{ row.evaluated_episodes }}</td><td>{{ '%.1f%%'|format(row.task_success_rate * 100) }}</td><td>{{ '%.1f%%'|format(row.stress_test_success_rate * 100) }}</td><td>{{ row.unique_failure_signatures }}</td><td>{{ row.severity_weighted_discoveries }}</td><td>{{ row.failure_directed_children }}</td><td>{{ row.input_tokens }}</td><td>{{ row.output_tokens }}</td><td>{{ row.provider_api_calls }}</td><td>${{ '%.4f'|format(row.estimated_cost_usd) }}</td><td>{{ row.runtime_error_episodes }}</td></tr>{% endfor %}
</tbody></table>
<h2>Source-level discovery comparison</h2><table><thead><tr><th>Source</th><th>Success</th><th>Unique signatures</th><th>Weighted discoveries</th></tr></thead><tbody>
{% for row in artifact.sources %}<tr><td>{{ row.source }}</td><td>{{ '%.1f%%'|format(row.stress_test_success_rate * 100) }}</td><td>{{ row.unique_failure_signatures }}</td><td>{{ row.severity_weighted_discoveries }}</td></tr>{% endfor %}
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
    runtime_errors = infrastructure_errors = protocol_errors = 0
    eligible_task_successes = eligible_stress_successes = eligible = 0
    for path in sorted((experiment / "episodes").rglob("episode.json")):
        episode = _json(path)
        if episode.get("runtime_status") == "agent_runtime_error":
            runtime_errors += 1
            errors = episode.get("runtime_errors")
            error_text = " ".join(str(item) for item in errors) if isinstance(errors, list) else ""
            if "AgentProtocolError:" in error_text:
                protocol_errors += 1
            else:
                infrastructure_errors += 1
                continue
        eligible += 1
        eligible_task_successes += _task_success(episode)
        eligible_stress_successes += _stress_success(episode)
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
        infrastructure_error_episodes=infrastructure_errors,
        protocol_error_episodes=protocol_errors,
        infrastructure_eligible_episodes=eligible,
        task_success_rate_excluding_infrastructure_errors=(
            eligible_task_successes / eligible if eligible else 0.0
        ),
        stress_test_success_rate_excluding_infrastructure_errors=(
            eligible_stress_successes / eligible if eligible else 0.0
        ),
        failure_directed_children=directed_children,
        artifact_dir=str(experiment.resolve()),
    )


def _aggregate_sources(experiments: list[Path]) -> list[SourceComparisonMetrics]:
    buckets: dict[str, _SourceBucket] = {
        source: _SourceBucket() for source in ("manual", "random", "failure_directed")
    }
    for experiment in experiments:
        for episode_path in sorted((experiment / "episodes").rglob("episode.json")):
            scenario = cast(
                dict[str, object],
                yaml.safe_load((episode_path.parent / "scenario.yaml").read_text(encoding="utf-8")),
            )
            source = str(scenario["source_method"])
            if source not in buckets:
                raise ValueError(f"Unsupported episode source in comparison: {source}")
            episode = _json(episode_path)
            bucket = buckets[source]
            bucket.evaluated += 1
            bucket.successes += _stress_success(episode)
            failure_path = episode_path.parent / "failure.json"
            if failure_path.exists():
                failure = _json(failure_path)
                signatures = bucket.signatures
                signature = str(failure["canonical_signature"])
                severity = str(failure["severity"])
                previous = signatures.get(signature)
                if previous is None or SEVERITY_WEIGHTS[severity] > SEVERITY_WEIGHTS[previous]:
                    signatures[signature] = severity
    rows: list[SourceComparisonMetrics] = []
    for source in ("manual", "random", "failure_directed"):
        bucket = buckets[source]
        evaluated = bucket.evaluated
        signatures = bucket.signatures
        rows.append(
            SourceComparisonMetrics(
                source=source,
                evaluated_episodes=evaluated,
                stress_test_success_rate=(bucket.successes / evaluated if evaluated else 0.0),
                unique_failure_signatures=len(signatures),
                severity_weighted_discoveries=sum(
                    SEVERITY_WEIGHTS[severity] for severity in signatures.values()
                ),
            )
        )
    return rows


def _task_success(episode: dict[str, object]) -> int:
    verification = episode.get("verification")
    return int(isinstance(verification, dict) and verification.get("task_success") is True)


def _stress_success(episode: dict[str, object]) -> int:
    verification = episode.get("verification")
    if not isinstance(verification, dict):
        return 0
    return int(
        all(
            verification.get(field) is True
            for field in (
                "task_success",
                "policy_compliance",
                "claim_grounding",
                "invariant_preservation",
                "parser_runtime_validity",
            )
        )
    )


def _markdown(artifact: ModelComparisonArtifact) -> str:
    lines = [
        "# EvalForge Live Model Comparison",
        "",
        f"Equal accepted budget: {artifact.equal_budget_per_source} scenarios per source.",
        "",
        "| Provider / model | Episodes | Task success | Stress success | Unique failures | "
        "Weighted discoveries | FD children | Input tokens | Output tokens | Provider API calls | "
        "Estimated cost | Agent runtime errors |",
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
            "## Runtime-error sensitivity",
            "",
            "Raw rates include every episode. Exclusion-adjusted rates remove provider/API "
            "infrastructure errors only; model protocol errors remain model failures.",
            "",
            "| Provider / model | Infrastructure errors | Protocol errors | Task raw | "
            "Task excl. infra | Stress raw | Stress excl. infra |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in artifact.models:
        lines.append(
            f"| {row.agent} / `{row.model}` | {row.infrastructure_error_episodes} | "
            f"{row.protocol_error_episodes} | {row.task_success_rate:.1%} | "
            f"{row.task_success_rate_excluding_infrastructure_errors:.1%} | "
            f"{row.stress_test_success_rate:.1%} | "
            f"{row.stress_test_success_rate_excluding_infrastructure_errors:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Source-level discovery comparison",
            "",
            "Signatures are deduplicated across models within each source. Success is full "
            "deterministic stress-test success over all model episodes.",
            "",
            "| Source | Success | Unique signatures | Weighted discoveries |",
            "|---|---:|---:|---:|",
        ]
    )
    for source_row in artifact.sources:
        lines.append(
            f"| {source_row.source.replace('_', '-').title()} | "
            f"{source_row.stress_test_success_rate:.1%} | "
            f"{source_row.unique_failure_signatures} | "
            f"{source_row.severity_weighted_discoveries} |"
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
