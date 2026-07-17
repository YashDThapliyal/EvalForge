from __future__ import annotations

import json

import pytest

from evalforge.agents.base import AgentRequest, ToolRegistry
from evalforge.agents.openai_agent import AgentProtocolError, LiveConfigurationError, OpenAIAgent
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.simulator.engine import Simulator

PRICING = {
    "input_cost_per_million": 5.0,
    "cached_input_cost_per_million": 0.5,
    "cache_write_cost_per_million": 6.25,
    "output_cost_per_million": 30.0,
}


class FakeResponses:
    def __init__(self, outputs: list[dict[str, object]]):
        self.outputs = outputs
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return self.outputs.pop(0)


class FakeClient:
    def __init__(self, outputs: list[dict[str, object]]):
        self.responses = FakeResponses(outputs)


def test_live_adapter_maps_tools_executes_native_call_and_preserves_raw_messages() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    {"type": "reasoning", "id": "reason-1", "summary": []},
                    {
                        "type": "function_call",
                        "name": "inspect_service",
                        "arguments": json.dumps({"service_id": "payments-api"}),
                        "call_id": "call-1",
                    },
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "input_tokens_details": {"cached_tokens": 10},
                },
            },
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "submit_final",
                        "arguments": json.dumps(
                            {"status": "not_resolved", "summary": "Inspected", "claims": []}
                        ),
                        "call_id": "call-final",
                    }
                ],
                "usage": {"input_tokens": 80, "output_tokens": 10},
            },
        ]
    )
    scenario = build_manual_scenario("bad_deployment", 0)
    request = AgentRequest.model_validate(scenario.public_view().model_dump())
    simulator = Simulator(scenario.initial_world, scenario.fault_plan)
    final = OpenAIAgent(client=client, model="fake-model", **PRICING).run(
        request, ToolRegistry(simulator, "operator", 5)
    )
    assert final.summary == "Inspected"
    assert simulator.events[0].tool_name == "inspect_service"
    tool = client.responses.calls[0]["tools"]
    assert isinstance(tool, list)
    assert tool[0]["type"] == "function"  # type: ignore[index]
    assert tool[0]["parameters"]["type"] == "object"  # type: ignore[index]
    assert tool[-1]["name"] == "submit_final"  # type: ignore[index]
    second_input = client.responses.calls[1]["input"]
    assert isinstance(second_input, list)
    assert any(item.get("type") == "reasoning" for item in second_input)
    assert any(item.get("type") == "function_call_output" for item in second_input)


def test_live_adapter_accounts_for_provider_usage() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "submit_final",
                        "arguments": json.dumps(
                            {"status": "not_resolved", "summary": "Done", "claims": []}
                        ),
                        "call_id": "call-final",
                    }
                ],
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "input_tokens_details": {"cached_tokens": 20},
                },
            }
        ]
    )
    scenario = build_manual_scenario("bad_deployment", 0)
    request = AgentRequest.model_validate(scenario.public_view().model_dump())
    simulator = Simulator(scenario.initial_world, scenario.fault_plan)
    agent = OpenAIAgent(client=client, model="gpt-5.6-sol", **PRICING)
    agent.run(request, ToolRegistry(simulator, "operator", 5))
    assert agent.usage.provider == "openai"
    assert agent.usage.model == "gpt-5.6-sol"
    assert agent.usage.input_tokens == 120
    assert agent.usage.cached_input_tokens == 20
    assert agent.usage.output_tokens == 30
    assert agent.usage.api_calls == 1
    assert agent.usage.estimated_cost_usd == pytest.approx(0.00141)


def test_malformed_live_final_is_structured_and_no_key_message_is_actionable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = FakeClient(
        [
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "submit_final",
                        "arguments": "not-json",
                        "call_id": "call-final",
                    }
                ]
            }
        ]
    )
    scenario = build_manual_scenario("bad_deployment", 0)
    request = AgentRequest.model_validate(scenario.public_view().model_dump())
    tools = ToolRegistry(Simulator(scenario.initial_world), "operator", 2)
    with pytest.raises(AgentProtocolError, match="malformed final"):
        OpenAIAgent(model="fake-model", client=client, **PRICING).run(request, tools)

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LiveConfigurationError, match="OPENAI_API_KEY"):
        OpenAIAgent(model="fake-model", **PRICING)
