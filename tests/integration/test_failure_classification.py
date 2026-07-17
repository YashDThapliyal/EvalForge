from __future__ import annotations

from evalforge.agents.base import AgentFinal, ClaimType, FinalClaim, ToolCall
from evalforge.agents.replay import ReplayAgent
from evalforge.execution.episode import run_episode
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.verification.engine import verify_episode
from evalforge.verification.taxonomy import classify_failure


def test_superficial_variants_share_signature_but_material_failures_do_not() -> None:
    records = []
    for variant in (0, 1):
        scenario = build_manual_scenario("lost_confirmation", variant)
        episode = run_episode(
            scenario,
            ReplayAgent(
                [ToolCall(tool_name="restart_service", arguments={"service_id": "payments-api"})],
                AgentFinal(
                    status="resolved",
                    summary="Restarted",
                    claims=[
                        FinalClaim(
                            claim_type=ClaimType.SERVICE_HEALTH,
                            service_id="payments-api",
                            value="healthy",
                        )
                    ],
                ),
            ),
        )
        record = classify_failure(scenario, episode, verify_episode(scenario, episode))
        assert record is not None
        records.append(record)
    assert records[0].canonical_signature == records[1].canonical_signature

    different = build_manual_scenario("non_idempotent_incident", 0)
    incident_args = {
        "service_id": "payments-api",
        "severity": "high",
        "summary": "Production issue requires attention",
    }
    episode = run_episode(
        different,
        ReplayAgent(
            [
                ToolCall(tool_name="open_incident", arguments=incident_args),
                ToolCall(tool_name="open_incident", arguments=incident_args),
            ],
            AgentFinal(status="escalated", summary="Opened incidents", claims=[]),
        ),
    )
    record = classify_failure(different, episode, verify_episode(different, episode))
    assert record is not None
    assert record.canonical_signature != records[0].canonical_signature
