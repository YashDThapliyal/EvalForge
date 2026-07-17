# Release checklist

Status is recorded from the final audit pass. Items are checked only after direct verification.

## Engineering

- [x] `uv sync --all-extras`
- [x] Ruff formatting
- [x] Ruff linting
- [x] Strict mypy for `src/evalforge`
- [x] Default pytest suite
- [x] Coverage run and threshold review
- [x] 50-scenario manual corpus validation
- [x] Shell syntax check for `scripts/run_model_suite.sh`

## Security and boundaries

- [x] Tracked-file secret-pattern scan found no API key material
- [x] `artifacts/` and provider transcripts remain gitignored
- [x] Default tests block network access
- [x] Production config rejects scripted and implicit agents/models
- [x] Live artifacts record only OpenAI or Anthropic tested-agent identities

## Reproducibility and artifacts

- [x] Regenerate six per-model reports from saved artifacts
- [x] Regenerate the combined comparison without provider calls
- [x] Inspect one successful episode
- [x] Inspect the GPT-5 protocol failure
- [x] Inspect one false-success/claim-grounding failure
- [x] Inspect one failure-directed child and parent lineage
- [x] Verify curated report paths and repository-relative artifact references

## Documentation

- [x] README
- [x] Architecture
- [x] Experiment methodology
- [x] Results
- [x] Limitations
- [x] Reproducibility guide
- [x] Project overview
- [x] Codebase audit

## Release hygiene

- [x] Required command exceptions reconciled with the live-only amendment
- [x] Git diff and whitespace check
- [x] Clean worktree after final commit
- [ ] Owner selects a license before public redistribution

The legacy `evalforge demo --seed 7` gate exits 2 because the live-only amendment deliberately
removed the demo command. The paid `configs/quick.yaml` experiment was not rerun during this
packaging audit; its functional path is covered by tests and the completed six-model artifacts.

Final compact artifacts:

- `results/model-suite/report.md`
- `results/model-suite/report.html`
- `results/model-suite/comparison.json`
