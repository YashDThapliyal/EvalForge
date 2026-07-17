"""Validated runtime configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ExperimentConfig(BaseModel):
    """Explicit live-provider experiment configuration with no fallback defaults."""

    model_config = ConfigDict(extra="forbid")

    seed: int = 7
    scenarios_per_source: int = Field(default=12, ge=1)
    agent: Literal["openai", "anthropic"]
    model: str = Field(min_length=1)
    max_agent_steps: int = Field(default=10, ge=1)
    max_output_tokens: int = Field(default=4096, ge=256)
    output_dir: str = "artifacts"
    random_proposer: Literal["openai"]
    random_proposer_model: str = Field(min_length=1)
    random_scenarios_path: str | None = None
    failure_directed_proposer: Literal["bounded_mutation"]
    manual_selection_strategy: str = "stratified-v1"
    input_cost_per_million: float = Field(ge=0)
    cached_input_cost_per_million: float = Field(ge=0)
    cache_write_cost_per_million: float = Field(ge=0)
    output_cost_per_million: float = Field(ge=0)


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load and validate a checked-in YAML experiment configuration."""

    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
