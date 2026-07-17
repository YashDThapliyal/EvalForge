from pathlib import Path

from evalforge.config import load_experiment_config

EXPECTED_MODELS = {
    "openai_gpt_5_6_sol.yaml": ("openai", "gpt-5.6-sol", 5.0, 0.5, 0.0, 30.0),
    "openai_gpt_5.yaml": ("openai", "gpt-5", 1.25, 0.125, 0.0, 10.0),
    "openai_gpt_5_mini.yaml": ("openai", "gpt-5-mini", 0.25, 0.025, 0.0, 2.0),
    "anthropic_opus_4_8.yaml": ("anthropic", "claude-opus-4-8", 5.0, 0.5, 6.25, 25.0),
    "anthropic_sonnet_5.yaml": ("anthropic", "claude-sonnet-5", 2.0, 0.2, 2.5, 10.0),
    "anthropic_haiku_4_5.yaml": (
        "anthropic",
        "claude-haiku-4-5-20251001",
        1.0,
        0.1,
        1.25,
        5.0,
    ),
}


def test_model_suite_configs_pin_provider_model_pricing_and_equal_budgets() -> None:
    config_dir = Path("configs/model_suite")
    assert {path.name for path in config_dir.glob("*.yaml")} == set(EXPECTED_MODELS)
    for filename, expected in EXPECTED_MODELS.items():
        config = load_experiment_config(config_dir / filename)
        actual = (
            config.agent,
            config.model,
            config.input_cost_per_million,
            config.cached_input_cost_per_million,
            config.cache_write_cost_per_million,
            config.output_cost_per_million,
        )
        assert actual == expected
        assert config.seed == 7
        assert config.scenarios_per_source == 12
        assert config.max_agent_steps == 10
        assert config.random_proposer == "openai"
        assert config.random_proposer_model == "gpt-5.6-sol"
        assert config.random_scenarios_path == "artifacts/model-suite/shared-random"
        assert config.output_dir == f"artifacts/model-suite/{config.model}"


def test_model_suite_runner_includes_every_config_and_comparison() -> None:
    script = Path("scripts/run_model_suite.sh").read_text(encoding="utf-8")
    for filename in EXPECTED_MODELS:
        assert f"configs/model_suite/{filename}" in script
    assert "evalforge experiment" in script
    assert "evalforge generate --method random --count 12" in script
    assert "evalforge compare" in script
    assert "OPENAI_API_KEY" in script
    assert "ANTHROPIC_API_KEY" in script
