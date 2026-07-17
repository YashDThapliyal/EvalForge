"""Run one isolated tested-agent episode and persist a reconstructable trace."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from pydantic import BaseModel, Field

from evalforge.agents.base import Agent, AgentFinal, AgentRequest, ProviderUsage, ToolRegistry
from evalforge.domain.results import VerificationResult
from evalforge.domain.scenario import ScenarioSpec
from evalforge.domain.trace import ToolEvent
from evalforge.domain.world import WorldState
from evalforge.execution.artifacts import atomic_write
from evalforge.scenarios.loader import write_scenario
from evalforge.serialization import canonical_json
from evalforge.simulator.engine import Simulator
from evalforge.verification.engine import verify_episode
from evalforge.verification.taxonomy import FailureRecord, classify_failure


class EpisodeResult(BaseModel):
    """Complete reconstructable outcome before deterministic verification."""

    episode_id: str
    scenario_id: str
    starting_world: WorldState
    public_request: AgentRequest
    events: list[ToolEvent]
    final_world: WorldState
    final: AgentFinal | None
    runtime_status: str = "valid"
    runtime_errors: list[str] = Field(default_factory=list)
    malformed_calls: int = 0
    agent_provider: str | None = None
    agent_model: str | None = None
    provider_usage: ProviderUsage | None = None
    raw_provider_messages: list[str] = Field(default_factory=list)
    verification: VerificationResult | None = None
    failure: FailureRecord | None = None


def run_episode(
    scenario: ScenarioSpec,
    agent: Agent,
    artifact_dir: Path | None = None,
    episode_id: str | None = None,
) -> EpisodeResult:
    """Run an agent against a fresh simulator copy under declared limits."""

    simulator = Simulator(scenario.initial_world, scenario.fault_plan, seed=scenario.seed)
    public = AgentRequest.model_validate(scenario.public_view().model_dump())
    registry = ToolRegistry(
        simulator,
        scenario.agent_identity,
        max_calls=scenario.max_agent_steps,
    )
    final: AgentFinal | None = None
    errors: list[str] = []
    runtime_status = "valid"
    try:
        final = agent.run(public, registry)
    except Exception as exc:  # provider/agent boundary must become data
        runtime_status = "agent_runtime_error"
        errors.append(f"{type(exc).__name__}: {exc}")
    if registry.budget_exceeded:
        runtime_status = "budget_exceeded"
        errors.append("Maximum tool-call budget exceeded")
    elif registry.malformed_calls:
        runtime_status = "malformed_tool_call"
        errors.append(f"Malformed tool calls: {registry.malformed_calls}")
    elif registry.repeated_call_limit_exceeded:
        runtime_status = "repeated_call_limit_exceeded"
        errors.append("Maximum repeated identical calls exceeded")
    resolved_id = episode_id or f"ep-{scenario.scenario_id}"
    raw_usage = getattr(agent, "usage", None)
    provider_usage = ProviderUsage.model_validate(raw_usage) if raw_usage is not None else None
    result = EpisodeResult(
        episode_id=resolved_id,
        scenario_id=scenario.scenario_id,
        starting_world=scenario.initial_world.model_copy(deep=True),
        public_request=public,
        events=simulator.events,
        final_world=simulator.world.model_copy(deep=True),
        final=final,
        runtime_status=runtime_status,
        runtime_errors=errors,
        malformed_calls=registry.malformed_calls,
        agent_provider=cast(str | None, getattr(agent, "provider", None))
        or (provider_usage.provider if provider_usage is not None else None),
        agent_model=cast(str | None, getattr(agent, "model", None))
        or (provider_usage.model if provider_usage is not None else None),
        provider_usage=provider_usage,
        raw_provider_messages=cast(list[str], getattr(agent, "raw_messages", [])),
    )
    result.verification = verify_episode(scenario, result)
    result.failure = classify_failure(scenario, result, result.verification)
    if artifact_dir is not None:
        persist_episode(artifact_dir, scenario, result)
    return result


def persist_episode(path: Path, scenario: ScenarioSpec, result: EpisodeResult) -> None:
    """Write all immutable episode components required for reconstruction."""

    path.mkdir(parents=True, exist_ok=True)
    write_scenario(path / "scenario.yaml", scenario)
    atomic_write(path / "public_request.json", canonical_json(result.public_request) + "\n")
    atomic_write(
        path / "trace.jsonl",
        "".join(canonical_json(event) + "\n" for event in result.events),
    )
    atomic_write(path / "final_world.json", canonical_json(result.final_world) + "\n")
    atomic_write(
        path / "agent_final.json",
        canonical_json(result.final) + "\n" if result.final is not None else "null\n",
    )
    atomic_write(path / "episode.json", canonical_json(result) + "\n")
    if result.verification is not None:
        atomic_write(path / "verification.json", canonical_json(result.verification) + "\n")
    if result.failure is not None:
        atomic_write(path / "failure.json", canonical_json(result.failure) + "\n")
