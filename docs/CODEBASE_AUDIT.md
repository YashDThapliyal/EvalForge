# EvalForge codebase audit

Audit date: 2026-07-17  
Scope: all tracked source, tests, configuration, scripts, documentation, the 50-scenario corpus manifest, and the saved six-model artifact tree.

## 1. Executive summary

EvalForge is a working executable evaluation system, not a prompt-only benchmark. Its strongest engineering property is the enforced boundary between agent-visible observations and verifier-visible reality. Live agents operate through native structured tools; deterministic Python verifiers decide success from state, permissions, invariants, traces, claims, and runtime validity.

The implementation is compact and mostly faithful to its live-only contract. The audit found four material release issues and fixed them under regression tests: model protocol failures were eligible for selective resampling on resume, comparison paths were workstation-specific, the partial-side-effect fault was declared but not represented as a partial actual outcome, and adaptive mutation names overstated executable behavior. No hidden-state leakage, state sharing, scripted live fallback, invalid-budget consumption, infrastructure-error inflation, secret exposure, or source-metric arithmetic error was found.

## 2. Final project status

The core simulator, validation, live adapters, experiment runner, deterministic verification, reporting, and CLI inspection paths are implemented. The audited experiment contains 216 genuine live-model episodes and can be summarized or re-rendered without provider calls.

The repository is ready for private technical review. Public redistribution remains a governance decision because no license file is present. The final validation evidence is recorded in [the release checklist](RELEASE_CHECKLIST.md) and `IMPLEMENTATION_STATUS.md`.

## 3. What EvalForge does

EvalForge asks an agent to resolve an operational task inside a local simulated environment. It can make the agent observe something different from what actually happened, retain a complete forensic trace, and independently decide whether the task was completed safely and truthfully. It then converts failures into stable signatures and compares manual, failure-blind random, and adaptive failure-directed scenario sources under equal accepted budgets.

## 4. End-to-end execution flow

1. Load a versioned private scenario.
2. Validate references, reachability, solvability, invariants, nontriviality, and deterministic replay through the hidden oracle plan.
3. Convert the scenario into an explicit public request.
4. Instantiate an isolated simulator and bounded tool registry.
5. Run an explicitly configured OpenAI or Anthropic agent through native tool calls.
6. Record each permission decision, actual outcome, visible observation, state hash/diff, side effect, and raw provider response.
7. Collect a structured `submit_final` result or a structured runtime/protocol failure.
8. Run outcome, invariant, trace-policy, claim-grounding, and runtime verification.
9. Classify any failure and calculate a canonical signature.
10. Persist episode and experiment artifacts, then render Markdown, HTML, JSON, and CLI views.

## 5. Architecture by module

The dependency structure is documented in [ARCHITECTURE.md](ARCHITECTURE.md). Domain schemas are provider-neutral. Simulator and verifier code depend on those schemas, not provider SDKs. Provider code is confined to `agents/openai_agent.py`, `agents/anthropic_agent.py`, and `scenarios/openai_proposer.py`. `execution` composes these services; `reporting` reads persisted artifacts.

The largest modules are the simulator engine, experiment runner, comparison reporter, manual-family builder, and validator. Their size reflects cohesive state machines or orchestration rather than a general framework. No database, web frontend, distributed queue, arbitrary code executor, or LLM correctness judge is present.

## 6. Major implemented features

| Feature | Problem solved | How and where | Test evidence | Concrete example |
|---|---|---|---|---|
| Simulated cloud environment | Real infrastructure is unsafe and irreproducible | Pydantic services, deployments, logs, users/permissions, incidents, monitoring, history, and side effects in `domain/world.py` | Simulator unit/property tests | `payments-api` can be unhealthy on `v2` while `v1` is known-good |
| Structured agent tools | Agents need bounded executable actions | Six JSON-schema tools in `simulator/tools.py`; transitions in `simulator/engine.py` | Tool-schema and engine tests | `rollback_deployment(service_id, target_version, idempotency_key)` |
| Permissions | Unauthorized calls must not mutate state | `permissions.py` decides before transition dispatch | `test_permission_denial_precedes_mutation` | A viewer restart returns `PERMISSION_DENIED` with identical hashes |
| Idempotency | Ambiguous retries can duplicate effects | Per-tool/key records in world state; unkeyed incidents remain non-idempotent | Engine tests | Reusing `inc-1` returns the first incident side effect |
| Fault injection | Real tools can fail or misreport | Scenario-selected `FaultSpec` matches tool, arguments, and occurrence | Engine and scenario tests | `CONFIRMATION_LOST` hides a successful restart |
| Reality vs. observation | Plausible responses can contradict state | `ToolEvent.actual_outcome` and `visible_observation` are separate; registry returns only the latter | Engine and execution tests | Actual rollback failure appears as visible success |
| Scenario specifications | Tests need versioned, reviewable contracts | `ScenarioSpec` contains world, fault plan, oracle, predicates, invariants, lineage, and seed | Scenario round-trip tests | A YAML scenario requires healthy `payments-api` after repair |
| Oracle validation | Generated tests must be solvable | `ScenarioValidator` executes the hidden plan twice and compares hashes | Scenario and corpus integration tests | An unreachable occurrence-9 fault is rejected |
| Public/hidden views | Tested agents must not see answers | `public_view()` constructs a new four-field request | Agent and scenario boundary tests | No fault plan, initial world, oracle, predicates, or lineage appears in JSON |
| Oracle and replay agents | Validation/debugging need deterministic action sources | `agents/oracle.py` and `agents/replay.py`; not selectable in production | Agent and live-only tests | Replay reproduces an oracle trace and final world |
| OpenAI live agent | Evaluate real OpenAI tool behavior | Responses API loop with strict functions and native continuation in `openai_agent.py` | Injected provider-response tests and saved artifacts | GPT-5 protocol failure retained seven raw responses |
| Anthropic live agent | Evaluate real Claude tool behavior | Messages API tool-use/tool-result loop in `anthropic_agent.py` | Injected response tests and saved artifacts | Claude receives assistant tool use followed by user tool result |
| Complete execution traces | Failures need forensic evidence | `episode.py` persists request, trace JSONL, worlds, final, verification, failure, raw messages, usage | Execution/integration tests | Every event includes before/after hash and path-level diff |
| Outcome verification | Final prose cannot prove state | Predicate checks in `verification/outcomes.py` | Verification tests | Wrong deployed version emits `WRONG_VERSION_DEPLOYED` |
| Invariant verification | Task success can hide collateral damage | Protected-state rules in `verification/invariants.py` | Verification tests | Restarting checkout while fixing payments triggers unrelated-state findings |
| Trace-policy verification | Some safety failures are temporal | Read-back, permission, uncertainty, retry, and escalation checks in `trace_policy.py` | Verification tests | Missing read after uncertain restart fails policy |
| Claim grounding | Structured claims may still be false | Claims resolve against actual final state and outcomes in `claims.py` | Verification tests | Claiming `v1` while state is `v2` is critical mismatch |
| Failure taxonomy | Findings need stable analysis categories | Required codes and `FailureRecord` in `taxonomy.py` | Taxonomy coverage tests | Failed mutation plus resolved status becomes false-success code |
| Canonical signatures | Superficial variants should deduplicate | Signature combines behavior context and excludes random/service IDs | Unit/integration signature tests | Two service-name variants share one behavioral signature |
| Random generation | Failure-blind synthesis provides exploration | OpenAI schema-constrained proposal plus common validation/dedup in `random_generator.py` | Proposer/generator tests | Invalid reference is rejected without consuming accepted budget |
| Failure-directed generation | Known weaknesses need targeted retesting | Prior same-arm failure plus bounded distractor/root-cause mutation in `failure_directed.py` | Lineage/determinism tests | Child adds a healthy similarly named shadow service |
| Equal-budget runner | Source comparison must be fair | `ExperimentRunner` fills 12/50 accepted scenarios per source and records attempts separately | Experiment tests | Three source arms each evaluate exactly the configured budget |
| Runtime error separation | Provider outages and model protocol failures imply different conclusions | Comparison separates infrastructure from `AgentProtocolError`; resume preserves protocol failures | Comparison and resume regression tests | GPT-5 missing `submit_final` stays a model failure |
| Multi-format reporting | Engineers need aggregate and episode-level views | JSON/Markdown/static HTML plus `inspect` CLI in `reporting/` | Reporting and golden tests | Failure page shows visible result beside hidden truth |

## 7. Scenario-source comparison

Across 72 episodes per source, manual scenarios achieved 81.9% full success with 8 unique signatures and weighted score 26; random achieved 58.3%, 11, and 41; failure-directed achieved 30.6%, 6, and 19. Signatures are deduplicated across models within each source and counted once at their highest observed severity.

## 8. Live-model experiment summary

The six explicit model IDs are GPT-5.6 Sol, GPT-5, GPT-5 mini, Claude Opus 4.8, Claude Sonnet 5, and Claude Haiku 4.5. Each has 36 episode artifacts, a complete manifest, resolved configuration, raw provider messages, usage, and reports. Aggregate evaluated-agent cost was $8.3154; random-proposal generation cost is not included.

Detailed rates and costs are in [RESULTS.md](RESULTS.md) and the curated [comparison report](../results/model-suite/report.md).

## 9. What the results establish

- Executable verification can expose policy, grounding, invariant, and runtime failures that task predicates alone miss.
- In this experiment, random synthesis explored the broadest distinct and severity-weighted failure set.
- Failure-directed scenarios were hardest and repeatedly exercised observed weaknesses.
- Sonnet 5 had the largest observed task/full reliability gap.
- GPT-5's malformed final response was a model protocol failure; infrastructure failures were zero.

## 10. What the results do not establish

They do not establish statistical significance, general model rankings, superiority outside this simulator, adaptive generation's general inferiority, production-cloud safety, or any RL-training result. They also do not include proposal cost in the tracked episode total.

## 11. Correct interpretation of failure-directed generation

Failure-directed generation is an exploitation mechanism. In the observed run it lowered verified success, demonstrating targeted difficulty, but concentrated on fewer canonical behaviors. It should be described as robustness/regression pressure around known weaknesses. Random generation was the better broad-discovery mechanism in this experiment.

## 12. Verification and reproducibility assessment

State transitions and oracle replay are deterministic under saved scenarios. Scenario and experiment seeds, resolved configuration, state hashes, raw messages, and findings are persisted. Reports regenerate without provider calls. Live sampling is not bit-for-bit reproducible, making immutable saved artifacts the authoritative observation record.

The resume audit found selective-resampling risk: all `agent_runtime_error` episodes were previously retried, including model protocol failures. The runner now preserves `AgentProtocolError` outcomes and retries only other provider/API runtime errors.

## 13. Test and quality assessment

Tests cover unit, property, integration, golden, and credential-gated live layers. Default tests patch socket connection attempts to fail. Critical paths include permission ordering, idempotency, hidden/public separation, isolation, provider continuations, validation replay, verifier codes, metric aggregation, report escaping, source fairness, and live-only configuration boundaries.

Coverage is 90% overall. Simulator core is 93%, validator 92%, episode execution 97%, and the experiment runner 89%; the narrow runner shortfall is concentrated in live construction and exceptional exhaustion paths. CLI coverage is 33% because Typer wiring and many user-error branches are exercised selectively. Final command output is recorded in the release checklist and implementation status.

## 14. Security and secret-handling assessment

No key-shaped secret was found in tracked files. API keys are read only from environment variables and are not written into resolved configuration. Full `artifacts/`, caches, coverage output, and `.DS_Store` are ignored. HTML uses Jinja autoescaping, and random proposals are parsed as schema data rather than executed.

Raw provider messages can contain task and tool data, so the ignored artifact tree should still be reviewed before external sharing. Secret-pattern scanning found several long `sk-`-prefixed strings; field-level inspection identified them as OpenAI `output[].encrypted_content` continuation blobs embedded inside serialized raw messages, not environment API keys. They remain excluded from the committed compact report.

## 15. Known limitations

See [LIMITATIONS.md](LIMITATIONS.md). The most consequential are the single-domain/single-seed design, no statistical analysis, compact simulator, bounded adaptive mutation set, OpenAI-only random proposer, incomplete semantic leakage detection, no hard wall-clock cancellation, and omitted proposal cost.

## 16. Material findings from the audit

| Finding | Severity | Disposition |
|---|---|---|
| Model protocol errors were resampled on resume | High—could selectively change a model failure | Fixed with regression test |
| Comparison JSON stored absolute workstation paths | Medium—reduced portability | Fixed; paths are relative |
| `PARTIAL_SIDE_EFFECT` produced a normal success outcome | Medium—advertised fault behavior inaccurate | Fixed; actual and visible statuses are `partial` with retained diff |
| Mutation registry named seven unimplemented transformations | Medium—overstated capability | Fixed; registry and docs now name only executable transformations |
| HTML comparison buried runtime sensitivity inside Markdown preformatted text | Low usability | Fixed with a dedicated table |
| No repository license | Medium governance | Left for owner decision; documented |
| Legacy offline demo/quick gates conflict with live-only amendment | Medium documentation | Explicitly documented; no fake fallback reintroduced |

## 17. Changes made during this pass

- Added four regression families for resume semantics, portable paths, partial faults, and mutation honesty.
- Preserved model protocol failures during resume.
- Added a real partial-outcome representation.
- Corrected executable mutation declarations.
- Made comparison artifact paths portable and added explicit HTML runtime sensitivity.
- Rebuilt public documentation around the audited six-model result.
- Added a compact committed comparison snapshot and release checklist.

## 18. Recommended future work

These are post-MVP improvements, not missing claims about the completed system:

1. Repeat the experiment across seeds and budgets, then add uncertainty intervals.
2. Add independently implemented, oracle-safe permission, fault-mode, topology, and idempotency mutation operators.
3. Record proposer token usage/cost beside evaluated-agent cost.
4. Add an Anthropic or provider-neutral scenario proposer.
5. Strengthen semantic leakage and near-duplicate checks without using an LLM correctness judge.
6. Add explicit wall-clock cancellation and final-output byte limits.
7. Choose a license and publish a redacted artifact bundle if public replication is desired.
8. Explore verifier dimensions as future RL environment signals; do not conflate this with current training support.

## 19. Final release-readiness verdict

**Ready for private engineering/interview review, with transparent scope limits.** The code and compact results are technically coherent, the saved run is genuine, negative findings are disclosed, and material correctness/reproducibility issues found in this pass were fixed under tests. Public open-source release additionally requires an owner-selected license and a deliberate decision about publishing redacted full artifacts.
