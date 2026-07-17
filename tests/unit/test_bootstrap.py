from __future__ import annotations

import json

from typer.testing import CliRunner

import evalforge
from evalforge.cli import app
from evalforge.config import ExperimentConfig
from evalforge.serialization import canonical_json
from tests.support import LIVE_CONFIG_FIELDS


def test_package_and_cli_help() -> None:
    assert evalforge.__version__
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "EvalForge" in result.stdout


def test_minimal_configuration_round_trips() -> None:
    config = ExperimentConfig(seed=7, scenarios_per_source=12, **LIVE_CONFIG_FIELDS)  # type: ignore[arg-type]
    assert ExperimentConfig.model_validate_json(config.model_dump_json()) == config


def test_live_experiment_config_records_model_and_pricing() -> None:
    config = ExperimentConfig(
        agent="openai",
        model="gpt-5.6-sol",
        input_cost_per_million=5.0,
        cached_input_cost_per_million=0.5,
        cache_write_cost_per_million=6.25,
        output_cost_per_million=30.0,
        random_proposer="openai",
        random_proposer_model="gpt-5.6-sol",
        failure_directed_proposer="bounded_mutation",
    )
    assert config.model == "gpt-5.6-sol"
    assert config.input_cost_per_million == 5.0


def test_canonical_json_is_stable() -> None:
    first = canonical_json({"z": [3, 2], "a": {"b": True}})
    second = canonical_json(json.loads(first))
    assert first == second == '{"a":{"b":true},"z":[3,2]}'
