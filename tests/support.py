"""Explicit deterministic test doubles that are never shipped as evaluated agents."""

from evalforge.agents.base import AgentFinal, AgentRequest, ToolRegistry
from evalforge.domain.scenario import ScenarioSpec, SourceMethod
from evalforge.scenarios.manual import FAMILIES, build_manual_scenario

LIVE_CONFIG_FIELDS: dict[str, object] = {
    "agent": "openai",
    "model": "test-live-model",
    "random_proposer": "openai",
    "random_proposer_model": "test-proposer-model",
    "failure_directed_proposer": "bounded_mutation",
    "input_cost_per_million": 1.0,
    "cached_input_cost_per_million": 0.1,
    "cache_write_cost_per_million": 1.25,
    "output_cost_per_million": 2.0,
}


class FixtureScenarioProposer:
    """Produce reviewable scenario fixtures only for generator orchestration tests."""

    def propose(self, attempt: int, seed: int) -> ScenarioSpec:
        family = FAMILIES[attempt % len(FAMILIES)]
        variant = (attempt // len(FAMILIES)) % 5
        scenario = build_manual_scenario(family, variant)
        scenario.scenario_id = f"test-proposal-{seed}-{attempt:04d}"
        scenario.source_method = SourceMethod.RANDOM
        scenario.metadata["test_fixture"] = True
        return scenario


class UnresolvedTestAgent:
    """Return an explicit failed terminal result for harness/reporting tests."""

    provider = "test-double"
    model = "test-double"

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        del request
        tools.call("inspect_service", {"service_id": "payments-api"})
        return AgentFinal(status="not_resolved", summary="Test fixture outcome", claims=[])
