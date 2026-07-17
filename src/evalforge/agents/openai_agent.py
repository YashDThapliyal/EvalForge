"""Optional OpenAI Responses API agent behind a provider-neutral boundary."""

from __future__ import annotations

import json
import os
from typing import Protocol, cast

from evalforge.agents.base import AgentFinal, AgentRequest, ToolRegistry
from evalforge.domain.world import JsonValue
from evalforge.serialization import canonical_json


class AgentProtocolError(ValueError):
    """A provider response violated the tool or final-result protocol."""


class LiveConfigurationError(RuntimeError):
    """Live adapter configuration is absent or unusable."""


class ResponsesClient(Protocol):
    """Minimal Responses API surface used by the adapter."""

    def create(self, **kwargs: object) -> object:
        """Create one response."""


class OpenAIClient(Protocol):
    """Minimal injectable client surface."""

    responses: ResponsesClient


class OpenAIAgent:
    """Use native function calls while exposing only public scenario data."""

    def __init__(
        self,
        client: OpenAIClient | None = None,
        model: str = "gpt-5-mini",
        max_output_size: int = 100_000,
    ):
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LiveConfigurationError(
                    "OPENAI_API_KEY is not set; export it and install the 'openai' extra"
                )
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise LiveConfigurationError(
                    "Install the optional provider dependency with: uv sync --extra openai"
                ) from exc
            client = cast(OpenAIClient, OpenAI(api_key=api_key))
        self.client = client
        self.model = model
        self.max_output_size = max_output_size
        self.raw_messages: list[str] = []

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Iterate native tool calls until a validated structured final is returned."""

        provider_tools = [_provider_tool(item) for item in request.tools]
        messages: list[dict[str, object]] = [
            {
                "role": "user",
                "content": (
                    f"Identity: {request.agent_identity}\nTask: {request.task}\n"
                    "Return only the required structured AgentFinal JSON when done."
                ),
            }
        ]
        for _ in range(request.max_agent_steps + 1):
            raw = self.client.responses.create(
                model=self.model, input=messages, tools=provider_tools
            )
            response = _response_dict(raw)
            self.raw_messages.append(canonical_json(cast(JsonValue, response)))
            output = response.get("output", [])
            calls = (
                [
                    item
                    for item in output
                    if isinstance(item, dict) and item.get("type") == "function_call"
                ]
                if isinstance(output, list)
                else []
            )
            if calls:
                for item in calls:
                    name = item.get("name")
                    call_id = item.get("call_id")
                    arguments_raw = item.get("arguments")
                    if not all(isinstance(value, str) for value in (name, call_id, arguments_raw)):
                        raise AgentProtocolError("malformed tool call in provider response")
                    try:
                        arguments = json.loads(cast(str, arguments_raw))
                    except json.JSONDecodeError as exc:
                        raise AgentProtocolError("malformed tool arguments from provider") from exc
                    observation = tools.call(cast(str, name), arguments)
                    messages.append(cast(dict[str, object], item))
                    messages.append(
                        {
                            "type": "function_call_output",
                            "call_id": cast(str, call_id),
                            "output": observation.model_dump_json(),
                        }
                    )
                continue
            output_text = response.get("output_text")
            if not isinstance(output_text, str) or len(output_text) > self.max_output_size:
                raise AgentProtocolError("malformed final output from provider")
            try:
                final = AgentFinal.model_validate_json(output_text)
            except ValueError as exc:
                raise AgentProtocolError("malformed final output from provider") from exc
            if final.status not in {"resolved", "not_resolved", "escalated"}:
                raise AgentProtocolError("malformed final status from provider")
            return final
        raise AgentProtocolError("provider exceeded the configured maximum step budget")


def _provider_tool(tool: dict[str, JsonValue]) -> dict[str, object]:
    name = tool.get("name")
    description = tool.get("description")
    parameters = tool.get("input_schema")
    if (
        not isinstance(name, str)
        or not isinstance(description, str)
        or not isinstance(parameters, dict)
    ):
        raise AgentProtocolError("public tool schema is malformed")
    return {"type": "function", "name": name, "description": description, "parameters": parameters}


def _response_dict(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return cast(dict[str, object], raw)
    if hasattr(raw, "model_dump"):
        dumped = raw.model_dump(mode="json")
        if isinstance(dumped, dict):
            return cast(dict[str, object], dumped)
    raise AgentProtocolError("provider returned an unsupported response object")
