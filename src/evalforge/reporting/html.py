"""Escaped static HTML experiment and per-failure reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from jinja2 import Environment

from evalforge.execution.artifacts import atomic_write
from evalforge.reporting.markdown import SOURCE_LABELS, SOURCE_ORDER, generate_markdown_report
from evalforge.reporting.metrics import ExperimentMetrics

ENV = Environment(autoescape=True)
STYLE = """
body{font:15px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18202a}
table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ccd3da;padding:.5rem;text-align:left}
th{background:#eef2f5}pre{background:#f6f8fa;padding:1rem;overflow:auto;white-space:pre-wrap}
.visible{border-left:4px solid #2374ab}.actual{border-left:4px solid #b42318}.diff{border-left:4px solid #7a5c00}
.hidden{background:#fff4e5;padding:1rem}.fail{color:#b42318}a{color:#075da8}
"""

REPORT_TEMPLATE = ENV.from_string(
    """<!doctype html><html><head><meta charset="utf-8"><title>EvalForge report</title>
<style>{{ style }}</style></head><body><h1>EvalForge Experiment Report</h1>
<p>Experiment <code>{{ manifest.experiment_id }}</code>; tested agent <code>{{ manifest.agent }}</code>; model <code>{{ manifest.model }}</code>.</p>
<h2>Three-source comparison</h2><table><thead><tr><th>Source</th><th>Evaluated</th><th>Stress success</th><th>Unique failures</th><th>Weighted discoveries</th></tr></thead><tbody>
{% for row in rows %}<tr><td>{{ row.label }}</td><td>{{ row.evaluated }}</td><td>{{ row.success }}</td><td>{{ row.unique }}</td><td>{{ row.weighted }}</td></tr>{% endfor %}
</tbody></table><h2>Discovery curves</h2>{% for row in rows %}<p>{{ row.label }}: <code>{{ row.curve }}</code></p>{% endfor %}
<h2>Failed episodes</h2><ul>{% for failure in failures %}<li><a href="failures/{{ failure }}.html">{{ failure }}</a></li>{% endfor %}</ul>
<h2>Full Markdown report</h2><pre>{{ markdown }}</pre></body></html>"""
)

FAILURE_TEMPLATE = ENV.from_string(
    """<!doctype html><html><head><meta charset="utf-8"><title>{{ episode.episode_id }}</title><style>{{ style }}</style></head><body>
<p><a href="../report.html">Back to experiment</a></p><h1>Failure {{ episode.episode_id }}</h1>
<h2>Starting environment</h2><pre>{{ starting }}</pre><h2>Agent-visible task</h2><pre>{{ episode.public_request.task }}</pre>
<section class="hidden"><h2>Hidden scenario metadata (never shown to agent)</h2><pre>{{ hidden }}</pre></section>
<h2>Chronological tool trace</h2>{% for event in episode.events %}<article><h3>{{ event.step_index }}. {{ event.tool_name }} <code>{{ event.call_id }}</code></h3>
<pre>Arguments: {{ event.arguments }}</pre><pre class="visible">Agent-visible observation: {{ event.visible_observation }}</pre>
<pre class="actual">Hidden actual outcome: {{ event.actual_outcome }}</pre><pre class="diff">State diff: {{ event.state_diff }}</pre></article>{% endfor %}
<h2>Final environment</h2><pre>{{ final_world }}</pre><h2>Final agent result</h2><pre>{{ final }}</pre>
<h2>Verifier findings and exact violated rules</h2><ul>{% for finding in failed_findings %}<li class="fail"><code>{{ finding.rule_id }}</code>: {{ finding.message }} (events {{ finding.evidence_event_ids }})</li>{% endfor %}</ul>
<h2>Failure signature</h2><pre>{{ failure.canonical_signature }}</pre><h2>Lineage</h2><pre>parent={{ failure.parent_scenario_id }} target={{ failure.parent_failure_signature }}</pre>
</body></html>"""
)


def generate_html_report(experiment: Path) -> str:
    """Generate the escaped comparison report and one page per failed episode."""

    markdown = generate_markdown_report(experiment)
    manifest = _json(experiment / "manifest.json")
    metrics = ExperimentMetrics.model_validate(_json(experiment / "metrics.json"))
    failures = [
        path.parent.name for path in sorted((experiment / "episodes").rglob("failure.json"))
    ]
    rows = []
    for source in SOURCE_ORDER:
        item = metrics.sources[source]
        rows.append(
            {
                "label": SOURCE_LABELS[source],
                "evaluated": item.evaluated,
                "success": f"{item.stress_test_success_rate:.1%}",
                "unique": item.unique_failure_signatures,
                "weighted": item.severity_weighted_discoveries,
                "curve": ", ".join(str(value) for value in item.discovery_curve),
            }
        )
    html = REPORT_TEMPLATE.render(
        style=STYLE, manifest=manifest, rows=rows, failures=failures, markdown=markdown
    )
    atomic_write(experiment / "report.html", html)
    failure_dir = experiment / "failures"
    for episode_id in failures:
        episode_dir = experiment / "episodes" / episode_id
        episode = _json(episode_dir / "episode.json")
        scenario = (episode_dir / "scenario.yaml").read_text(encoding="utf-8")
        verification = _json(episode_dir / "verification.json")
        failure = _json(episode_dir / "failure.json")
        page = FAILURE_TEMPLATE.render(
            style=STYLE,
            episode=episode,
            starting=json.dumps(episode["starting_world"], indent=2, sort_keys=True),
            hidden=scenario,
            final_world=json.dumps(episode["final_world"], indent=2, sort_keys=True),
            final=json.dumps(episode["final"], indent=2, sort_keys=True),
            failed_findings=[
                item
                for item in cast(list[dict[str, object]], verification["findings"])
                if not item["passed"]
            ],
            failure=failure,
        )
        atomic_write(failure_dir / f"{episode_id}.html", page)
    return html


def _json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
