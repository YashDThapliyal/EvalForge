"""Optional schema-constrained live scenario proposer."""

from __future__ import annotations

import os
from typing import Protocol, cast

from evalforge.agents.openai_agent import LiveConfigurationError
from evalforge.domain.scenario import ScenarioSpec


class ResponsesClient(Protocol):
    """Minimal injectable response creation surface."""

    def create(self, **kwargs: object) -> object:
        """Create one schema-constrained response."""


class Client(Protocol):
    """Minimal injectable live proposer client."""

    responses: ResponsesClient


class OpenAIScenarioProposer:
    """Request complete ScenarioSpec JSON and never execute generated content."""

    def __init__(self, client: Client | None = None, model: str = "gpt-5-mini"):
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

        raw = self.client.responses.create(
            model=self.model,
            input=(
                f"Create executable cloud-operations stress scenario proposal {attempt} "
                f"using deterministic seed {seed}. Return schema-conforming data only."
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "scenario_spec",
                    "strict": True,
                    "schema": ScenarioSpec.model_json_schema(),
                }
            },
        )
        if isinstance(raw, dict):
            output_text = raw.get("output_text")
        elif hasattr(raw, "output_text"):
            output_text = raw.output_text
        else:
            output_text = None
        if not isinstance(output_text, str):
            raise ValueError("Live proposer returned malformed schema output")
        return ScenarioSpec.model_validate_json(output_text)
