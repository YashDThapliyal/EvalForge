"""Deterministic verifier result models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from evalforge.domain.world import JsonValue


class VerificationFinding(BaseModel):
    """One independently checkable rule result with trace evidence."""

    rule_id: str
    passed: bool
    severity: Literal["info", "low", "medium", "high", "critical"]
    message: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    expected: JsonValue = None
    actual: JsonValue = None
    component: Literal["outcome", "invariant", "trace_policy", "claims", "runtime"]


class VerificationResult(BaseModel):
    """Aggregated deterministic verification dimensions."""

    findings: list[VerificationFinding]
    task_success: bool
    policy_compliance: bool
    claim_grounding: bool
    invariant_preservation: bool
    parser_runtime_validity: bool

    @property
    def success(self) -> bool:
        """Return true only when every independent dimension passes."""

        return (
            self.task_success
            and self.policy_compliance
            and self.claim_grounding
            and self.invariant_preservation
            and self.parser_runtime_validity
        )

    @property
    def failed_findings(self) -> list[VerificationFinding]:
        """Return only violated rules."""

        return [finding for finding in self.findings if not finding.passed]
