from inspect import Parameter, signature
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from evalforge.agents.anthropic_agent import AnthropicAgent
from evalforge.agents.openai_agent import OpenAIAgent
from evalforge.cli import app
from evalforge.config import ExperimentConfig
from evalforge.scenarios.openai_proposer import OpenAIScenarioProposer

LIVE_FIELDS = {
    "agent": "openai",
    "model": "gpt-5.6-sol",
    "random_proposer": "openai",
    "random_proposer_model": "gpt-5.6-sol",
    "failure_directed_proposer": "bounded_mutation",
    "input_cost_per_million": 5.0,
    "cached_input_cost_per_million": 0.5,
    "cache_write_cost_per_million": 6.25,
    "output_cost_per_million": 30.0,
}


def test_experiment_config_rejects_scripted_or_implicit_agents() -> None:
    with pytest.raises(ValidationError):
        ExperimentConfig(
            agent="scripted",
            model="fake",
            **{  # type: ignore[arg-type]
                key: value for key, value in LIVE_FIELDS.items() if key not in {"agent", "model"}
            },
        )
    with pytest.raises(ValidationError):
        ExperimentConfig.model_validate({"seed": 7})
    config = ExperimentConfig(**LIVE_FIELDS)  # type: ignore[arg-type]
    assert config.agent == "openai"
    assert config.model == "gpt-5.6-sol"


def test_cli_has_no_scripted_or_credential_free_demo_path(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--scenario",
            str(tmp_path / "missing.yaml"),
            "--agent",
            "scripted",
            "--model",
            "fake",
            "--input-cost-per-million",
            "1",
            "--cached-input-cost-per-million",
            "1",
            "--cache-write-cost-per-million",
            "1",
            "--output-cost-per-million",
            "1",
        ],
    )
    assert result.exit_code != 0
    assert "Unsupported agent: scripted" in result.output
    demo = runner.invoke(app, ["demo", "--seed", "7"])
    assert demo.exit_code != 0
    assert "No such command 'demo'" in demo.output


def test_production_tree_contains_no_scripted_evaluation_implementation() -> None:
    roots = [Path("src/evalforge"), Path("configs")]
    forbidden = ("ScriptedBaselineAgent", "ProgrammaticProposer", "agent: scripted")
    matches = {
        str(path): token
        for root in roots
        for path in root.rglob("*")
        if path.suffix in {".py", ".yaml", ".yml"}
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    }
    assert matches == {}


def test_live_adapters_have_no_implicit_model_or_pricing_defaults() -> None:
    required = {
        "model",
        "input_cost_per_million",
        "cached_input_cost_per_million",
        "cache_write_cost_per_million",
        "output_cost_per_million",
    }
    for adapter in (OpenAIAgent, AnthropicAgent):
        parameters = signature(adapter).parameters
        assert all(parameters[name].default is Parameter.empty for name in required)
    assert signature(OpenAIScenarioProposer).parameters["model"].default is Parameter.empty
