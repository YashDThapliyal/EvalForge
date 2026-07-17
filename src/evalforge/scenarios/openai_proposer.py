"""Optional schema-constrained live scenario proposer."""

from __future__ import annotations

import os
from typing import Protocol, cast

from evalforge.agents.openai_agent import LiveConfigurationError
from evalforge.domain.scenario import ScenarioSpec
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.serialization import canonical_json
from evalforge.simulator.tools import tool_schemas


class ResponsesClient(Protocol):
    """Minimal injectable response creation surface."""

    def create(self, **kwargs: object) -> object:
        """Create one schema-constrained response."""


class Client(Protocol):
    """Minimal injectable live proposer client."""

    responses: ResponsesClient


class LiveProposalError(RuntimeError):
    """The live provider could not return a usable scenario proposal."""


MAX_PROPOSAL_OUTPUT_TOKENS = 12_000


class OpenAIScenarioProposer:
    """Request complete ScenarioSpec JSON and never execute generated content."""

    def __init__(self, model: str, client: Client | None = None):
        if not model.strip():
            raise LiveConfigurationError("OpenAI proposer model must be explicitly configured")
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LiveConfigurationError("OPENAI_API_KEY is required for the live proposer")
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise LiveConfigurationError("Install the 'openai' extra") from exc
            client = cast(Client, OpenAI(api_key=api_key))
        self.client = client
        self.model = model

    def propose(self, attempt: int, seed: int) -> ScenarioSpec:
        """Request one data-only proposal constrained to the versioned schema."""

        try:
            raw = self.client.responses.create(
                model=self.model,
                max_output_tokens=MAX_PROPOSAL_OUTPUT_TOKENS,
                input=(
                    f"Create complete executable cloud-operations stress scenario proposal "
                    f"{attempt} using seed {seed}. It must use source_method=random, have no "
                    "parent lineage, reference only entities present in initial_world, require a "
                    "meaningful legal oracle mutation, make every declared fault reachable, "
                    "preserve its invariants, and avoid revealing the hidden repair in task text. "
                    f"Use only these tools: {canonical_json(tool_schemas())}. Use this shape as "
                    "an example but create a materially different scenario with a unique "
                    "scenario_id: "
                    f"{canonical_json(build_manual_scenario('bad_deployment', seed % 5))}. "
                    "Return schema-conforming data only."
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "scenario_spec",
                        # ScenarioSpec contains recursive JsonValue maps. OpenAI strict mode
                        # rejects arbitrary-key maps, so apply deterministic validation afterward.
                        "strict": False,
                        "schema": ScenarioSpec.model_json_schema(),
                    }
                },
            )
        except Exception as exc:
            raise LiveProposalError(f"OpenAI scenario proposal failed: {exc}") from exc
        if isinstance(raw, dict):
            output_text = raw.get("output_text")
        elif hasattr(raw, "output_text"):
            output_text = raw.output_text
        else:
            output_text = None
        if not isinstance(output_text, str):
            raise ValueError("Live proposer returned malformed schema output")
        return ScenarioSpec.model_validate_json(output_text)
