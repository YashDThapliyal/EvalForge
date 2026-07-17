"""Canonical exact and structural scenario fingerprints."""

from __future__ import annotations

import hashlib

from evalforge.domain.scenario import ScenarioSpec
from evalforge.serialization import canonical_json


def fingerprint(scenario: ScenarioSpec) -> str:
    """Hash semantically relevant scenario fields, excluding prose and metadata."""

    data = scenario.model_dump(
        mode="json",
        exclude={
            "scenario_id",
            "title",
            "task",
            "metadata",
            "parent_scenario_id",
            "parent_failure_signature",
        },
    )
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()


def near_fingerprint(scenario: ScenarioSpec) -> str:
    """Hash a lightweight normalized behavioral structure."""

    structure = {
        "tags": sorted(scenario.tags),
        "faults": [fault.kind.value for fault in scenario.fault_plan],
        "actions": [action.tool_name for action in scenario.oracle_plan],
        "predicates": [predicate.kind.value for predicate in scenario.success_contract.predicates],
        "invariants": [invariant.kind.value for invariant in scenario.invariants],
    }
    return hashlib.sha256(canonical_json(structure).encode()).hexdigest()
