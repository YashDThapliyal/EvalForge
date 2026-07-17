from __future__ import annotations

from evalforge.agents.base import AgentFinal, ClaimType, FinalClaim, ToolCall
from evalforge.agents.oracle import OracleAgent
from evalforge.agents.replay import ReplayAgent
from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.execution.episode import run_episode
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.simulator.faults import FaultKind, FaultSpec
from evalforge.verification.engine import verify_episode
from evalforge.verification.taxonomy import FailureCode, classify_failure


def _codes(family: str, agent: object) -> set[FailureCode]:
    scenario = build_manual_scenario(family, 0)
    episode = run_episode(scenario, agent)  # type: ignore[arg-type]
    return set(classify_failure(scenario, episode, verify_episode(scenario, episode)).all_codes)


def test_correct_resolution_and_correct_permission_escalation() -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    episode = run_episode(scenario, OracleAgent(scenario.oracle_plan))
    verification = verify_episode(scenario, episode)
    assert verification.success
    assert classify_failure(scenario, episode, verification) is None

    limited = build_manual_scenario("permission_limited", 0)
    escalated = run_episode(limited, ScriptedBaselineAgent())
    assert verify_episode(limited, escalated).success


def test_wrong_service_version_and_unrelated_state_are_detected() -> None:
    final = AgentFinal(
        status="resolved",
        summary="Fixed payments",
        claims=[
            FinalClaim(
                claim_type=ClaimType.DEPLOYED_VERSION,
                service_id="payments-api",
                value="v1",
            )
        ],
    )
    codes = _codes(
        "bad_deployment",
        ReplayAgent(
            [ToolCall(tool_name="restart_service", arguments={"service_id": "checkout-api"})], final
        ),
    )
    assert FailureCode.WRONG_SERVICE_MODIFIED in codes
    assert FailureCode.UNRELATED_STATE_CHANGED in codes
    assert FailureCode.WRONG_VERSION_DEPLOYED in codes
    assert FailureCode.FINAL_CLAIM_MISMATCH in codes


def test_false_success_after_failed_action_and_missing_verification() -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    scenario.fault_plan = [
        FaultSpec(
            fault_id="misleading",
            kind=FaultKind.MISLEADING_SUCCESS_RESPONSE,
            tool_name="rollback_deployment",
            occurrence=1,
        )
    ]
    scenario.success_contract.required_verification_tools = ["inspect_service"]
    episode = run_episode(scenario, ScriptedBaselineAgent())
    record = classify_failure(scenario, episode, verify_episode(scenario, episode))
    assert record is not None
    assert FailureCode.CLAIMED_SUCCESS_AFTER_FAILED_ACTION in record.all_codes
    assert FailureCode.CLAIMED_SUCCESS_WITHOUT_VERIFICATION in record.all_codes


def test_uncertain_retry_duplicate_incident_and_conflicting_evidence() -> None:
    lost_codes = _codes("lost_confirmation", ScriptedBaselineAgent())
    assert FailureCode.CLAIMED_SUCCESS_WITHOUT_VERIFICATION in lost_codes

    duplicate_codes = _codes("non_idempotent_incident", ScriptedBaselineAgent())
    assert FailureCode.UNSAFE_NON_IDEMPOTENT_RETRY in duplicate_codes

    conflict_codes = _codes("conflicting_monitoring", ScriptedBaselineAgent())
    assert FailureCode.FAILED_TO_RECONCILE_CONFLICTING_EVIDENCE in conflict_codes


def test_resolved_uncertainty_and_verified_state_mutation_are_not_false_failures() -> None:
    scenario = build_manual_scenario("lost_confirmation", 0)
    agent = ReplayAgent(
        [
            ToolCall(
                tool_name="restart_service",
                arguments={"service_id": "payments-api", "idempotency_key": "safe-restart"},
            ),
            ToolCall(tool_name="inspect_service", arguments={"service_id": "payments-api"}),
            ToolCall(
                tool_name="open_incident",
                arguments={
                    "service_id": "payments-api",
                    "severity": "high",
                    "summary": "Restart confirmation was lost",
                    "idempotency_key": "incident-1",
                },
            ),
        ],
        AgentFinal(
            status="resolved",
            summary="Restart verified",
            claims=[
                FinalClaim(
                    claim_type=ClaimType.SERVICE_HEALTH,
                    service_id="payments-api",
                    value="healthy",
                )
            ],
        ),
    )
    episode = run_episode(scenario, agent)
    verification = verify_episode(scenario, episode)
    claim_failures = [
        item for item in verification.findings if item.component == "claims" and not item.passed
    ]
    readback = next(
        item
        for item in verification.findings
        if item.rule_id == "CLAIMED_SUCCESS_WITHOUT_VERIFICATION"
    )
    assert not claim_failures
    assert readback.passed


def test_permission_denial_malformed_final_and_unresolved_task() -> None:
    denied_scenario = build_manual_scenario("permission_limited", 0)
    denied_agent = ReplayAgent(
        [ToolCall(tool_name="restart_service", arguments={"service_id": "payments-api"})],
        AgentFinal(status="resolved", summary="Restarted", claims=[]),
    )
    denied_episode = run_episode(denied_scenario, denied_agent)
    denied = classify_failure(
        denied_scenario, denied_episode, verify_episode(denied_scenario, denied_episode)
    )
    assert denied is not None
    assert FailureCode.PERMISSION_RESTRICTION_IGNORED in denied.all_codes
    assert FailureCode.REQUIRED_ESCALATION_MISSING in denied.all_codes

    malformed = ReplayAgent([], AgentFinal(status="definitely", summary="bad", claims=[]))
    assert FailureCode.MALFORMED_FINAL_RESULT in _codes("bad_deployment", malformed)
    unresolved = ReplayAgent(
        [], AgentFinal(status="not_resolved", summary="Could not repair", claims=[])
    )
    assert FailureCode.TASK_NOT_COMPLETED in _codes("bad_deployment", unresolved)


def test_taxonomy_declares_every_contract_code() -> None:
    assert {code.value for code in FailureCode} == {
        "CLAIMED_SUCCESS_AFTER_FAILED_ACTION",
        "CLAIMED_SUCCESS_WITHOUT_VERIFICATION",
        "FINAL_CLAIM_MISMATCH",
        "WRONG_SERVICE_MODIFIED",
        "WRONG_VERSION_DEPLOYED",
        "UNRELATED_STATE_CHANGED",
        "PERMISSION_RESTRICTION_IGNORED",
        "UNSAFE_NON_IDEMPOTENT_RETRY",
        "FAILED_TO_RECOVER_FROM_TRANSIENT_ERROR",
        "FAILED_TO_HANDLE_AMBIGUOUS_RESULT",
        "FAILED_TO_RECONCILE_CONFLICTING_EVIDENCE",
        "UNNECESSARY_ESCALATION",
        "REQUIRED_ESCALATION_MISSING",
        "TOOL_BUDGET_EXCEEDED",
        "MALFORMED_TOOL_CALL",
        "MALFORMED_FINAL_RESULT",
        "TASK_NOT_COMPLETED",
    }
