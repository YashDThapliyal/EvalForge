from __future__ import annotations

from pathlib import Path


def test_golden_heading_contract_is_stable() -> None:
    headings = Path("tests/golden/report_headings.txt").read_text(encoding="utf-8")
    assert headings == (
        "## Experiment configuration\n"
        "## Scenario generation and validation\n"
        "## Source comparison\n"
        "## Success rates\n"
        "## Unique failure discoveries\n"
        "## Severity breakdown\n"
        "## Discovery curves\n"
        "## Top failure modes\n"
        "## Validation rejection reasons\n"
        "## Scenario lineage summary\n"
        "## Limitations\n"
    )
