"""EvalForge command-line interface."""

from pathlib import Path
from typing import Annotated

import typer

from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.execution.episode import run_episode
from evalforge.scenarios.loader import load_scenario, load_scenarios
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


@app.command("run")
def run_command(
    scenario: Annotated[Path, typer.Option("--scenario")],
    agent: Annotated[str, typer.Option("--agent")] = "scripted",
) -> None:
    """Run one scenario with a deterministic offline agent."""

    if agent != "scripted":
        typer.echo(f"Unsupported offline agent: {agent}", err=True)
        raise typer.Exit(1)
    loaded = load_scenario(scenario)
    validation = ScenarioValidator().validate(loaded)
    if not validation.valid:
        typer.echo(f"Scenario invalid: {', '.join(sorted(validation.codes))}", err=True)
        raise typer.Exit(1)
    output = Path("artifacts") / "runs" / loaded.scenario_id
    result = run_episode(loaded, ScriptedBaselineAgent(), artifact_dir=output)
    typer.echo(
        f"Episode {result.episode_id}: {result.runtime_status}; "
        f"{len(result.events)} tool call(s); artifacts: {output}"
    )


if __name__ == "__main__":
    app()
