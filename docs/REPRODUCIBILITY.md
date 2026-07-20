# Reproducibility guide

## Environment

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src/evalforge
uv run pytest -q
uv run pytest --cov=evalforge --cov-report=term-missing
uv run evalforge validate scenarios/manual
```

Default tests block socket connections. They use deterministic doubles under `tests/`; production commands cannot select those doubles.

## Re-score saved episodes after a verifier change

When the verifier changes, the saved episodes must be re-scored rather than re-run:

```bash
uv run python scripts/rescore_from_artifacts.py artifacts/model-suite/*/evalforge-seed7-b12-*
```

This recomputes verification, failure classification, and `metrics.json` from the episodes exactly as executed, and prints per-source before/after rates. It makes no provider calls.

Re-running `evalforge experiment` would **not** be equivalent: corrected pass/fail signal feeds failure-directed lineage, so different descendant scenarios would be generated and new paid episodes required. That produces a different experiment, not a correction of an existing one. Regenerate reports afterwards with the commands below.

## Rebuild reports without model calls

If the full `artifacts/model-suite/` directory is available, regenerate each experiment report with:

```bash
uv run evalforge report --experiment artifacts/model-suite/<model>/<experiment-id>
```

Then regenerate the six-model comparison:

```bash
uv run evalforge compare \
  --experiment artifacts/model-suite/gpt-5.6-sol/evalforge-seed7-b12-41c8210abd \
  --experiment artifacts/model-suite/gpt-5/evalforge-seed7-b12-c498c0e3f2 \
  --experiment artifacts/model-suite/gpt-5-mini/evalforge-seed7-b12-5e454027b9 \
  --experiment artifacts/model-suite/claude-opus-4-8/evalforge-seed7-b12-bd24aae034 \
  --experiment artifacts/model-suite/claude-sonnet-5/evalforge-seed7-b12-46cda94bad \
  --experiment artifacts/model-suite/claude-haiku-4-5-20251001/evalforge-seed7-b12-9ed86e4c03 \
  --output results/model-suite
```

This command reads only saved manifests, resolved configurations, metrics, episode results, failures, and scenario lineage. It does not instantiate an agent or contact a provider.

## Inspect evidence

```bash
# Successful episode
uv run evalforge inspect \
  --experiment artifacts/model-suite/claude-opus-4-8/evalforge-seed7-b12-bd24aae034 \
  --episode manual-000-bad_deployment_001

# GPT-5 model-protocol failure
uv run evalforge inspect \
  --experiment artifacts/model-suite/gpt-5/evalforge-seed7-b12-c498c0e3f2 \
  --episode failure_directed-003-fd_10_0000

# False-success / claim-grounding example
uv run evalforge inspect \
  --experiment artifacts/model-suite/claude-haiku-4-5-20251001/evalforge-seed7-b12-9ed86e4c03 \
  --episode failure_directed-008-fd_15_0000
```

`inspect` is intended for failed episodes; successful episodes can be read directly from their `episode.json` and `trace.jsonl` files.

## Rerun live models

Only run this when paid provider calls are intended:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
bash scripts/run_model_suite.sh
```

The script reuses completed episode artifacts. Model protocol failures are preserved as observed model outcomes; only provider/API infrastructure errors are eligible for retry. Live responses are sampled and therefore not bit-for-bit deterministic.

## Legacy offline commands

The repository's live-only amendment intentionally removed `evalforge demo` and scripted production experiments. Simulator and verifier behavior remain locally reproducible through the default test suite, oracle validation, and report reconstruction. `configs/quick.yaml` is a paid live configuration, not an offline fixture.
