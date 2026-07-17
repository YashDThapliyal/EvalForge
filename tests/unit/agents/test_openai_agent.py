from __future__ import annotations

import json

import pytest

from evalforge.agents.base import AgentRequest, ToolRegistry
from evalforge.agents.openai_agent import AgentProtocolError, LiveConfigurationError, OpenAIAgent
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.simulator.engine import Simulator


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
                    {
                        "type": "function_call",
                        "name": "inspect_service",
                        "arguments": json.dumps({"service_id": "payments-api"}),
                        "call_id": "call-1",
                    }
                ]
            },
            {
                "output_text": json.dumps(
                    {"status": "not_resolved", "summary": "Inspected", "claims": []}
                )
            },
        ]
    )
    scenario = build_manual_scenario("bad_deployment", 0)
    request = AgentRequest.model_validate(scenario.public_view().model_dump())
    simulator = Simulator(scenario.initial_world, scenario.fault_plan)
    final = OpenAIAgent(client=client, model="fake-model").run(
        request, ToolRegistry(simulator, "operator", 5)
    )
    assert final.summary == "Inspected"
    assert simulator.events[0].tool_name == "inspect_service"
    tool = client.responses.calls[0]["tools"]
    assert isinstance(tool, list)
    assert tool[0]["type"] == "function"  # type: ignore[index]
    assert tool[0]["parameters"]["type"] == "object"  # type: ignore[index]


def test_malformed_live_final_is_structured_and_no_key_message_is_actionable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = FakeClient([{"output_text": "not-json"}])
    scenario = build_manual_scenario("bad_deployment", 0)
    request = AgentRequest.model_validate(scenario.public_view().model_dump())
    tools = ToolRegistry(Simulator(scenario.initial_world), "operator", 2)
    with pytest.raises(AgentProtocolError, match="malformed final"):
        OpenAIAgent(client=client).run(request, tools)

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LiveConfigurationError, match="OPENAI_API_KEY"):
        OpenAIAgent()
