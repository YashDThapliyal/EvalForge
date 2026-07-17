"""Provider-neutral tested-agent contract and bounded tool access."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict

from evalforge.domain.trace import ToolObservation
from evalforge.domain.world import JsonValue
from evalforge.simulator.engine import Simulator


class ClaimType(StrEnum):
    """Deterministically verifiable final claim types."""

    SERVICE_HEALTH = "service_health"
    DEPLOYED_VERSION = "deployed_version"
    CONFIG_VALUE = "config_value"
    INCIDENT_OPENED = "incident_opened"
    ACTION_SUCCEEDED = "action_succeeded"
    PERMISSION_LIMITATION = "permission_limitation"
    UNRESOLVED_UNCERTAINTY = "unresolved_uncertainty"


class FinalClaim(BaseModel):
    """One structured assertion in an agent's final response."""

    model_config = ConfigDict(extra="forbid")

    claim_type: ClaimType
    service_id: str | None = None
    tool_name: str | None = None
    key: str | None = None
    value: JsonValue = None


class AgentFinal(BaseModel):
    """Required structured terminal response from every agent."""

    model_config = ConfigDict(extra="forbid")

    status: str
    summary: str
    claims: list[FinalClaim]


class AgentRequest(BaseModel):
    """The complete and only scenario context shown to a tested agent."""

    model_config = ConfigDict(extra="forbid")

    task: str
    agent_identity: str
    tools: list[dict[str, JsonValue]]
    max_agent_steps: int


class ToolCall(BaseModel):
    """Stored provider-neutral tool call used by replay agents."""

    tool_name: str
    arguments: dict[str, JsonValue]


class ToolRegistry:
    """Bounded agent-facing access to visible simulator observations."""

    def __init__(
        self,
        simulator: Simulator,
        actor_id: str,
        max_calls: int,
        max_malformed: int = 2,
        max_repeated: int = 3,
    ):
        self.simulator = simulator
        self.actor_id = actor_id
        self.max_calls = max_calls
        self.max_malformed = max_malformed
        self.max_repeated = max_repeated
        self.malformed_calls = 0
        self.budget_exceeded = False
        self.repeated_call_limit_exceeded = False
        self._calls: Counter[str] = Counter()

    def call(self, tool_name: str, arguments: object) -> ToolObservation:
        """Execute one well-formed call and expose only its visible observation."""

        if not isinstance(arguments, dict) or not all(isinstance(key, str) for key in arguments):
            self.malformed_calls += 1
            return ToolObservation(
                status="error", message="Malformed tool arguments: expected an object"
            )
        if len(self.simulator.events) >= self.max_calls:
            self.budget_exceeded = True
            return ToolObservation(status="error", message="Tool-call budget exceeded")
        json_arguments = cast(dict[str, JsonValue], arguments)
        signature = f"{tool_name}:{json_arguments!r}"
        self._calls[signature] += 1
        if self._calls[signature] > self.max_repeated:
            self.repeated_call_limit_exceeded = True
            return ToolObservation(status="error", message="Repeated-call limit exceeded")
        return self.simulator.execute(self.actor_id, tool_name, json_arguments).visible_observation


class Agent(Protocol):
    """Provider-neutral agent interface."""

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Interact through tools and return a structured terminal result."""
