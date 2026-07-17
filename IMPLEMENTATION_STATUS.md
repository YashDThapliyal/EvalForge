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
