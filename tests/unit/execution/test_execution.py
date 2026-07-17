from __future__ import annotations

from pathlib import Path

from evalforge.agents.base import AgentFinal, AgentRequest, ToolRegistry
from evalforge.execution.episode import run_episode
from evalforge.scenarios.manual import build_manual_scenario


class InspectingAgent:
    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        assert "private" not in request.model_dump_json()
        tools.call("inspect_service", {"service_id": "payments-api"})
        tools.call("inspect_service", {"service_id": "checkout-api"})
        return AgentFinal(status="not_resolved", summary="Inspected", claims=[])


class OverBudgetAgent:
    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        del request
        for _ in range(20):
            tools.call("inspect_service", {"service_id": "payments-api"})
        return AgentFinal(status="not_resolved", summary="Exceeded", claims=[])


class MalformedAgent:
    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        del request
        tools.call("restart_service", "not-an-object")
        return AgentFinal(status="not_resolved", summary="Malformed", claims=[])


def test_ordered_complete_trace_and_artifact_persistence(tmp_path: Path) -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    episode = run_episode(scenario, InspectingAgent(), artifact_dir=tmp_path)
    assert [event.step_index for event in episode.events] == [1, 2]
    assert all(event.actual_outcome and event.visible_observation for event in episode.events)
    trace = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    assert '"actual_outcome"' in trace and '"visible_observation"' in trace
    assert (tmp_path / "scenario.yaml").exists()
    assert (tmp_path / "public_request.json").exists()
    assert (tmp_path / "verification.json").exists()
    assert "fault_plan" not in (tmp_path / "public_request.json").read_text(encoding="utf-8")


def test_episode_world_isolation() -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    first = run_episode(scenario, InspectingAgent())
    first.final_world.services["payments-api"].health = "invented"
    second = run_episode(scenario, InspectingAgent())
    assert second.starting_world == scenario.initial_world
    assert second.final_world.services["payments-api"].health == "unhealthy"


def test_budget_and_malformed_calls_become_structured_outcomes() -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    scenario.max_agent_steps = 2
    budget = run_episode(scenario, OverBudgetAgent())
    assert budget.runtime_status == "budget_exceeded"
    assert len(budget.events) == 2

    malformed = run_episode(scenario, MalformedAgent())
    assert malformed.runtime_status == "malformed_tool_call"
    assert malformed.malformed_calls == 1
