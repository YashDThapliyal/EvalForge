"""Scenario-controlled deterministic fault declarations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from evalforge.domain.world import JsonValue


class FaultKind(StrEnum):
    """Supported actual and observation fault families."""

    ACTION_FAILS = "ACTION_FAILS"
    CONFIRMATION_LOST = "CONFIRMATION_LOST"
    AMBIGUOUS_RESPONSE = "AMBIGUOUS_RESPONSE"
    STALE_READ = "STALE_READ"
    MISLEADING_SUCCESS_RESPONSE = "MISLEADING_SUCCESS_RESPONSE"
    TRANSIENT_FAILURE_THEN_SUCCESS = "TRANSIENT_FAILURE_THEN_SUCCESS"
    CONFLICTING_MONITORING = "CONFLICTING_MONITORING"
    PARTIAL_SIDE_EFFECT = "PARTIAL_SIDE_EFFECT"


class FaultSpec(BaseModel):
    """Precisely triggered fault controlled by scenario data."""

    model_config = ConfigDict(extra="forbid")

    fault_id: str
    kind: FaultKind
    tool_name: str
    matching_arguments: dict[str, JsonValue] = Field(default_factory=dict)
    occurrence: int = Field(default=1, ge=1)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)

    def matches(self, tool_name: str, arguments: dict[str, JsonValue], occurrence: int) -> bool:
        """Return whether a call activates this fault."""

        return (
            self.tool_name == tool_name
            and self.occurrence == occurrence
            and all(arguments.get(key) == value for key, value in self.matching_arguments.items())
        )
