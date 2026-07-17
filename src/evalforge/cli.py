"""EvalForge command-line interface."""

import typer

app = typer.Typer(
    name="evalforge",
    help="EvalForge: executable stress tests for tool-using AI agents.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Generate, validate, execute, and analyze agent stress tests."""


if __name__ == "__main__":
    app()
