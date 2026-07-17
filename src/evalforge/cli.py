"""EvalForge command-line interface."""

from pathlib import Path

import typer

from evalforge.scenarios.loader import load_scenarios
from evalforge.scenarios.validator import ScenarioValidator

app = typer.Typer(
    name="evalforge",
    help="EvalForge: executable stress tests for tool-using AI agents.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Generate, validate, execute, and analyze agent stress tests."""


@app.command("validate")
def validate_command(path: Path) -> None:
    """Validate one scenario or every YAML scenario under a directory."""

    scenarios = load_scenarios(path)
    invalid: list[tuple[str, set[str]]] = []
    for scenario in scenarios:
        result = ScenarioValidator().validate(scenario)
        if not result.valid:
            invalid.append((scenario.scenario_id, result.codes))
    if invalid:
        for scenario_id, codes in invalid:
            typer.echo(f"invalid {scenario_id}: {', '.join(sorted(codes))}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Validated {len(scenarios)} scenario(s) from {path}")


if __name__ == "__main__":
    app()
