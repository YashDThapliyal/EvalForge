from __future__ import annotations

from pathlib import Path

from evalforge.execution.demo import run_demo


def test_six_case_demo_runs_real_offline_pipeline(tmp_path: Path) -> None:
    result = run_demo(seed=7, output_dir=tmp_path)
    assert len(result.episodes) == 6
    assert result.failure_signatures
    assert (result.artifact_dir / "report.md").exists()
    assert (result.artifact_dir / "report.html").exists()
    assert "VISIBLE:" in result.example_timeline
    assert "ACTUAL:" in result.example_timeline
