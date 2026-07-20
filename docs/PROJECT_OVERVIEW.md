# EvalForge project overview

Tool-using agents can sound confident while acting incorrectly. A rollback may fail behind a success-like response, a restart may succeed while its confirmation is lost, or an agent may modify the wrong similarly named service. If evaluation sees only the final prose, these failures are easy to miss.

EvalForge is an executable evaluation system for that gap. It places a live OpenAI or Anthropic agent inside a small local cloud-operations world, exposes six structured tools, injects deterministic execution and observation faults, records every state transition, and verifies the result without an LLM judge.

The core design separates reality from observation. Every call records the permission decision, hidden actual outcome, agent-visible observation, state hashes, state diff, side effect, and applied fault. The agent receives only public task context, tool schemas, and visible observations. Deterministic verifiers then check final outcomes, protected invariants, uncertainty/retry policy, structured final claims, and runtime validity.

Scenarios share one versioned schema and one validation pipeline. Manual scenarios cover ten reviewed operational families. Random scenarios are schema-constrained live proposals created without failure feedback. Failure-directed scenarios are bounded children of failures observed earlier in the same adaptive run. Oracle execution proves that accepted scenarios are legal, solvable, invariant-preserving, and deterministically replayable.

The audited experiment evaluated six real models—GPT-5.6 Sol, GPT-5, GPT-5 mini, Claude Opus 4.8, Claude Sonnet 5, and Claude Haiku 4.5—on 12 accepted scenarios from each source. That produced 216 episodes. Every episode retained provider/model identity, raw provider messages, tool trajectories, verifier findings, token usage, and estimated evaluated-agent cost.

The strongest positive result was that executable verification exposed reliability gaps hidden by task-level success. Claude Sonnet 5 and Claude Haiku 4.5, for example, each completed task predicates in 13.9 points more episodes than achieved full deterministic success once policy, claims, invariants, and runtime validity were included.

The experiment also produced an important negative result. Failure-directed scenarios were clearly the hardest, at 30.6% full success against 63.9% for random. But they did not trade that difficulty for breadth, and neither did random: 7 versus 6 unique canonical signatures and weighted scores of 25 versus 19. At one seed with no confidence intervals that difference is not a result. The honest interpretation is that adaptive generation concentrated pressure around known weaknesses and worked as targeted robustness/regression testing; whether it beats random generation at broad discovery is underpowered in this run rather than answered by it.

An audit on 2026-07-20 corrected an earlier version of these figures; see the [correction note](RESULTS.md#correction-2026-07-20).

This distinction is why EvalForge is useful. It can measure both whether an agent reached a desired state and whether it behaved safely and truthfully along the way. It also preserves enough evidence for a researcher or engineer to reproduce reports and inspect exact failures without rerunning paid models.

The completed MVP is deliberately narrow: local Python state, cloud-operations tasks, deterministic verification, file artifacts, and native provider tool calling. It does not mutate real infrastructure, train models, use an LLM correctness judge, or establish general model rankings. Future work could expand scenario domains and mutation operators, add repeated-seed statistical analysis, and translate verifier dimensions into RL environment signals.

Start with the [README](../README.md), read the [architecture](ARCHITECTURE.md), and inspect the [audited results](RESULTS.md).
