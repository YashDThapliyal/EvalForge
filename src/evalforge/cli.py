"""EvalForge command-line interface."""

from pathlib import Path
from typing import Annotated

import typer

from evalforge.agents.anthropic_agent import AnthropicAgent
from evalforge.agents.base import Agent
from evalforge.agents.openai_agent import LiveConfigurationError, OpenAIAgent
from evalforge.agents.scripted import ScriptedBaselineAgent
from evalforge.config import load_experiment_config
from evalforge.execution.artifacts import atomic_write
from evalforge.execution.demo import run_demo
from evalforge.execution.episode import run_episode
from evalforge.execution.experiment import ExperimentRunner
from evalforge.reporting.comparison import generate_model_comparison
from evalforge.reporting.html import generate_html_report
from evalforge.reporting.inspect import render_failure_timeline
from evalforge.scenarios.failure_directed import FailureDirectedScenarioGenerator
from evalforge.scenarios.loader import load_scenario, load_scenarios, write_scenario
from evalforge.scenarios.random_generator import ProgrammaticProposer, RandomScenarioGenerator
from evalforge.scenarios.validator import ScenarioValidator
from evalforge.serialization import canonical_json
from evalforge.verification.taxonomy import FailureRecord

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
    model: Annotated[str | None, typer.Option("--model")] = None,
) -> None:
    """Run one scenario with a scripted or explicitly configured live agent."""

    selected_agent: Agent
    if agent == "scripted":
        selected_agent = ScriptedBaselineAgent()
    elif agent == "openai":
        try:
            selected_agent = OpenAIAgent(model=model or "gpt-5.6-sol")
        except LiveConfigurationError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
    elif agent == "anthropic":
        try:
            selected_agent = AnthropicAgent(model=model or "claude-opus-4-8")
        except LiveConfigurationError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
    else:
        typer.echo(f"Unsupported agent: {agent}", err=True)
        raise typer.Exit(1)
    loaded = load_scenario(scenario)
    validation = ScenarioValidator().validate(loaded)
    if not validation.valid:
        typer.echo(f"Scenario invalid: {', '.join(sorted(validation.codes))}", err=True)
        raise typer.Exit(1)
    output = Path("artifacts") / "runs" / loaded.scenario_id
    result = run_episode(loaded, selected_agent, artifact_dir=output)
    typer.echo(
        f"Episode {result.episode_id}: {result.runtime_status}; "
        f"{len(result.events)} tool call(s); artifacts: {output}"
    )
    if result.runtime_status != "valid":
        for error in result.runtime_errors:
            typer.echo(error, err=True)
        raise typer.Exit(1)


@app.command("generate")
def generate_command(
    method: Annotated[str, typer.Option("--method")],
    count: Annotated[int, typer.Option("--count")],
    seed: Annotated[int, typer.Option("--seed")] = 7,
    output: Annotated[Path, typer.Option("--output")] = Path("artifacts/generated"),
    failures: Annotated[Path | None, typer.Option("--failures")] = None,
) -> None:
    """Generate validated scenarios using an offline proposer."""

    if method == "random":
        result = RandomScenarioGenerator(ProgrammaticProposer()).generate(count=count, seed=seed)
    elif method == "failure-directed":
        if failures is None:
            typer.echo("--failures is required for failure-directed generation", err=True)
            raise typer.Exit(1)
        failure_paths = sorted(failures.rglob("failure.json"))
        if not failure_paths:
            typer.echo(f"No failure.json artifacts found under {failures}", err=True)
            raise typer.Exit(1)
        failure_path = failure_paths[0]
        failure = FailureRecord.model_validate_json(failure_path.read_text(encoding="utf-8"))
        parent = load_scenario(failure_path.parent / "scenario.yaml")
        result = FailureDirectedScenarioGenerator().generate(
            parent, failure, count=count, seed=seed
        )
    else:
        typer.echo(f"Unsupported generation method: {method}", err=True)
        raise typer.Exit(1)
    if len(result.accepted) != count:
        typer.echo(
            f"Generated only {len(result.accepted)}/{count}; inspect rejection statistics", err=True
        )
        raise typer.Exit(1)
    for scenario_item in result.accepted:
        write_scenario(output / f"{scenario_item.scenario_id}.yaml", scenario_item)
    atomic_write(output / "generation_stats.json", canonical_json(result.stats) + "\n")
    typer.echo(
        f"Generated {len(result.accepted)} valid {method} scenario(s); "
        f"attempted {result.stats.attempted}; output: {output}"
    )


@app.command("experiment")
def experiment_command(
    config: Annotated[Path, typer.Option("--config")],
) -> None:
    """Run the deterministic equal-budget three-source experiment."""

    try:
        result = ExperimentRunner(load_experiment_config(config)).run()
    except (LiveConfigurationError, RuntimeError, ValueError) as exc:
        typer.echo(f"Experiment failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Experiment {result.experiment_id} complete: {len(result.episode_ids)} episodes; "
        f"artifacts: {result.artifact_dir}"
    )


@app.command("compare")
def compare_command(
    experiments: Annotated[list[Path], typer.Option("--experiment")],
    output: Annotated[Path, typer.Option("--output")] = Path("artifacts/live/comparison"),
) -> None:
    """Compare two or more completed equal-budget model experiments."""

    try:
        result = generate_model_comparison(experiments, output)
    except ValueError as exc:
        typer.echo(f"Comparison failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Compared {len(result.artifact.models)} models; reports: "
        f"{result.output_dir / 'report.md'} and {result.output_dir / 'report.html'}"
    )


@app.command("report")
def report_command(
    experiment: Annotated[Path, typer.Option("--experiment")],
) -> None:
    """Regenerate Markdown, HTML, and failure pages from saved artifacts."""

    generate_html_report(experiment)
    typer.echo(f"Regenerated {experiment / 'report.md'} and {experiment / 'report.html'}")


@app.command("inspect")
def inspect_command(
    experiment: Annotated[Path, typer.Option("--experiment")],
    episode: Annotated[str, typer.Option("--episode")],
) -> None:
    """Print a chronological failed-episode timeline and exact violated rules."""

    typer.echo(render_failure_timeline(experiment, episode), nl=False)


@app.command("demo")
def demo_command(
    seed: Annotated[int, typer.Option("--seed")] = 7,
) -> None:
    """Run the six-case credential-free demonstration."""

    result = run_demo(seed=seed)
    typer.echo(
        f"Demo scenarios: {len(result.episodes)}; success rate: {result.success_rate:.1%}\n"
        f"Discovered failure signatures: {len(result.failure_signatures)}"
    )
    for signature in result.failure_signatures:
        typer.echo(f"- {signature}")
    typer.echo("\nExample failure timeline:")
    typer.echo(result.example_timeline, nl=False)
    typer.echo(f"Markdown report: {result.artifact_dir / 'report.md'}")
    typer.echo(f"HTML report: {result.artifact_dir / 'report.html'}")


if __name__ == "__main__":
    app()
