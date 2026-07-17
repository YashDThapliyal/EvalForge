"""YAML loading and writing for scenarios and compact manual manifests."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

from evalforge.domain.scenario import ScenarioSpec
from evalforge.scenarios.manual import build_manual_scenario


def load_scenario(path: Path) -> ScenarioSpec:
    """Load one complete versioned scenario YAML file."""

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ScenarioSpec.model_validate(raw)


def write_scenario(path: Path, scenario: ScenarioSpec) -> None:
    """Write a reviewable scenario YAML artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(scenario.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )


def load_scenarios(path: Path) -> list[ScenarioSpec]:
    """Load one scenario, directory of scenarios, or reviewed manual manifest."""

    if path.is_file():
        return _load_path(path)
    scenarios: list[ScenarioSpec] = []
    for child in sorted(path.glob("*.yaml")):
        scenarios.extend(_load_path(child))
    return scenarios


def _load_path(path: Path) -> list[ScenarioSpec]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "manual_scenarios" in raw:
        entries = cast(list[dict[str, object]], raw["manual_scenarios"])
        return [
            build_manual_scenario(str(entry["family"]), int(str(entry["variant"])))
            for entry in entries
        ]
    return [ScenarioSpec.model_validate(raw)]

