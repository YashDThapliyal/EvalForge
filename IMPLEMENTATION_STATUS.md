# EvalForge implementation status

Current as of 2026-07-17. This file records the active implementation and its verification
commands. Earlier credential-free evaluation paths were removed by owner request and are not
supported.

## Completed foundation

- Domain models, permission-first simulator transitions, all six tools, idempotency, eight fault
  kinds, and the required actual-outcome/visible-observation boundary.
- Versioned scenarios, explicit public views, canonical fingerprints, common oracle validation,
  and 50 reviewed manual variants across ten families.
- Bounded tool execution, immutable episode artifacts, deterministic outcome/invariant/policy/
  claim verification, all required failure codes, and stable behavioral signatures.
- Equal-budget manual/random/failure-directed orchestration, metrics, static Markdown/HTML
  reporting, escaped failure pages, comparison reports, and CLI inspection.
- Native OpenAI Responses and Anthropic Messages tool loops with strict `submit_final`, raw
  provider-message capture, provider/model identity, token usage, API calls, and explicit-price
  cost estimates.

## Live-only evaluation migration

Test-first red gate:

```text
UV_CACHE_DIR=/private/tmp/evalforge-uv-cache \
  uv run pytest tests/unit/test_live_only.py -q
failed: production tree still contained agents/scripted.py and execution/demo.py
```

Implemented:

- Removed the production scripted tested agent and credential-free demo command/module.
- Removed the programmatic random scenario proposer.
- Made provider, tested model, proposal backend/model, failure-directed backend, and prices
  required validated configuration fields.
- Made standalone `run` require explicit `--agent` and `--model`.
- Made random `generate` require explicit `--proposer openai --proposer-model ...`.
- Made production experiments construct only OpenAI or Anthropic agents and a live OpenAI
  scenario proposer; provider/authentication errors are never substituted.
- Retained oracle/replay only for validation and regression debugging.
- Moved all deterministic harness/proposer doubles under `tests/` and made their injection
  explicit.
- Updated every checked-in experiment configuration to a live provider/proposer configuration.

Targeted green gates completed so far:

```text
26 agent/scenario/verification/integration tests passed
21 experiment/reporting/config/verification tests passed
12 live-adapter and live-only boundary tests passed
```

Real provider smoke gate:

```text
uv run evalforge generate --method random --count 1 --seed 991 \
  --output /private/tmp/evalforge-live-smoke \
  --proposer openai --proposer-model gpt-5.6-sol
passed: 1 attempted, 1 accepted, 0 rejected, 0 duplicates

uv run evalforge validate /private/tmp/evalforge-live-smoke
passed: ledger_ingest_pressure_random_991_p0
```

The proposal was returned by the real OpenAI API and created a new `ledger-ingest` memory-pressure
scenario; no fixture or local proposal path participated.

## Final live-only migration gates — passed 2026-07-17

```text
uv run ruff format --check .                              passed (74 files)
uv run ruff check .                                       passed
uv run mypy src/evalforge                                 passed (48 source files)
uv run pytest --cov=evalforge --cov-report=term-missing   passed (59, 2 live deselected, 90%)
uv run evalforge validate scenarios/manual                passed (50 scenarios)
```

The two deselected tests are explicitly marked credential-presence checks. Provider protocol
behavior is covered in the normal suite with injected raw provider responses; the real proposer
smoke command above separately proves external API execution.

## Previously audited real-model result

Before this migration, genuine provider episodes were completed and retained as immutable
artifacts:

- `gpt-5.6-sol`: 36/36 full stress success, 207 provider calls, estimated `$0.9887`.
- `claude-opus-4-8`: 27/36 full stress success, nine failure episodes, one unique high-severity
  typed-configuration signature, 218 provider calls, estimated `$3.6389`.
- The comparison comprised 72 genuine model episodes under equal accepted budgets. These are
  descriptive results for one seed and quick budget, not a statistical-significance claim.

Artifacts:

- `artifacts/live-audited/final-model-comparison/report.md`
- `artifacts/live-audited/final-model-comparison/report.html`
- `artifacts/live/evalforge-seed7-b12-652596d9d5/report.md`
- `artifacts/live-audited/evalforge-seed7-b12-6c29c2409f/report.md`

Because the random source in that historical run predates the live-only proposal migration, a
new post-migration experiment is required before using it to compare scenario-source quality.

## Six-model suite — implemented 2026-07-17

- Added equal-budget configs for GPT-5.6 Sol, GPT-5, GPT-5 mini, Claude Opus 4.8, Claude Sonnet 5,
  and the pinned Claude Haiku 4.5 snapshot.
- Verified model IDs and explicit token rates against current official provider documentation.
- Added one unattended `scripts/run_model_suite.sh` command that checks both credentials, creates
  one live-proposed shared random corpus, runs all six models, and renders the combined report.
- Added shared-corpus loading and validation so every model receives identical manual and random
  cases while its failure-directed arm remains adaptive to its own observed failures.
- Corrected OpenAI cache-write pricing to zero because OpenAI bills cached input reads rather than
  a separate Anthropic-style cache-write line item.

TDD and final gates:

```text
model-suite tests before implementation                     failed (missing configs/runner)
shared-random-corpus test before implementation              failed (unsupported config/path)
uv run pytest tests/unit/test_model_suite.py \
  tests/unit/execution/test_experiment.py -q                 passed (7)
bash -n scripts/run_model_suite.sh                           passed
uv run ruff format --check .                                 passed (75 files)
uv run ruff check .                                          passed
uv run mypy src/evalforge                                    passed (48 source files)
uv run pytest --cov=evalforge --cov-report=term-missing      passed (62, 2 deselected, 90%)
```

### Provider-lane parallelism

- The suite now runs one OpenAI lane and one Anthropic lane concurrently.
- Models remain sequential inside each provider lane to control rate-limit pressure.
- Comparison starts only after both lanes succeed; a failed lane makes the script return nonzero.
- Provider output is persisted separately under `artifacts/model-suite/logs/`.
- Replaced interleaved provider prints with side-by-side episode progress bars showing the active
  model and completed episodes out of 108 for each lane.
- TDD red gate: the runner test failed because provider lanes and waits were absent.
- Green gate: model-suite tests passed (4), and `bash -n scripts/run_model_suite.sh` passed.
- Full regression gate: 65 passed, 2 explicitly live tests deselected; Ruff and strict mypy passed.
- Added cost guards for the paid shared-corpus stage: at most 36 proposal attempts and 12,000
  output tokens per proposal. Expected total suite spend is documented as $10–$14, with $20
  recommended provisioning and a $25 billing alert.

### Runtime sensitivity and source discovery audit

- Added raw and infrastructure-error-excluded task/stress success rates to model comparisons.
- Separated provider infrastructure errors from model protocol errors; malformed final output stays
  in the model-failure denominator.
- Added cross-model source metrics for success, deduplicated canonical failure signatures, and
  severity-weighted unique discoveries.
- TDD red gate: the comparison test failed because runtime sensitivity and source aggregation were
  absent. Targeted green gate: `uv run pytest -q tests/unit/reporting/test_model_comparison.py`
  passed.
- Audited the GPT-5 runtime-status episode as `AgentProtocolError: malformed final output:
  submit_final was not called`, not an infrastructure failure.
- Final gates: Ruff format/check passed, strict mypy passed for 48 source files, and pytest passed
  with 65 tests (2 credential-gated live tests deselected).
