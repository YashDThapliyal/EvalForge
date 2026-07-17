from __future__ import annotations

from evalforge.agents.base import AgentFinal, AgentRequest, ClaimType, FinalClaim, ToolCall
from evalforge.agents.oracle import OracleAgent
from evalforge.agents.replay import ReplayAgent
from evalforge.execution.episode import run_episode
from evalforge.scenarios.manual import build_manual_scenario


def test_oracle_and_replay_agents_execute_declared_calls() -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    oracle_episode = run_episode(scenario, OracleAgent(scenario.oracle_plan))
    replay = ReplayAgent(
        [ToolCall(tool_name=e.tool_name, arguments=e.arguments) for e in oracle_episode.events],
        oracle_episode.final,
    )
    replay_episode = run_episode(scenario, replay)
    assert replay_episode.final_world == oracle_episode.final_world
    assert [e.tool_name for e in replay_episode.events] == [
        e.tool_name for e in oracle_episode.events
    ]


def test_agent_request_cannot_contain_private_scenario_fields() -> None:
    request = AgentRequest.model_validate(
        build_manual_scenario("lost_confirmation", 0).public_view().model_dump()
    )
    text = request.model_dump_json()
    assert "fault_plan" not in text
    assert "oracle_plan" not in text
    assert "initial_world" not in text


def test_structured_final_claim_model() -> None:
    final = AgentFinal(
        status="resolved",
        summary="Service is healthy",
        claims=[
            FinalClaim(
                claim_type=ClaimType.SERVICE_HEALTH,
                service_id="payments-api",
                value="healthy",
            )
        ],
    )
    assert AgentFinal.model_validate_json(final.model_dump_json()) == final
