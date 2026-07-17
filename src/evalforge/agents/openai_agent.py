"""Optional OpenAI Responses API agent behind a provider-neutral boundary."""

from __future__ import annotations

import json
import os
from typing import Protocol, cast

from evalforge.agents.base import AgentFinal, AgentRequest, ProviderUsage, ToolRegistry
from evalforge.agents.live_tools import provider_tool, submit_final_tool
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
    """Use Responses API function calls while exposing only public scenario data."""

    def __init__(
        self,
        model: str,
        input_cost_per_million: float,
        cached_input_cost_per_million: float,
        cache_write_cost_per_million: float,
        output_cost_per_million: float,
        client: OpenAIClient | None = None,
        max_output_tokens: int = 4096,
    ):
        if not model.strip():
            raise LiveConfigurationError("OpenAI model must be explicitly configured")
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LiveConfigurationError(
                    "OPENAI_API_KEY is not set; export it and install the 'live' extra"
                )
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise LiveConfigurationError(
                    "Install the optional provider dependencies with: uv sync --extra live"
                ) from exc
            client = cast(OpenAIClient, OpenAI(api_key=api_key))
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.input_cost_per_million = input_cost_per_million
        self.cached_input_cost_per_million = cached_input_cost_per_million
        self.cache_write_cost_per_million = cache_write_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.raw_messages: list[str] = []
        self.usage = ProviderUsage(provider="openai", model=model)

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Iterate native tool calls until the model calls ``submit_final``."""

        provider_tools = [provider_tool(item, strict=True) for item in request.tools]
        provider_tools.append(submit_final_tool(strict=True))
        input_items: list[object] = [
            {
                "role": "user",
                "content": _agent_prompt(request),
            }
        ]
        for _ in range(request.max_agent_steps + 1):
            raw = self.client.responses.create(
                model=self.model,
                input=list(input_items),
                tools=provider_tools,
                parallel_tool_calls=False,
                max_output_tokens=self.max_output_tokens,
            )
            response = _response_dict(raw)
            self.raw_messages.append(canonical_json(cast(JsonValue, response)))
            self._record_usage(response)
            output = response.get("output")
            if not isinstance(output, list):
                raise AgentProtocolError("provider response omitted its output sequence")
            output_items = [
                cast(dict[str, object], item) for item in output if isinstance(item, dict)
            ]
            native_output = getattr(raw, "output", None)
            continuation = native_output if isinstance(native_output, list) else output_items
            input_items.extend(continuation)
            calls = [item for item in output_items if item.get("type") == "function_call"]
            if not calls:
                raise AgentProtocolError("malformed final output: submit_final was not called")
            for item in calls:
                name = item.get("name")
                call_id = item.get("call_id")
                arguments_raw = item.get("arguments")
                if not all(isinstance(value, str) for value in (name, call_id, arguments_raw)):
                    raise AgentProtocolError("malformed tool call in provider response")
                try:
                    arguments = json.loads(cast(str, arguments_raw))
                except json.JSONDecodeError as exc:
                    label = "final output" if name == "submit_final" else "tool arguments"
                    raise AgentProtocolError(f"malformed {label} from provider") from exc
                if not isinstance(arguments, dict):
                    raise AgentProtocolError("malformed tool arguments from provider")
                if name == "submit_final":
                    return _validate_final(arguments)
                observation = tools.call(cast(str, name), arguments)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": cast(str, call_id),
                        "output": observation.model_dump_json(),
                    }
                )
        raise AgentProtocolError("provider exceeded the configured maximum step budget")

    def _record_usage(self, response: dict[str, object]) -> None:
        raw_usage = response.get("usage")
        usage = raw_usage if isinstance(raw_usage, dict) else {}
        details_raw = usage.get("input_tokens_details")
        details = details_raw if isinstance(details_raw, dict) else {}
        self.usage.record(
            input_tokens=_integer(usage.get("input_tokens")),
            output_tokens=_integer(usage.get("output_tokens")),
            cached_input_tokens=_integer(details.get("cached_tokens")),
            input_cost_per_million=self.input_cost_per_million,
            cached_input_cost_per_million=self.cached_input_cost_per_million,
            cache_write_cost_per_million=self.cache_write_cost_per_million,
            output_cost_per_million=self.output_cost_per_million,
        )


def _agent_prompt(request: AgentRequest) -> str:
    return (
        f"Identity: {request.agent_identity}\nTask: {request.task}\n\n"
        "Operate only through the supplied tools. Treat uncertain or ambiguous mutation results "
        "as unresolved until you verify state with a read. Use idempotency keys for safe retries "
        "and do not blindly retry unkeyed incident creation. Never invent tool outcomes. When you "
        "are done, call submit_final exactly once with claims about final/current state and "
        "actions that actually succeeded. Omit historical pre-remediation state. Do not answer "
        "in prose."
    )


def _validate_final(arguments: dict[str, object]) -> AgentFinal:
    try:
        final = AgentFinal.model_validate(arguments)
    except ValueError as exc:
        raise AgentProtocolError("malformed final output from provider") from exc
    if final.status not in {"resolved", "not_resolved", "escalated"}:
        raise AgentProtocolError("malformed final status from provider")
    return final


def _response_dict(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return cast(dict[str, object], raw)
    if hasattr(raw, "model_dump"):
        dumped = raw.model_dump(mode="json")
        if isinstance(dumped, dict):
            return cast(dict[str, object], dumped)
    raise AgentProtocolError("provider returned an unsupported response object")


def _integer(value: object) -> int:
    return value if isinstance(value, int) else 0
