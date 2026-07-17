"""Aggregate independent deterministic verifier components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from evalforge.domain.results import VerificationFinding, VerificationResult
from evalforge.domain.scenario import ScenarioSpec
from evalforge.verification.claims import verify_claims
from evalforge.verification.invariants import verify_invariants
from evalforge.verification.outcomes import verify_outcomes
from evalforge.verification.trace_policy import verify_trace_policy

if TYPE_CHECKING:
    from evalforge.execution.episode import EpisodeResult


def verify_episode(scenario: ScenarioSpec, episode: EpisodeResult) -> VerificationResult:
    """Run every verifier and preserve independent pass dimensions."""

    outcome = verify_outcomes(scenario, episode)
    invariants = verify_invariants(scenario, episode)
    policy = verify_trace_policy(scenario, episode)
    claims = verify_claims(episode)
    runtime = _runtime_findings(episode)
    return VerificationResult(
        findings=outcome + invariants + policy + claims + runtime,
        task_success=_passed(outcome),
        policy_compliance=_passed(policy),
        claim_grounding=_passed(claims),
        invariant_preservation=_passed(invariants),
        parser_runtime_validity=_passed(runtime),
    )


def _passed(findings: list[VerificationFinding]) -> bool:
    return all(finding.passed for finding in findings)


def _runtime_findings(episode: EpisodeResult) -> list[VerificationFinding]:
    rule = {
        "budget_exceeded": "TOOL_BUDGET_EXCEEDED",
        "malformed_tool_call": "MALFORMED_TOOL_CALL",
    }.get(episode.runtime_status, "MALFORMED_FINAL_RESULT")
    passed = episode.runtime_status == "valid"
    return [
        VerificationFinding(
            rule_id=rule,
            passed=passed,
            severity="high" if not passed else "info",
            message="Episode runtime valid" if passed else "; ".join(episode.runtime_errors),
            component="runtime",
        )
    ]
