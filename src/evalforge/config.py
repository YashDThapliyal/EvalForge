"""Validated runtime configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExperimentConfig(BaseModel):
    """Configuration shared by offline experiment sources."""

    model_config = ConfigDict(extra="forbid")

    seed: int = 7
    scenarios_per_source: int = Field(default=12, ge=1)
    agent: str = "scripted"
    model: str | None = None
    max_agent_steps: int = Field(default=10, ge=1)
    max_output_tokens: int = Field(default=4096, ge=256)
    output_dir: str = "artifacts"
    random_proposer: str = "programmatic"
    failure_directed_proposer: str = "programmatic"
    input_cost_per_million: float | None = Field(default=None, ge=0)
    cached_input_cost_per_million: float | None = Field(default=None, ge=0)
    cache_write_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def resolve_live_defaults(self) -> ExperimentConfig:
        """Materialize provider model and pricing so artifacts are reproducible."""

        defaults: dict[str, tuple[str, float, float, float, float]] = {
            "openai": ("gpt-5.6-sol", 5.0, 0.5, 6.25, 30.0),
            "anthropic": ("claude-opus-4-8", 5.0, 0.5, 6.25, 25.0),
        }
        if self.agent == "scripted":
            return self
        if self.agent not in defaults:
            raise ValueError(f"Unsupported experiment agent: {self.agent}")
        model, input_rate, cached_rate, write_rate, output_rate = defaults[self.agent]
        self.model = self.model or model
        self.input_cost_per_million = (
            input_rate if self.input_cost_per_million is None else self.input_cost_per_million
        )
        self.cached_input_cost_per_million = (
            cached_rate
            if self.cached_input_cost_per_million is None
            else self.cached_input_cost_per_million
        )
        self.cache_write_cost_per_million = (
            write_rate
            if self.cache_write_cost_per_million is None
            else self.cache_write_cost_per_million
        )
        self.output_cost_per_million = (
            output_rate if self.output_cost_per_million is None else self.output_cost_per_million
        )
        return self


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load and validate a checked-in YAML experiment configuration."""

    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
