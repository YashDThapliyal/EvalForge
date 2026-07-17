# Experiment design

The experiment compares manual, random, and failure-directed sources under the same accepted-scenario count, tested agent, maximum tool calls, verifier, and failure taxonomy.

Random proposals use programmatic templates by default and never receive tested-agent traces or failures. The adaptive source begins with a validated seed in its own run; after evaluation it can mutate only a scenario/failure pair already observed in that same source. Each accepted child records its parent scenario and canonical target signature and contains one to three controlled mutations. Invalid and duplicate candidates remain generation statistics and never consume evaluation budget.

Primary outputs are unique meaningful failure signatures, severity-weighted unique discoveries, and cumulative discovery curves. The report also includes validation/duplicate rates, task and full stress success, high/critical discoveries, failures per ten tests, coverage across scenario and fault families, average tool calls, unsafe retry rate, and false-success rate. Results are descriptive; EvalForge does not assert statistical significance by default.

Reproducibility comes from canonical serialization, explicit seeds, deterministic ordering, complete resolved configurations, fresh world copies, and replayable episode artifacts.

