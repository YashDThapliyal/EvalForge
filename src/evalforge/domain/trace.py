"""Auditable tool execution trace models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from evalforge.domain.world import JsonValue


class OutcomeStatus(StrEnum):
    """Actual simulator outcome status."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class PermissionDecision(BaseModel):
    """Auditable authorization decision made before execution."""

    allowed: bool
    required: str
    reason: str


class ActualOutcome(BaseModel):
    """Hidden truth about what a tool execution did."""

    status: OutcomeStatus
    message: str
    data: dict[str, JsonValue] = Field(default_factory=dict)
    error_code: str | None = None


class ToolObservation(BaseModel):
    """Only the structured fields returned to a tested agent."""

    model_config = ConfigDict(extra="forbid")

    status: str
    message: str
    data: dict[str, JsonValue] = Field(default_factory=dict)


class StateChange(BaseModel):
    """One canonical path-level state change."""

    path: str
    before: JsonValue = None
    after: JsonValue = None


class StateDiff(BaseModel):
    """Stable list of changes between world snapshots."""

    changes: list[StateChange] = Field(default_factory=list)


class ToolEvent(BaseModel):
    """Complete actual-versus-visible execution event."""

    call_id: str
    step_index: int
    tool_name: str
    arguments: dict[str, JsonValue]
    actor_id: str
    permission_decision: PermissionDecision
    actual_outcome: ActualOutcome
    visible_observation: ToolObservation
    state_before_hash: str
    state_after_hash: str
    state_diff: StateDiff
    side_effect_id: str | None = None
    fault_ids_applied: list[str] = Field(default_factory=list)

