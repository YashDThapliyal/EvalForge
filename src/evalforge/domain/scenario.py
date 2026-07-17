"""Versioned executable scenario specification."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from evalforge.domain.world import JsonValue, WorldState
from evalforge.simulator.faults import FaultSpec
from evalforge.simulator.tools import tool_schemas


class SourceMethod(StrEnum):
    """Scenario proposal source used in an experiment."""

    MANUAL = "manual"
    RANDOM = "random"
    FAILURE_DIRECTED = "failure_directed"


class PredicateKind(StrEnum):
    """Supported deterministic final-state predicates."""

    SERVICE_HEALTH = "service_health"
    DEPLOYED_VERSION = "deployed_version"
    CONFIG_VALUE = "config_value"
    INCIDENT_EXISTS = "incident_exists"


class Predicate(BaseModel):
    """One machine-checkable desired outcome."""

    model_config = ConfigDict(extra="forbid")

    kind: PredicateKind
    service_id: str
    expected: JsonValue
    key: str | None = None
    severity: str | None = None


class SuccessContract(BaseModel):
    """Outcome and trace requirements for task success."""

    predicates: list[Predicate]
    required_verification_tools: list[str] = Field(default_factory=list)
    require_authorized_mutations: bool = True
    max_tool_calls: int | None = None


class InvariantKind(StrEnum):
    """Supported safety and isolation invariants."""

    NO_UNRELATED_SERVICES_CHANGED = "no_unrelated_services_changed"
    NO_PERMISSION_DENIED_MUTATION = "no_permission_denied_mutation"
    NO_DUPLICATE_INCIDENTS = "no_duplicate_incidents"
    NO_FORBIDDEN_ACTION = "no_forbidden_action"
    ONLY_CONFIG_KEY_CHANGED = "only_config_key_changed"


class InvariantSpec(BaseModel):
    """One machine-checkable protected property."""

    kind: InvariantKind
    allowed_service_ids: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    config_key: str | None = None


class OracleAction(BaseModel):
    """Hidden legal action in the deterministic solvability plan."""

    tool_name: str
    arguments: dict[str, JsonValue]


class PublicScenario(BaseModel):
    """Explicitly filtered request visible to a tested agent."""

    task: str
    agent_identity: str
    tools: list[dict[str, JsonValue]]
    max_agent_steps: int


class ScenarioSpec(BaseModel):
    """Complete private scenario, including oracle and verifier data."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str
    title: str
    task: str
    seed: int
    source_method: SourceMethod
    parent_scenario_id: str | None = None
    parent_failure_signature: str | None = None
    tags: list[str]
    agent_identity: str = "operator"
    initial_world: WorldState
    fault_plan: list[FaultSpec] = Field(default_factory=list)
    oracle_plan: list[OracleAction]
    success_contract: SuccessContract
    invariants: list[InvariantSpec] = Field(default_factory=list)
    max_agent_steps: int = Field(default=10, ge=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    def public_view(self) -> PublicScenario:
        """Return only data explicitly permitted by the agent contract."""

        return PublicScenario(
            task=self.task,
            agent_identity=self.agent_identity,
            tools=tool_schemas(),
            max_agent_steps=self.max_agent_steps,
        )

