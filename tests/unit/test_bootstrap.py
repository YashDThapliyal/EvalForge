from __future__ import annotations

import json

from typer.testing import CliRunner

import evalforge
from evalforge.cli import app
from evalforge.config import ExperimentConfig
from evalforge.serialization import canonical_json


def test_package_and_cli_help() -> None:
    assert evalforge.__version__
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "EvalForge" in result.stdout


def test_minimal_configuration_round_trips() -> None:
    config = ExperimentConfig(seed=7, scenarios_per_source=12)
    assert ExperimentConfig.model_validate_json(config.model_dump_json()) == config


def test_canonical_json_is_stable() -> None:
    first = canonical_json({"z": [3, 2], "a": {"b": True}})
    second = canonical_json(json.loads(first))
    assert first == second == '{"a":{"b":true},"z":[3,2]}'
