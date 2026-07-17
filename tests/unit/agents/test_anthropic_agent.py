from __future__ import annotations

import pytest

from evalforge.agents.anthropic_agent import AnthropicAgent
from evalforge.agents.base import AgentRequest, ToolRegistry
from evalforge.agents.openai_agent import LiveConfigurationError
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.simulator.engine import Simulator

PRICING = {
    "input_cost_per_million": 5.0,
    "cached_input_cost_per_million": 0.5,
    "cache_write_cost_per_million": 6.25,
    "output_cost_per_million": 25.0,
}


class FakeMessages:
    def __init__(self, outputs: list[dict[str, object]]):
        self.outputs = outputs
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return self.outputs.pop(0)


class FakeClient:
    def __init__(self, outputs: list[dict[str, object]]):
        self.messages = FakeMessages(outputs)


def test_anthropic_agent_uses_canonical_tool_result_loop_and_final_tool() -> None:
    client = FakeClient(
        [
            {
                "content": [
                    {"type": "text", "text": "I will inspect first."},
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "inspect_service",
                        "input": {"service_id": "payments-api"},
                    },
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 90, "output_tokens": 20},
            },
            {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-final",
                        "name": "submit_final",
                        "input": {"status": "not_resolved", "summary": "Inspected", "claims": []},
                    }
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 70, "output_tokens": 15},
            },
        ]
    )
    scenario = build_manual_scenario("bad_deployment", 0)
    request = AgentRequest.model_validate(scenario.public_view().model_dump())
    simulator = Simulator(scenario.initial_world, scenario.fault_plan)
    agent = AnthropicAgent(client=client, model="claude-opus-4-8", **PRICING)
    final = agent.run(request, ToolRegistry(simulator, "operator", 5))

    assert final.summary == "Inspected"
    assert simulator.events[0].tool_name == "inspect_service"
    second_messages = client.messages.calls[1]["messages"]
    assert isinstance(second_messages, list)
    assert second_messages[-2]["role"] == "assistant"
    assert second_messages[-1]["role"] == "user"
    assert second_messages[-1]["content"][0]["type"] == "tool_result"
    provider_tools = client.messages.calls[0]["tools"]
    assert isinstance(provider_tools, list)
    assert provider_tools[-1]["name"] == "submit_final"
    read_logs = next(item for item in provider_tools if item["name"] == "read_logs")
    assert "minimum" not in read_logs["input_schema"]["properties"]["limit"]
    assert "maximum" not in read_logs["input_schema"]["properties"]["limit"]
    assert agent.usage.input_tokens == 160
    assert agent.usage.output_tokens == 35
    assert agent.usage.api_calls == 2
    assert agent.usage.estimated_cost_usd == pytest.approx(0.001675)


def test_anthropic_agent_requires_explicit_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LiveConfigurationError, match="ANTHROPIC_API_KEY"):
        AnthropicAgent(model="fake-model", **PRICING)
