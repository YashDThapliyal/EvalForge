# EvalForge implementation status

Work began 2026-07-17. Exact phase gates and final command results are recorded here as they complete.

## Phase 0 — bootstrap and contracts

- Red test: `PYTHONPATH=src pytest tests/unit/test_bootstrap.py -q` — failed during collection because `evalforge` did not exist.
- Implemented package metadata, strict configuration, canonical JSON, and the base Typer CLI.
- Gate: `uv sync --all-extras`; `uv run pytest tests/unit -q` (3 passed); `uv run ruff check .`; `uv run mypy src/evalforge` — passed.

## Phase 1 — simulator

- Red test: `uv run pytest tests/unit/simulator tests/property -q` — failed because simulator domain modules did not exist.
- Implemented the world, all six tools, permission-first execution, idempotency, eight fault kinds, actual/visible outcome separation, stable hashing, diffs, and provider-neutral schemas.
- Gate: targeted tests (6 passed), full suite (9 passed), Ruff, and strict mypy — passed.

## Phase 2 — scenarios and validation

- Red test: scenario tests failed during collection because scenario domain and loader modules did not exist.
- Implemented versioned specs, explicit public views, YAML round-trips, exact/near fingerprints, common oracle validation, and a checked-in manifest of 50 curated variants across 10 required families.
- Gate: `evalforge validate scenarios/manual` (50 valid), targeted tests (5 passed), full suite (14 passed), Ruff, and strict mypy — passed.

## Phase 3 — agent harness and tracing

- Red test: agent/execution tests failed during collection because the agent and episode packages did not exist.
- Implemented public-only agent requests, oracle/scripted/replay agents, bounded visible-only tool access, structured parser/runtime outcomes, isolated episodes, and atomic complete artifacts.
- Gate: targeted tests (8 passed), scripted CLI episode (2 calls), full suite (22 passed), Ruff, and strict mypy — passed.

## Phase 4 — verification and failure taxonomy

- Red test: verification tests failed during collection because verifier components did not exist.
- Implemented independent outcome, invariant, trace-policy, claim-grounding, and runtime verifiers; all 17 required failure codes; stable behavioral signatures; and persisted verification/failure artifacts.
- Gate: targeted tests (7 passed), full suite (29 passed), Ruff, and strict mypy — passed.

## Phase 5 — scenario generation

- Red test: generator tests failed during collection because random/failure-directed coordinators did not exist.
- Implemented the failure-blind offline proposer, common validation/deduplication accounting, all 10 bounded mutation families, validated lineage-preserving child generation, and both CLI generation modes.
- Gate: targeted tests (4 passed), offline CLI generated 12/12 valid scenarios in 12 attempts, full suite (33 passed), Ruff, and strict mypy — passed.

## Phase 6 — experiments and metrics

- Red test: experiment/metrics tests failed during collection because those packages did not exist.
- Implemented deterministic resolved configs, equal 12/50 budgets, same-agent orchestration, own-run-only adaptive targeting, complete manifests, and all required raw metrics/discovery curves.
- Gate: targeted tests (3 passed); quick experiment `evalforge-seed7-b12-f3a38fa735` completed 36 episodes; full suite (36 passed), Ruff, and strict mypy — passed.

## Phase 7 — reports and failure inspection

- Red test: report tests failed during collection because renderers and inspector did not exist.
- Implemented artifact-only Markdown/HTML regeneration, escaped per-failure pages, three-source tables, discovery curves, lineage links, and exact-rule terminal inspection.
- Gate: reporting/golden tests (5 passed); regenerated the quick report; inspected `failure_directed-008-fd_15_0000`; full suite (40 passed), Ruff, and strict mypy — passed.

## Phase 8 — optional live adapter, hardening, and documentation

- Red test: provider/demo tests failed during collection because optional adapter, live proposer, and demo modules did not exist.
- Implemented fake-tested native OpenAI tool calling, raw-message capture, strict final parsing, a JSON-schema-only live proposer, actionable no-key errors, socket-blocked default tests, an end-to-end six-case demo, and complete architecture/experiment/README documentation.
- Gate so far: 44 default tests passed (1 live test deselected), 91% overall coverage, Ruff and strict mypy passed, and the offline demo completed 6 scenarios with 4 unique failure signatures.

## Final Definition of Done — passed 2026-07-17

All commands required by `AGENTS.md` completed successfully from the repository root:

```text
uv sync --all-extras                                      passed (43 packages resolved)
uv run ruff format --check .                              passed (68 files formatted)
uv run ruff check .                                       passed
uv run mypy src/evalforge                                 passed (47 source files)
uv run pytest --cov=evalforge --cov-report=term-missing   passed (44 passed, 1 live deselected, 91% coverage)
uv run evalforge validate scenarios/manual                passed (50 scenarios)
uv run evalforge demo --seed 7                            passed (6 scenarios, 4 unique signatures)
uv run evalforge experiment --config configs/quick.yaml   passed (36 episodes)
```

The required real failure inspection also passed:

```text
uv run evalforge inspect \
  --experiment artifacts/evalforge-seed7-b12-f3a38fa735 \
  --episode failure_directed-008-fd_15_0000
```

### Final experiment

- Experiment ID: `evalforge-seed7-b12-f3a38fa735`
- Accepted/evaluated budget: 12 per source, 36 total.
- Manual: 5 failed episodes, 1 unique signature, 58.3% full stress-test success.
- Random: 8 failed episodes, 7 unique signatures, 33.3% full stress-test success.
- Failure-directed: 12 failed episodes, 1 unique signature, 0% full stress-test success.
- These are descriptive results for the scripted baseline; no superiority or significance claim is made.
- Markdown report: `artifacts/evalforge-seed7-b12-f3a38fa735/report.md`
- HTML report: `artifacts/evalforge-seed7-b12-f3a38fa735/report.html`
- Demo reports: `artifacts/demo-seed7/report.md` and `artifacts/demo-seed7/report.html`.

### Inspected failure example

`failure_directed-008-fd_15_0000` injected `CONFIRMATION_LOST` on `restart_service`. The hidden actual outcome succeeded and changed `identity-api` to healthy, while the visible observation was uncertain. The scripted baseline blindly restarted again and did not read back state. EvalForge reported `CLAIMED_SUCCESS_WITHOUT_VERIFICATION` plus a grounded final-claim uncertainty mismatch, with the relevant event IDs and state diffs.

### Important design decisions

- Actual outcomes and agent-visible observations use separate models and artifact fields.
- Permissions are decided before mutation; idempotency and side effects are auditable.
- The same oracle validator gates manual, random, and failure-directed scenarios.
- Adaptive generation uses only failures observed earlier within its own source run.
- Correctness is deterministic; no LLM judge is used.
- Provider code is optional, fake-tested, and excluded from default network-blocked tests.

### Known limitations

- The simulator intentionally models a compact cloud-operations world, not a real cloud provider.
- The 50-scenario manual corpus is a reviewed compact manifest expanded through deterministic family builders.
- Bounded failure-directed mutations emphasize controlled validity over open-ended diversity; this run repeatedly explored one signature.
- Live-provider behavior is not covered by the offline 91% measurement and depends on model/service behavior.

### Exact optional live commands

```bash
export OPENAI_API_KEY=...
uv sync --all-extras
uv run evalforge run --scenario scenarios/manual/bad_deployment_001.yaml --agent openai
uv run pytest -m live tests/live
```

## Audited real-model evaluation — passed 2026-07-17

The earlier quick report used `ScriptedBaselineAgent` and remains only an offline CI demonstration. It is not used in this model comparison.

### Live TDD and hardening

- Added failing tests first for strict schemas, OpenAI reasoning/function continuation replay, Anthropic tool-result ordering, structured finalization, provider usage/cost, cross-model reports, adaptive seed fallback, stratified selection, observable diagnosis, exact resume, and signature stability.
- Implemented real OpenAI Responses and Anthropic Messages tool loops with strict `submit_final`; no live path falls back to the scripted agent.
- Fixed verifier false positives around resolved uncertainty and verification followed by an incident action.
- Made configuration repair agent-solvable through ordinary log evidence and changed quick manual selection to cover all ten families before repeats.
- Continued adaptive validated seeds when a strong model passed the first seed; children are generated only after an own-run failure.
- Preserved completed model failures during resume so failed episodes are never selectively resampled.
- Made failure signatures independent of final-claim ordering.

### Audited commands

```text
.venv/bin/evalforge experiment --config configs/live_openai.yaml
  passed: evalforge-seed7-b12-652596d9d5, 36 episodes

.venv/bin/evalforge experiment --config configs/live_anthropic.yaml
  passed: evalforge-seed7-b12-6c29c2409f, 36 episodes

.venv/bin/evalforge compare \
  --experiment artifacts/live/evalforge-seed7-b12-652596d9d5 \
  --experiment artifacts/live-audited/evalforge-seed7-b12-6c29c2409f \
  --output artifacts/live-audited/final-model-comparison
  passed: JSON, Markdown, and HTML generated
```

### Audited results

- Equal accepted budget: 12 manual, 12 random, and 12 adaptive scenarios per model; 72 genuine model episodes total.
- `gpt-5.6-sol`: 36/36 task and full stress success; 0 failures/signatures; 0 failure-directed children because its adaptive run found no failure; 249,719 input tokens (158,055 cached), 15,044 output tokens, 207 provider calls, estimated `$0.9887`, 0 provider runtime errors.
- `claude-opus-4-8`: 27/36 task and full stress success (75.0%); 9 failure episodes; 1 unique high-severity signature; 4 lineage-tracked children; 559,768 input tokens, 33,603 output tokens, 218 provider calls, estimated `$3.6389`, 0 provider runtime errors.
- Anthropic consistently wrote timeout `"30"` (string) instead of `30` (integer). The simulator applied the typed mutation, deterministic verification rejected it, and four targeted descendants reproduced the signature.
- Manual and random sets covered all ten scenario families. OpenAI's adaptive seed sweep covered ten; Anthropic's covered nine because four targeted children filled the remaining budget. Each source covered four injected fault families.
- These are descriptive results for one seed and one quick sample per model; no statistical-significance or general superiority claim is made.

Final artifacts:

- `artifacts/live-audited/final-model-comparison/report.md`
- `artifacts/live-audited/final-model-comparison/report.html`
- `artifacts/live/evalforge-seed7-b12-652596d9d5/report.md`
- `artifacts/live-audited/evalforge-seed7-b12-6c29c2409f/report.md`

### Final post-live Definition of Done recheck

```text
uv sync --all-extras                                      passed (45 packages resolved)
uv run ruff format --check .                              passed (74 files formatted)
uv run ruff check .                                       passed
uv run mypy src/evalforge                                 passed (50 source files)
uv run pytest --cov=evalforge --cov-report=term-missing   passed (56 passed, 2 live deselected, 90% coverage)
uv run evalforge validate scenarios/manual                passed (50 scenarios)
uv run evalforge demo --seed 7                            passed (6 scenarios, 4 unique signatures)
uv run evalforge experiment --config configs/quick.yaml   passed (36 episodes, evalforge-seed7-b12-e848f5c094)
```
