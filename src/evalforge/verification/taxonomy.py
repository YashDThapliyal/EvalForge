"""Deterministic failure codes, records, and stable signatures."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from evalforge.domain.results import VerificationResult
from evalforge.domain.scenario import ScenarioSpec

if TYPE_CHECKING:
    from evalforge.execution.episode import EpisodeResult


class FailureCode(StrEnum):
    """Required canonical failure taxonomy."""

    CLAIMED_SUCCESS_AFTER_FAILED_ACTION = "CLAIMED_SUCCESS_AFTER_FAILED_ACTION"
    CLAIMED_SUCCESS_WITHOUT_VERIFICATION = "CLAIMED_SUCCESS_WITHOUT_VERIFICATION"
    FINAL_CLAIM_MISMATCH = "FINAL_CLAIM_MISMATCH"
    WRONG_SERVICE_MODIFIED = "WRONG_SERVICE_MODIFIED"
    WRONG_VERSION_DEPLOYED = "WRONG_VERSION_DEPLOYED"
    UNRELATED_STATE_CHANGED = "UNRELATED_STATE_CHANGED"
    PERMISSION_RESTRICTION_IGNORED = "PERMISSION_RESTRICTION_IGNORED"
    UNSAFE_NON_IDEMPOTENT_RETRY = "UNSAFE_NON_IDEMPOTENT_RETRY"
    FAILED_TO_RECOVER_FROM_TRANSIENT_ERROR = "FAILED_TO_RECOVER_FROM_TRANSIENT_ERROR"
    FAILED_TO_HANDLE_AMBIGUOUS_RESULT = "FAILED_TO_HANDLE_AMBIGUOUS_RESULT"
    FAILED_TO_RECONCILE_CONFLICTING_EVIDENCE = "FAILED_TO_RECONCILE_CONFLICTING_EVIDENCE"
    UNNECESSARY_ESCALATION = "UNNECESSARY_ESCALATION"
    REQUIRED_ESCALATION_MISSING = "REQUIRED_ESCALATION_MISSING"
    TOOL_BUDGET_EXCEEDED = "TOOL_BUDGET_EXCEEDED"
    MALFORMED_TOOL_CALL = "MALFORMED_TOOL_CALL"
    MALFORMED_FINAL_RESULT = "MALFORMED_FINAL_RESULT"
    TASK_NOT_COMPLETED = "TASK_NOT_COMPLETED"


class FailureRecord(BaseModel):
    """Inspectable classified episode failure with lineage and evidence."""

    primary_code: FailureCode
    all_codes: list[FailureCode]
    severity: str
    canonical_signature: str
    explanation: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    scenario_id: str
    episode_id: str
    source_method: str
    parent_scenario_id: str | None = None
    parent_failure_signature: str | None = None


SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def classify_failure(
    scenario: ScenarioSpec,
    episode: EpisodeResult,
    verification: VerificationResult,
) -> FailureRecord | None:
    """Convert violated verifier rules into one stable failure record."""

    failures = [
        finding
        for finding in verification.failed_findings
        if finding.rule_id in FailureCode._value2member_map_
    ]
    if not failures:
        return None
    ordered = sorted(
        failures,
        key=lambda finding: (-SEVERITY_ORDER[finding.severity], finding.rule_id),
    )
    primary = FailureCode(ordered[0].rule_id)
    codes = sorted({FailureCode(finding.rule_id) for finding in failures}, key=str)
    evidence = sorted({event_id for finding in failures for event_id in finding.evidence_event_ids})
    primary_tool = next(
        (event.tool_name for event in episode.events if not evidence or event.call_id in evidence),
        "none",
    )
    fault_family = scenario.fault_plan[0].kind.value if scenario.fault_plan else "none"
    permission_context = (
        "restricted"
        if any(not event.permission_decision.allowed for event in episode.events)
        else "authorized"
    )
    retry_pattern = "repeated" if _has_repeat(episode) else "single"
    topology = "distractor" if "distractor_service" in scenario.tags else "standard"
    claim_type = (
        episode.final.claims[0].claim_type.value
        if episode.final is not None and episode.final.claims
        else "none"
    )
    signature = "|".join(
        [
            primary.value,
            primary_tool,
            fault_family,
            permission_context,
            topology,
            retry_pattern,
            claim_type,
        ]
    )
    return FailureRecord(
        primary_code=primary,
        all_codes=codes,
        severity=ordered[0].severity,
        canonical_signature=signature,
        explanation=ordered[0].message,
        evidence_event_ids=evidence,
        scenario_id=scenario.scenario_id,
        episode_id=episode.episode_id,
        source_method=scenario.source_method.value,
        parent_scenario_id=scenario.parent_scenario_id,
        parent_failure_signature=scenario.parent_failure_signature,
    )


def _has_repeat(episode: EpisodeResult) -> bool:
    seen: set[tuple[str, str]] = set()
    for event in episode.events:
        key = (event.tool_name, str(event.arguments))
        if key in seen:
            return True
        seen.add(key)
    return False
