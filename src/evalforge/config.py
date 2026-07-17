"""Validated runtime configuration."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ExperimentConfig(BaseModel):
    """Configuration shared by offline experiment sources."""

    model_config = ConfigDict(extra="forbid")

    seed: int = 7
    scenarios_per_source: int = Field(default=12, ge=1)
    agent: str = "scripted"
    max_agent_steps: int = Field(default=10, ge=1)
    output_dir: str = "artifacts"
    random_proposer: str = "programmatic"
    failure_directed_proposer: str = "programmatic"


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load and validate a checked-in YAML experiment configuration."""

    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
