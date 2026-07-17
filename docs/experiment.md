# Experiment design

The experiment compares manual, random, and failure-directed sources under the same accepted-scenario count, tested agent, maximum tool calls, verifier, and failure taxonomy.

Random proposals use the explicitly configured live OpenAI schema-constrained proposer and never receive tested-agent traces or failures. There is no local proposal fallback. The adaptive source begins with a validated seed in its own run; after evaluation it can mutate only a scenario/failure pair already observed in that same source. Each accepted child records its parent scenario and canonical target signature and contains one to three controlled mutations. Invalid and duplicate candidates remain generation statistics and never consume evaluation budget.

Primary outputs are unique meaningful failure signatures, severity-weighted unique discoveries, and cumulative discovery curves. The report also includes validation/duplicate rates, task and full stress success, high/critical discoveries, failures per ten tests, coverage across scenario and fault families, average tool calls, unsafe retry rate, and false-success rate. Results are descriptive; EvalForge does not assert statistical significance by default.

Auditability comes from canonical serialization, explicit seeds, deterministic ordering, complete resolved configurations, fresh world copies, raw provider messages, and replayable episode artifacts. Live model sampling is not guaranteed to be bit-for-bit reproducible, so reports preserve the exact observed run.

## Live comparison

`configs/live_openai.yaml` and `configs/live_anthropic.yaml` run the same 12-per-source design against real provider models. Manual selection is stratified across all reviewed families. If the adaptive source has not observed a failure, it continues through a deterministic validated seed pool; it creates targeted children only after a failure appears in its own run. A model with no adaptive failure therefore has zero failure-directed children rather than fabricated feedback.

```bash
uv run evalforge compare \
  --experiment artifacts/live/<openai-id> \
  --experiment artifacts/live-audited/<anthropic-id> \
  --output artifacts/live-audited/final-model-comparison
```

The comparison includes model identity, task/full stress success, unique signatures, severity-weighted discoveries, failure-directed child count, tokens, provider calls, estimated cost, and provider runtime failures.
