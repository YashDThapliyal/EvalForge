from __future__ import annotations

import json
from pathlib import Path

from evalforge.config import ExperimentConfig
from evalforge.execution.experiment import ExperimentRunner
from evalforge.reporting.html import generate_html_report
from evalforge.reporting.inspect import render_failure_timeline
from evalforge.reporting.markdown import generate_markdown_report


def _experiment(tmp_path: Path) -> Path:
    return (
        ExperimentRunner(ExperimentConfig(seed=7, scenarios_per_source=2, output_dir=str(tmp_path)))
        .run()
        .artifact_dir
    )


def test_reports_regenerate_from_artifacts_with_required_sections(tmp_path: Path) -> None:
    experiment = _experiment(tmp_path)
    markdown = generate_markdown_report(experiment)
    html = generate_html_report(experiment)
    assert markdown == (experiment / "report.md").read_text(encoding="utf-8")
    assert html == (experiment / "report.html").read_text(encoding="utf-8")
    required = (Path("tests/golden/report_headings.txt").read_text(encoding="utf-8")).splitlines()
    assert [line for line in markdown.splitlines() if line.startswith("## ")] == required
    for phrase in ("Manual", "Random", "Failure-directed", "Discovery curves"):
        assert phrase.lower() in markdown.lower()


def test_failure_pages_escape_text_distinguish_truth_and_have_live_links(tmp_path: Path) -> None:
    experiment = _experiment(tmp_path)
    failed = next(path.parent for path in (experiment / "episodes").rglob("failure.json"))
    episode_path = failed / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    episode["public_request"]["task"] = "<script>alert('unsafe')</script>"
    episode_path.write_text(json.dumps(episode), encoding="utf-8")
    generate_html_report(experiment)
    page = experiment / "failures" / f"{failed.name}.html"
    content = page.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in content and "<script>alert" not in content
    assert "Agent-visible observation" in content
    assert "Hidden actual outcome" in content
    assert "State diff" in content
    report = (experiment / "report.html").read_text(encoding="utf-8")
    assert f"failures/{failed.name}.html" in report
    assert page.exists()


def test_terminal_inspection_prints_signature_and_exact_violated_rules(tmp_path: Path) -> None:
    experiment = _experiment(tmp_path)
    failed = next(path.parent for path in (experiment / "episodes").rglob("failure.json"))
    timeline = render_failure_timeline(experiment, failed.name)
    verification = json.loads((failed / "verification.json").read_text(encoding="utf-8"))
    for finding in verification["findings"]:
        if not finding["passed"]:
            assert finding["rule_id"] in timeline
    assert "VISIBLE:" in timeline and "ACTUAL:" in timeline
    assert "FAILURE SIGNATURE:" in timeline
