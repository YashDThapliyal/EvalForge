"""Validated runtime configuration."""

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

