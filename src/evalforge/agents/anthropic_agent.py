"""Optional Anthropic Messages API tested-agent adapter."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Protocol, cast

from evalforge.agents.base import AgentFinal, AgentRequest, ProviderUsage, ToolRegistry
from evalforge.agents.live_tools import anthropic_submit_final_tool, anthropic_tool
from evalforge.agents.openai_agent import (
    AgentProtocolError,
    LiveConfigurationError,
    _agent_prompt,
    _integer,
    _response_dict,
    _validate_final,
)
from evalforge.domain.world import JsonValue
from evalforge.serialization import canonical_json


class MessagesClient(Protocol):
    """Minimal Anthropic Messages API surface."""

    def create(self, **kwargs: object) -> object:
        """Create one message."""


class AnthropicClient(Protocol):
    """Minimal injectable Anthropic client surface."""

    messages: MessagesClient


class AnthropicAgent:
    """Use Anthropic custom tools and canonical ``tool_result`` continuation messages."""

    def __init__(
        self,
        model: str,
        input_cost_per_million: float,
        cached_input_cost_per_million: float,
        cache_write_cost_per_million: float,
        output_cost_per_million: float,
        client: AnthropicClient | None = None,
        max_output_tokens: int = 4096,
    ):
        if not model.strip():
            raise LiveConfigurationError("Anthropic model must be explicitly configured")
        if client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise LiveConfigurationError(
                    "ANTHROPIC_API_KEY is not set; export it and install the 'live' extra"
                )
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover
                raise LiveConfigurationError(
                    "Install the optional provider dependencies with: uv sync --extra live"
                ) from exc
            client = cast(AnthropicClient, Anthropic(api_key=api_key))
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.input_cost_per_million = input_cost_per_million
        self.cached_input_cost_per_million = cached_input_cost_per_million
        self.cache_write_cost_per_million = cache_write_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.raw_messages: list[str] = []
        self.usage = ProviderUsage(provider="anthropic", model=model)

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Run until Claude calls ``submit_final`` or violates the protocol."""

        provider_tools = [anthropic_tool(item) for item in request.tools]
        provider_tools.append(anthropic_submit_final_tool())
        messages: list[dict[str, object]] = [{"role": "user", "content": _agent_prompt(request)}]
        for _ in range(request.max_agent_steps + 1):
            raw = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=(
                    "You are the tested operations agent. You cannot see hidden simulator state, "
                    "faults, verifier predicates, or actual outcomes. Use only visible tool "
                    "results."
                ),
                messages=deepcopy(messages),
                tools=provider_tools,
                tool_choice={"type": "auto", "disable_parallel_tool_use": True},
            )
            response = _response_dict(raw)
            self.raw_messages.append(canonical_json(cast(JsonValue, response)))
            self._record_usage(response)
            content = response.get("content")
            if not isinstance(content, list):
                raise AgentProtocolError("provider response omitted its content sequence")
            blocks = [
                cast(dict[str, object], block) for block in content if isinstance(block, dict)
            ]
            tool_uses = [block for block in blocks if block.get("type") == "tool_use"]
            if not tool_uses:
                raise AgentProtocolError("malformed final output: submit_final was not called")
            messages.append({"role": "assistant", "content": blocks})
            results: list[dict[str, object]] = []
            for block in tool_uses:
                name = block.get("name")
                use_id = block.get("id")
                arguments = block.get("input")
                if not isinstance(name, str) or not isinstance(use_id, str):
                    raise AgentProtocolError("malformed tool call in provider response")
                if not isinstance(arguments, dict):
                    raise AgentProtocolError("malformed tool arguments from provider")
                if name == "submit_final":
                    return _validate_final(arguments)
                observation = tools.call(name, arguments)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use_id,
                        "content": observation.model_dump_json(),
                    }
                )
            messages.append({"role": "user", "content": results})
        raise AgentProtocolError("provider exceeded the configured maximum step budget")

    def _record_usage(self, response: dict[str, object]) -> None:
        raw_usage = response.get("usage")
        usage = raw_usage if isinstance(raw_usage, dict) else {}
        self.usage.record(
            input_tokens=_integer(usage.get("input_tokens")),
            output_tokens=_integer(usage.get("output_tokens")),
            cached_input_tokens=_integer(usage.get("cache_read_input_tokens")),
            cache_write_input_tokens=_integer(usage.get("cache_creation_input_tokens")),
            input_cost_per_million=self.input_cost_per_million,
            cached_input_cost_per_million=self.cached_input_cost_per_million,
            cache_write_cost_per_million=self.cache_write_cost_per_million,
            output_cost_per_million=self.output_cost_per_million,
        )
