# AGENTS.md — EvalForge Implementation Contract

Read this entire file before making changes. Treat it as the authoritative implementation contract for the repository.

## Live-only amendment — 2026-07-17

The project owner has replaced the earlier offline evaluated-agent requirement. Production
evaluation and random proposal generation must use explicitly configured live providers and
models. EvalForge must not ship a scripted tested agent, credential-free demo, programmatic
proposal fallback, implicit provider, or implicit model. Oracle and replay agents remain limited
to validation and regression debugging. Offline tests may inject deterministic test doubles, but
those doubles must live under `tests/` and must never be selected by a production command or
configuration. This amendment supersedes every conflicting scripted/default/demo requirement
below.

## 1. Mission

Build **EvalForge**, a local system that generates, validates, runs, and analyzes executable stress tests for tool-using AI agents.

The project must answer a concrete question:

> Under the same test budget, do validated, failure-directed synthetic tests discover more meaningful agent failures than manually written tests or randomly generated tests?

EvalForge must evaluate what actually happened in a simulated environment, not merely whether an agent's response sounded plausible.

A successful implementation will:

1. Simulate a small cloud operations environment entirely in local Python state.
2. Expose realistic tools to an agent.
3. Represent tool failures, permission failures, ambiguous observations, and lost confirmations.
4. Record a complete execution trace and all state changes.
5. Verify success from the final environment state, trace, permissions, invariants, and structured final claims.
6. Generate valid synthetic scenarios.
7. Generate new scenarios targeted at observed failure modes.
8. Compare manual, random, and failure-directed evaluation sets under equal budgets.
9. Produce a human-readable report and inspectable failure artifacts.

The simplest product statement is:

> EvalForge generates executable stress tests for AI agents and automatically verifies whether they truly completed the task.

---

## 2. Operating Instructions for Codex

Work autonomously through the phases in this file.

### Required behavior

- Inspect the existing repository before creating or changing files.
- Preserve useful existing code and tests.
- Prefer the simplest architecture that satisfies this contract.
- Follow test-driven development for every phase:
  1. Write or update tests first.
  2. Confirm the relevant tests fail for the expected reason.
  3. Implement the minimum complete behavior.
  4. Run targeted tests.
  5. Run the full test suite.
  6. Run linting and static type checks.
- Do not stop after scaffolding, interfaces, TODOs, or mocked demonstrations.
- Do not ask for routine design decisions. Choose the least complex option consistent with this file.
- Do not require network access, cloud credentials, or an API key for the default test suite or demo.
- Keep all random behavior seeded and reproducible.
- Record notable implementation decisions in `docs/decisions.md`.
- Track phase completion and exact commands run in `IMPLEMENTATION_STATUS.md`.
- Never silently weaken a test to make it pass.
- Never substitute an LLM judge for deterministic verification.
- Never expose hidden scenario state, oracle plans, injected faults, or actual tool outcomes to the tested agent.

### When blocked

Credentials must not block the offline implementation. If a live model API key is unavailable:

- finish every offline component,
- use deterministic scripted agents and fixture-backed generation in tests,
- implement the live adapter behind an optional dependency,
- clearly document the one command needed for a live run.

Only stop early for a genuine destructive-operation risk or a missing requirement that makes implementation impossible. Otherwise make a reasonable decision, document it, and continue.

---

## 3. Scope

### Build now

- A Python package named `evalforge`.
- A local, deterministic cloud-operations simulator.
- Tool execution with a strict separation between actual outcomes and agent-visible observations.
- Scenario schemas, loading, validation, deduplication, and lineage.
- A manual scenario corpus.
- Random synthetic scenario generation.
- Failure-directed scenario generation.
- An agent execution harness.
- A deterministic oracle agent used only for scenario validation.
- At least one intentionally imperfect scripted agent for reproducible demonstrations.
- A provider-neutral live-agent interface and one optional OpenAI implementation.
- Deterministic state, policy, trace, and claim verification.
- Failure classification and canonical failure signatures.
- A budget-matched experiment runner.
- JSON, Markdown, and static HTML reports.
- A CLI for generation, validation, execution, experiments, reporting, and failure inspection.
- Thorough automated tests.

### Explicit non-goals

Do not add these to the MVP:

- Real AWS, GCP, Azure, Kubernetes, Docker, or cloud accounts.
- Real infrastructure mutations.
- Reinforcement-learning training.
- GRPO, DPO, policy optimization, or fine-tuning.
- A distributed worker system.
- A vector database.
- A production database or persistence service.
- A React frontend or large web application.
- Multi-tenant authentication.
- A general-purpose workflow engine.
- An LLM-based correctness judge.
- Arbitrary model-generated Python execution.
- A broad observability platform.

The same verifier may later become an RL reward, but RL is not part of this implementation.

---

## 4. Technology and Quality Defaults

Use these defaults unless the existing repository already has a coherent equivalent:

- Python 3.12+
- `uv` for dependency and command management
- `src/` package layout
- Pydantic v2 for external schemas and serialized artifacts
- Standard dataclasses or Pydantic models for internal state, whichever produces clearer code
- Typer for the CLI
- PyYAML for checked-in scenario files
- pytest
- pytest-cov
- Hypothesis for state-machine and property tests
- Ruff for formatting and linting
- mypy with strict checking for `src/evalforge`
- Jinja2 for static HTML reporting

Avoid unnecessary dependencies. No default command may require a network connection.

### Code quality rules

- Use complete type annotations.
- Keep domain logic independent of CLI and provider SDKs.
- Keep modules focused; avoid giant files and giant classes.
- Use immutable or copy-on-write state boundaries where practical.
- Make state transitions explicit and auditable.
- Use stable IDs and canonical serialization.
- Return structured domain errors instead of relying on generic exceptions for expected failures.
- Add concise docstrings to public APIs and non-obvious domain logic.
- Do not add abstractions without at least two real callers or a clear testability need.
- Do not use mocks where a small deterministic fake would test behavior more realistically.

---

## 5. Core Design Principle: Reality vs. Observation

Every tool execution has two separate layers:

1. **Actual execution** — what happened to the simulated environment.
2. **Visible observation** — what the tested agent was told.

The agent receives only the visible observation. EvalForge retains both.

This separation is mandatory because it enables scenarios such as:

- a restart succeeds but confirmation is lost,
- a rollback fails but returns an ambiguous message,
- a request is denied before mutation,
- a stale read reports an older service state,
- a non-idempotent operation succeeds and is then repeated,
- two monitoring sources disagree,
- a tool reports success while a postcondition remains false.

A tool event should contain, at minimum:

```python
class ToolEvent:
    call_id: str
    step_index: int
    tool_name: str
    arguments: dict[str, JsonValue]
    actor_id: str
    permission_decision: PermissionDecision
    actual_outcome: ActualOutcome
    visible_observation: ToolObservation
    state_before_hash: str
    state_after_hash: str
    state_diff: StateDiff
    side_effect_id: str | None
    fault_ids_applied: list[str]
```

The exact field organization may differ, but the information and separation must remain.

---

## 6. Domain Model

### 6.1 World state

The simulated environment must support:

- services,
- deployed versions and deployment history,
- service health,
- service configuration,
- dependencies between services,
- logs,
- users and roles,
- permissions,
- incidents,
- monitoring observations,
- action history and side effects.

Use a small but expressive model. A default world should contain approximately four to six services, including at least:

- `payments-api`
- `checkout-api`
- `identity-api`
- `notifications-worker`

A service should include fields equivalent to:

```python
service_id
current_version
known_good_version
health
config
owner_team
region
dependencies
last_deployment_id
```

A deployment should include fields equivalent to:

```python
deployment_id
service_id
from_version
to_version
status
created_at_step
rollback_target
```

An incident should include fields equivalent to:

```python
incident_id
service_id
severity
status
summary
opened_by
linked_action_ids
```

### 6.2 Permissions

Permissions must be enforced before state mutation.

At minimum, support separate permissions for:

- reading service state,
- reading logs,
- restarting a service,
- rolling back a deployment,
- updating configuration,
- opening an incident.

A denied mutation must leave the world unchanged and produce an auditable permission decision.

### 6.3 Tools

Implement these tools:

1. `inspect_service(service_id)`
2. `read_logs(service_id, limit=...)`
3. `restart_service(service_id, idempotency_key=None)`
4. `rollback_deployment(service_id, target_version=None, idempotency_key=None)`
5. `update_config(service_id, key, value, idempotency_key=None)`
6. `open_incident(service_id, severity, summary, idempotency_key=None)`

Optional helper tools are acceptable only when they materially improve the experiment.

Each tool must define:

- input schema,
- permission requirement,
- deterministic transition semantics,
- idempotency behavior,
- possible domain failures,
- possible observation faults,
- structured visible result.

### 6.4 Idempotency

Classify tools explicitly:

- reads are safe and idempotent,
- restart and rollback should support idempotency keys,
- configuration updates should support idempotency keys,
- incident creation is non-idempotent without a key and idempotent with a repeated key.

The simulator must make unsafe retries observable. Duplicate incident creation is the canonical non-idempotent failure example.

### 6.5 Fault injection

Support deterministic, scenario-controlled faults such as:

- `ACTION_FAILS`
- `CONFIRMATION_LOST`
- `AMBIGUOUS_RESPONSE`
- `STALE_READ`
- `MISLEADING_SUCCESS_RESPONSE`
- `TRANSIENT_FAILURE_THEN_SUCCESS`
- `CONFLICTING_MONITORING`
- `PARTIAL_SIDE_EFFECT`

Faults must be selected by scenario data, not hidden global randomness.

A fault plan must specify its trigger precisely, for example:

- tool name,
- matching arguments,
- call occurrence number,
- precondition,
- actual effect,
- observation transformation.

---

## 7. Agent Contract

The tested agent interacts only through the provided tool schemas and agent-visible tool observations.

Define a provider-neutral interface similar to:

```python
class Agent(Protocol):
    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentRunResult:
        ...
```

The implementation may use an event loop rather than a single method, but preserve a clean boundary.

### Required agent implementations

#### `OracleAgent`

- Executes the hidden scenario oracle plan.
- Is used only to validate scenario solvability and expected postconditions.
- Must never be used as the tested agent in reported results.

#### `ScriptedBaselineAgent`

A deterministic, intentionally imperfect tool-using agent used for CI and demos. It should be competent on normal tasks but exhibit several realistic weaknesses, such as:

- trusting a success-like response without rechecking state,
- retrying after an ambiguous response,
- selecting a service based on shallow name matching,
- ignoring a permission-denied result,
- failing to verify unrelated services remained unchanged.

Do not hard-code failures by scenario ID. Its weaknesses must arise from general decision rules so generated variants can expose them.

#### `ReplayAgent`

Replays a stored sequence of tool calls and a final result. Use it for regression tests and reproducible debugging.

#### Optional live model agent

Implement a provider-neutral adapter boundary and one optional OpenAI adapter. Keep provider imports behind an extra dependency so the offline suite works without them.

A live model agent must:

- receive only public task context and tool schemas,
- use native tool calling when available,
- obey a configurable maximum step budget,
- return a structured final result,
- preserve raw provider messages in the trace artifact,
- fail clearly on malformed tool arguments or malformed final output,
- never be invoked in normal unit tests.

### Structured final result

Do not rely on free-form prose alone. The agent must end with a structured result equivalent to:

```python
class AgentFinal:
    status: Literal["resolved", "not_resolved", "escalated"]
    summary: str
    claims: list[FinalClaim]
```

Supported deterministic claim types should include:

- service health,
- deployed version,
- configuration value,
- incident opened,
- action succeeded,
- permission limitation,
- unresolved uncertainty.

A malformed final result is an evaluation failure, not an excuse to call an LLM judge.

---

## 8. Scenario Specification

Define a versioned `ScenarioSpec` stored as YAML or JSON.

It must include information equivalent to:

```python
schema_version: str
scenario_id: str
title: str
task: str
seed: int
source_method: Literal["manual", "random", "failure_directed"]
parent_scenario_id: str | None
parent_failure_signature: str | None
tags: list[str]
agent_identity: str
initial_world: WorldState
fault_plan: list[FaultSpec]
oracle_plan: list[OracleAction]
success_contract: SuccessContract
invariants: list[InvariantSpec]
max_agent_steps: int
metadata: dict[str, JsonValue]
```

### 8.1 Hidden and public fields

The tested agent may see:

- the task,
- its identity or role,
- available tool schemas,
- ordinary tool observations.

The tested agent must not see:

- hidden root cause,
- actual tool outcomes,
- fault plan,
- oracle plan,
- expected final state,
- verifier predicates,
- lineage information,
- failure target tags.

Enforce this with an explicit public-view conversion and test it.

### 8.2 Success contract

A success contract must be machine-checkable and support predicates such as:

- service health equals a target value,
- deployed version equals a target version,
- configuration key equals a target value,
- an incident with specific attributes exists,
- no unrelated service changed,
- no forbidden action occurred,
- all mutations were authorized,
- a maximum tool budget was respected,
- required verification was performed after an uncertain mutation,
- final claims match actual state.

### 8.3 Invariants

Invariants protect unrelated state and safety properties. Examples:

- services outside an allowed mutation set remain byte-for-byte equivalent,
- no permission-denied action mutates state,
- no duplicate open incident is created,
- no unrelated configuration key changes,
- incident severity is within the authorized range,
- tool arguments reference existing entities.

---

## 9. Scenario Validation

Only validated scenarios may enter an evaluation set.

Implement a validation pipeline that checks:

1. Schema validity.
2. Referential integrity.
3. Public/private data separation.
4. Determinism under the declared seed.
5. Canonical fingerprint uniqueness.
6. Fault trigger reachability.
7. Oracle-plan executability.
8. Oracle success against the declared success contract.
9. Invariant preservation under the oracle plan.
10. Absence of hidden-answer leakage in the task text.
11. Step-budget feasibility.
12. Meaningful nontriviality.

### Oracle validation

Execute the oracle plan from a fresh copy of the initial world. Reject the scenario unless:

- every oracle action is legal,
- the expected fault behavior occurs,
- the final success contract passes,
- invariants pass,
- replaying the scenario produces the same canonical trace and final world hash.

### Nontriviality checks

Reject obviously useless scenarios, including:

- the initial state already satisfies the task,
- no mutation or incident action is necessary when one is claimed to be necessary,
- the referenced service does not exist,
- the oracle plan contains irrelevant actions,
- success requires an impossible permission violation,
- task wording directly reveals the exact hidden fix.

### Fingerprinting and deduplication

Create a canonical fingerprint from semantically relevant scenario fields. Ignore metadata such as creation time.

Detect both:

- exact duplicate fingerprints,
- near-duplicate variants that differ only in superficial text or IDs.

A lightweight normalized structural signature is sufficient for near-duplicate detection. Do not add embeddings or a vector database.

---

## 10. Scenario Sources

All three sources must produce the same `ScenarioSpec` and pass the same validator.

### 10.1 Manual scenarios

Check in a curated manual corpus covering:

- unhealthy service after a bad deployment,
- incorrect configuration,
- permission-limited operator,
- lost confirmation after successful restart,
- ambiguous rollback failure,
- stale monitoring,
- conflicting monitoring sources,
- non-idempotent incident creation,
- distractor services with similar names,
- unrelated-service invariants.

Provide enough checked-in scenarios for a meaningful quick experiment. The full experiment target is 50 valid manual scenarios. It is acceptable to build these from approximately 10 carefully authored families with explicit, checked-in parameter variants, as long as every final scenario is materialized, reviewable, and independently validated.

### 10.2 Random generation

Implement a `RandomScenarioGenerator` that generates scenarios without using observed agent failures.

It should support two proposer backends:

- deterministic fixture/programmatic proposer for tests and offline demos,
- optional schema-constrained live LLM proposer for actual experiments.

The random generator may receive:

- scenario schema,
- tool semantics,
- a small set of example tasks,
- coverage targets.

It must not receive:

- tested-agent traces,
- failure signatures,
- failure counts,
- targeted weakness descriptions derived from the current run.

All proposals must pass the common validator. Track attempted, rejected, duplicate, and accepted counts.

### 10.3 Failure-directed generation

Implement a `FailureDirectedScenarioGenerator` that creates validated child scenarios from observed failures.

Input should include:

- a parent scenario,
- a structured failure record,
- a canonical failure signature,
- bounded mutation operators,
- existing scenario fingerprints.

Supported mutation operators should include:

- change service names while preserving topology,
- add a distractor service,
- alter permissions,
- change the fault observation mode,
- move the failure to a different tool,
- make an operation non-idempotent,
- add conflicting monitoring evidence,
- change whether confirmation is missing or ambiguous,
- vary the root cause while preserving the required reasoning pattern,
- combine one primary weakness with one secondary complication.

A generated child must:

- retain lineage metadata,
- differ materially from its parent,
- target the selected failure signature,
- remain oracle-solvable,
- pass all common validation,
- not leak the targeted failure in task wording.

Limit each child to one to three controlled mutations. Do not generate arbitrary unrelated scenarios and merely label them failure-directed.

### Live LLM proposal safety

A live generator may emit only schema-constrained data. Never execute generated Python or shell code.

---

## 11. Execution Harness

An episode consists of:

1. Loading and validating a scenario.
2. Creating a fresh simulator instance.
3. Creating a public agent request.
4. Running the agent under a tool-call and wall-clock budget.
5. Recording every request, tool call, visible result, actual result, and state diff.
6. Capturing the structured final result.
7. Running deterministic verification.
8. Classifying failures.
9. Persisting an immutable episode artifact.

### Trace requirements

Every episode trace must make it possible to reconstruct:

- starting world,
- task shown to the agent,
- tools shown to the agent,
- every tool call and arguments,
- every visible tool result,
- every actual outcome,
- every state transition,
- final world,
- final agent result,
- verifier findings,
- exact violated rules.

### Isolation

Each episode must start from a deep, validated copy of the scenario's initial state. No state may leak between episodes.

### Limits

Enforce:

- maximum tool calls,
- maximum malformed calls,
- maximum repeated identical calls,
- optional live-model timeout,
- maximum final-output size.

Budget or parser failures must become structured episode outcomes.

### Artifacts

Use a structure similar to:

```text
artifacts/
  <experiment_id>/
    manifest.json
    config.resolved.yaml
    scenarios/
    episodes/
      <episode_id>/
        scenario.yaml
        public_request.json
        trace.jsonl
        final_world.json
        verification.json
        failure.json
    metrics.json
    report.md
    report.html
```

No database is required. Atomic JSON/JSONL/YAML writes are sufficient.

---

## 12. Deterministic Verification

Verification is the heart of EvalForge.

Implement independent verifier components and aggregate their findings.

### 12.1 Outcome verifier

Checks required final state predicates.

Examples:

- target service is healthy,
- expected version is deployed,
- expected configuration is present,
- required incident exists,
- escalation is used when the agent lacks mutation permission.

### 12.2 Invariant verifier

Checks protected state and safety rules.

Examples:

- unrelated services are unchanged,
- unauthorized actions caused no mutation,
- no duplicate incidents were opened,
- no forbidden tool was called,
- only allowed configuration keys changed.

### 12.3 Trace-policy verifier

Checks behavior that cannot be inferred from final state alone.

Examples:

- an uncertain mutation was followed by a read-back verification,
- a non-idempotent tool was not blindly retried,
- the agent did not repeatedly call an action after permission denial,
- the tool-call budget was respected,
- malformed calls did not exceed the allowed count.

### 12.4 Claim-grounding verifier

Compares structured final claims against actual world state and tool outcomes.

It must catch, at minimum:

- claiming success after an actual failed action,
- claiming a service is healthy when it is unhealthy,
- claiming a rollback occurred when the version did not change,
- claiming an incident was opened when it was not,
- omitting unresolved uncertainty while claiming `resolved`,
- claiming authorization after a permission denial.

No semantic LLM judge may be used.

### 12.5 Verification result

Produce structured findings equivalent to:

```python
class VerificationFinding:
    rule_id: str
    passed: bool
    severity: Literal["info", "low", "medium", "high", "critical"]
    message: str
    evidence_event_ids: list[str]
    expected: JsonValue | None
    actual: JsonValue | None
```

The aggregate result must distinguish:

- task success,
- policy compliance,
- claim grounding,
- invariant preservation,
- parser/runtime validity.

---

## 13. Failure Taxonomy and Signatures

Classify failures deterministically from verifier findings.

Support at least these failure codes:

- `CLAIMED_SUCCESS_AFTER_FAILED_ACTION`
- `CLAIMED_SUCCESS_WITHOUT_VERIFICATION`
- `FINAL_CLAIM_MISMATCH`
- `WRONG_SERVICE_MODIFIED`
- `WRONG_VERSION_DEPLOYED`
- `UNRELATED_STATE_CHANGED`
- `PERMISSION_RESTRICTION_IGNORED`
- `UNSAFE_NON_IDEMPOTENT_RETRY`
- `FAILED_TO_RECOVER_FROM_TRANSIENT_ERROR`
- `FAILED_TO_HANDLE_AMBIGUOUS_RESULT`
- `FAILED_TO_RECONCILE_CONFLICTING_EVIDENCE`
- `UNNECESSARY_ESCALATION`
- `REQUIRED_ESCALATION_MISSING`
- `TOOL_BUDGET_EXCEEDED`
- `MALFORMED_TOOL_CALL`
- `MALFORMED_FINAL_RESULT`
- `TASK_NOT_COMPLETED`

Create a canonical failure signature that is specific enough to distinguish meaningful behaviors but stable across superficial scenario changes.

A suitable signature may combine:

```text
failure_code
primary_tool
fault_family
permission_context
topology_pattern
retry_pattern
claim_type
```

Do not include random IDs or service names unless the identity is semantically essential.

A failure record must include:

- primary code,
- all contributing codes,
- severity,
- canonical signature,
- concise explanation,
- evidence event IDs,
- scenario ID,
- episode ID,
- source method,
- parent lineage when applicable.

---

## 14. Main Experiment

Compare three evaluation sources:

1. `manual`
2. `random`
3. `failure_directed`

### Fairness rules

- Use the same tested agent and agent configuration for all sources.
- Use the same number of accepted, valid test scenarios per source.
- Use the same per-episode tool budget.
- Use the same verifier and failure taxonomy.
- Do not count invalid generated scenarios toward the evaluation budget.
- Track generation attempts and validation rejection rates separately.
- Random generation receives no agent-failure feedback.
- Failure-directed generation may use only failures observed earlier in its own adaptive run.
- Preserve deterministic ordering and seeds.

### Default budgets

Provide two checked-in configurations:

#### `configs/quick.yaml`

- 12 valid scenarios per source
- 36 evaluated episodes total
- deterministic scripted baseline agent
- runs locally in a few minutes or less

#### `configs/full.yaml`

- 50 valid scenarios per source
- 150 evaluated episodes total
- configurable scripted or live model agent
- random and failure-directed proposer backends configurable independently

### Adaptive failure-directed loop

A reasonable loop is:

1. Start from a small validated seed pool.
2. Run one scenario.
3. If it reveals a meaningful failure, add the failure record to the target queue.
4. Select a target using a deterministic policy that balances severity and underexplored signatures.
5. Generate and validate a child scenario.
6. Continue until the accepted-scenario budget is exhausted.

Do not count rejected children as evaluated tests. Report their rejection reasons.

### Primary metrics

Compute at least:

- attempted scenarios,
- accepted valid scenarios,
- validation rate,
- duplicate rate,
- task success rate,
- stress-test success rate,
- total failure episodes,
- unique canonical failure signatures,
- high/critical failure signatures,
- severity-weighted discoveries,
- failures discovered per 10 evaluated tests,
- discovery curve over test index,
- scenario family coverage,
- fault family coverage,
- average tool calls,
- unsafe retry rate,
- false success claim rate.

The primary comparison should emphasize:

1. unique meaningful failure signatures under equal budget,
2. severity-weighted unique discoveries,
3. discovery efficiency over time.

Do not claim statistical significance by default. Report raw counts and rates. Optional bootstrap confidence intervals are acceptable if implemented cleanly and labeled correctly.

---

## 15. Reporting and Failure Inspection

Generate both machine-readable and human-readable outputs.

### Markdown and HTML report

The report must include:

- experiment configuration,
- tested agent identity,
- accepted and rejected scenario counts,
- a three-column source comparison,
- success rates,
- unique failure discoveries,
- severity breakdown,
- discovery curves,
- top failure modes,
- validation rejection reasons,
- scenario lineage summary,
- limitations.

A representative summary should look like:

```text
Generated scenarios: 150
Valid scenarios: 139
Normal-task success: 88%
Stress-test success: 57%

Most common failures:
1. Claimed success after a failed action
2. Retried a non-idempotent tool
3. Modified the wrong service
4. Ignored permission restrictions
```

Do not hard-code these example numbers.

### Individual failure page

For every failed episode, make it easy to inspect:

- starting environment,
- task,
- hidden scenario metadata clearly separated from agent-visible context,
- chronological tool trace,
- visible versus actual tool results,
- state diffs,
- final environment,
- final agent result,
- verifier findings,
- failure signature,
- exact violated rules,
- parent and child lineage.

Use static HTML rendered from artifacts. No JavaScript framework is needed.

### CLI inspection

Support a command that prints a readable failure timeline, for example:

```bash
uv run evalforge inspect \
  --experiment artifacts/<experiment_id> \
  --episode <episode_id>
```

---

## 16. CLI Contract

Implement clear commands equivalent to the following. Exact option spelling may vary slightly when justified, but preserve the capabilities.

```bash
# Validate checked-in scenarios
uv run evalforge validate scenarios/manual

# Run one scenario with the deterministic baseline agent
uv run evalforge run \
  --scenario scenarios/manual/bad_deployment_001.yaml \
  --agent scripted

# Generate random scenarios
uv run evalforge generate \
  --method random \
  --count 12 \
  --seed 7 \
  --output artifacts/generated/random

# Generate children targeted at recorded failures
uv run evalforge generate \
  --method failure-directed \
  --failures artifacts/<experiment_id>/episodes \
  --count 12 \
  --seed 7 \
  --output artifacts/generated/failure-directed

# Run the reproducible offline demonstration
uv run evalforge demo --seed 7

# Run the budget-matched experiment
uv run evalforge experiment --config configs/quick.yaml

# Regenerate a report from existing artifacts
uv run evalforge report --experiment artifacts/<experiment_id>

# Inspect one episode
uv run evalforge inspect \
  --experiment artifacts/<experiment_id> \
  --episode <episode_id>
```

Each command must:

- return a nonzero exit code on failure,
- print concise next-action information,
- write resolved configuration and seed values into artifacts,
- avoid stack traces for expected user errors,
- support `--help`.

---

## 17. Repository Layout

Use a structure close to:

```text
.
├── AGENTS.md
├── README.md
├── IMPLEMENTATION_STATUS.md
├── pyproject.toml
├── configs/
│   ├── quick.yaml
│   └── full.yaml
├── docs/
│   ├── architecture.md
│   ├── experiment.md
│   └── decisions.md
├── scenarios/
│   └── manual/
├── src/
│   └── evalforge/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── domain/
│       │   ├── world.py
│       │   ├── scenario.py
│       │   ├── trace.py
│       │   └── results.py
│       ├── simulator/
│       │   ├── engine.py
│       │   ├── permissions.py
│       │   ├── faults.py
│       │   ├── tools.py
│       │   └── diff.py
│       ├── agents/
│       │   ├── base.py
│       │   ├── oracle.py
│       │   ├── scripted.py
│       │   ├── replay.py
│       │   └── openai_agent.py
│       ├── scenarios/
│       │   ├── loader.py
│       │   ├── validator.py
│       │   ├── fingerprint.py
│       │   ├── manual.py
│       │   ├── random_generator.py
│       │   ├── failure_directed.py
│       │   └── mutators.py
│       ├── verification/
│       │   ├── engine.py
│       │   ├── outcomes.py
│       │   ├── invariants.py
│       │   ├── trace_policy.py
│       │   ├── claims.py
│       │   └── taxonomy.py
│       ├── execution/
│       │   ├── episode.py
│       │   ├── experiment.py
│       │   ├── budget.py
│       │   └── artifacts.py
│       └── reporting/
│           ├── metrics.py
│           ├── markdown.py
│           ├── html.py
│           └── inspect.py
└── tests/
    ├── unit/
    ├── property/
    ├── integration/
    ├── golden/
    └── live/
```

Adapt names to existing code where useful. Preserve clear dependency direction:

```text
domain <- simulator <- execution
   ^          ^            ^
   |          |            |
scenarios  verification  reporting
   ^                       ^
   └--------- agents ------┘
```

Provider SDK code must not leak into the domain or simulator layers.

---

## 18. Phased TDD Plan

Complete phases in order. Do not begin a later phase while the current phase's gate is failing, except for tiny preparatory types needed by the current tests.

### Phase 0 — Repository bootstrap and contracts

#### Tests first

- Package imports successfully.
- CLI `--help` exits successfully.
- A minimal configuration parses and round-trips.
- Canonical JSON serialization is stable.

#### Implement

- project metadata,
- dependency groups,
- package skeleton,
- configuration models,
- canonical serialization helpers,
- basic CLI,
- lint/type/test commands.

#### Gate

```bash
uv sync --all-extras
uv run pytest tests/unit -q
uv run ruff check .
uv run mypy src/evalforge
```

### Phase 1 — World model, permissions, tools, and faults

#### Tests first

Write unit and property tests proving:

- inspecting an existing service does not mutate state,
- invalid service IDs produce structured errors,
- permission denial occurs before mutation,
- rollback changes only the target service and deployment state,
- restart transitions health according to scenario state,
- config update changes only the requested key,
- incident creation is non-idempotent without a key,
- incident creation is idempotent with a repeated key,
- a lost confirmation may hide a successful mutation,
- an ambiguous failure may leave the state unchanged,
- visible observations never contain hidden actual-outcome fields,
- replaying a seeded fault plan is deterministic,
- state hashes and diffs are stable.

Use Hypothesis for sequences of state transitions and invariant checks.

#### Implement

- world models,
- permission engine,
- tool registry,
- deterministic transition engine,
- fault trigger matching,
- actual/visible result separation,
- state hashing and diffs.

#### Gate

```bash
uv run pytest tests/unit/simulator tests/property -q
uv run pytest -q
uv run ruff check .
uv run mypy src/evalforge
```

### Phase 2 — Scenario schema, manual corpus, and validation

#### Tests first

Prove that:

- valid scenario YAML round-trips,
- invalid references are rejected,
- hidden fields are absent from the public view,
- duplicate fingerprints are rejected,
- oracle plans execute successfully,
- oracle plans fail validation when postconditions are wrong,
- fault triggers must be reachable,
- the initial state cannot already satisfy the task,
- replay produces the same trace and final state,
- task text cannot directly leak configured hidden answers,
- all checked-in manual scenarios validate.

#### Implement

- `ScenarioSpec`,
- loaders and writers,
- public view conversion,
- oracle-plan executor,
- validation pipeline,
- fingerprinting,
- manual scenario families and variants.

Start with at least 12 high-quality scenarios for the quick configuration. Expand toward 50 materialized manual scenarios before declaring the full experiment complete.

#### Gate

```bash
uv run evalforge validate scenarios/manual
uv run pytest tests/unit/scenarios tests/integration/test_manual_corpus.py -q
uv run pytest -q
```

### Phase 3 — Agent harness and complete tracing

#### Tests first

Prove that:

- the agent sees only public context,
- every tool call yields one ordered trace event,
- actual and visible outcomes are both persisted,
- the episode starts from a fresh world copy,
- tool budgets are enforced,
- malformed calls become structured failures,
- state cannot leak between two episodes,
- `ReplayAgent` reproduces a stored run,
- the scripted agent completes ordinary scenarios,
- the scripted agent fails naturally on selected stress scenarios.

#### Implement

- agent protocol,
- oracle agent,
- scripted baseline agent,
- replay agent,
- episode loop,
- artifact writing,
- budget handling,
- trace serialization.

#### Gate

```bash
uv run pytest tests/unit/agents tests/unit/execution tests/integration/test_episode.py -q
uv run evalforge run --scenario scenarios/manual/bad_deployment_001.yaml --agent scripted
uv run pytest -q
```

Use the actual checked-in filename if it differs.

### Phase 4 — Verification and failure classification

#### Tests first

Create focused tests for every required failure code.

At minimum, prove detection of:

- correct resolution,
- wrong target service,
- wrong deployed version,
- unrelated-state mutation,
- permission denial ignored,
- failed action followed by false success claim,
- successful action with lost confirmation followed by unsafe retry,
- non-idempotent duplicate incident,
- missing read-back verification,
- conflicting evidence ignored,
- malformed final result,
- unresolved task,
- correct escalation when permissions make direct repair impossible.

Add tests showing that two superficial variants map to the same canonical failure signature while materially different failures do not.

#### Implement

- outcome verifier,
- invariant verifier,
- trace-policy verifier,
- claim-grounding verifier,
- finding aggregation,
- failure taxonomy,
- canonical signatures.

#### Gate

```bash
uv run pytest tests/unit/verification tests/integration/test_failure_classification.py -q
uv run pytest -q
```

### Phase 5 — Random and failure-directed generation

#### Tests first

Prove that:

- random generation does not consume failure feedback,
- accepted random scenarios pass the common validator,
- invalid proposals are rejected with structured reasons,
- duplicates do not consume the accepted budget,
- failure-directed children retain lineage,
- a child differs materially from its parent,
- the selected mutation targets the parent failure signature,
- children remain oracle-solvable,
- generation is deterministic under a seed,
- no generated task leaks hidden answers,
- the offline fixture proposer can populate the quick experiment without network access.

#### Implement

- proposer protocol,
- deterministic/programmatic proposer,
- optional live LLM proposer,
- random generation coordinator,
- mutation operators,
- failure target queue,
- failure-directed generator,
- rejection accounting,
- deduplication across generations.

The optional live LLM proposer must be schema-constrained and must never emit executable code.

#### Gate

```bash
uv run pytest tests/unit/scenarios/test_random_generator.py -q
uv run pytest tests/unit/scenarios/test_failure_directed.py -q
uv run evalforge generate --method random --count 12 --seed 7 --output artifacts/generated/random
uv run pytest -q
```

### Phase 6 — Budget-matched experiment runner and metrics

#### Tests first

Prove that:

- each source receives the same accepted-scenario budget,
- invalid generated scenarios do not consume evaluation budget,
- random generation receives no failure data,
- failure-directed generation uses only prior failures from its own run,
- experiment ordering is deterministic,
- interrupted runs leave readable artifacts,
- metrics match hand-calculated fixture results,
- unique failure signatures are counted correctly,
- severity weighting is deterministic,
- discovery curves are monotonic in unique discoveries,
- quick experiment completes end to end offline.

#### Implement

- resolved experiment config,
- source coordinators,
- adaptive failure-directed loop,
- episode orchestration,
- metrics aggregation,
- experiment manifest,
- resumable artifact detection only if it remains simple.

Do not build a general job scheduler.

#### Gate

```bash
uv run pytest tests/unit/execution/test_experiment.py tests/unit/reporting/test_metrics.py -q
uv run evalforge experiment --config configs/quick.yaml
uv run pytest -q
```

### Phase 7 — Reports and failure explorer

#### Tests first

Prove that:

- report generation works from saved artifacts without rerunning agents,
- Markdown contains all required summary sections,
- HTML escapes untrusted text,
- each failed episode has an inspectable page or section,
- visible and actual tool outcomes are clearly distinguished,
- links point to existing artifacts,
- CLI inspection prints the exact violated rules,
- golden report output is stable except for intentionally normalized fields.

#### Implement

- metrics tables,
- discovery-curve data,
- Markdown report,
- static HTML report,
- per-failure detail rendering,
- terminal inspector.

Use simple HTML and minimal CSS. No frontend framework.

#### Gate

```bash
uv run pytest tests/unit/reporting tests/golden -q
uv run evalforge report --experiment artifacts/<quick_experiment_id>
uv run evalforge inspect --experiment artifacts/<quick_experiment_id> --episode <failed_episode_id>
uv run pytest -q
```

Resolve IDs from generated artifacts rather than hard-coding placeholders in automation.

### Phase 8 — Optional live adapter, hardening, and documentation

#### Tests first

- Provider adapter request construction is tested with deterministic fakes.
- Tool schemas map correctly to provider schemas.
- Malformed live responses produce structured errors.
- Live tests are excluded by default and marked clearly.
- No-key behavior gives a concise actionable message.

#### Implement

- optional OpenAI agent adapter,
- optional OpenAI scenario proposer,
- live smoke-test command or marker,
- architecture documentation,
- experiment documentation,
- limitations,
- reproducibility instructions,
- contributor commands.

Never make a live API call during normal tests.

#### Gate

```bash
uv run pytest -q
uv run pytest --cov=evalforge --cov-report=term-missing
uv run ruff format --check .
uv run ruff check .
uv run mypy src/evalforge
uv run evalforge demo --seed 7
uv run evalforge experiment --config configs/quick.yaml
```

---

## 19. Testing Standards

### Test layers

Use all of the following:

- **Unit tests** for domain rules, tool semantics, predicates, and metrics.
- **Property tests** for transition sequences, determinism, isolation, and invariants.
- **Integration tests** for scenario validation, complete episodes, and experiments.
- **Golden tests** for canonical artifacts and reports.
- **Live tests** for provider adapters, skipped unless explicitly enabled.

### Network policy

Tests must fail if an unmarked unit or integration test attempts network access.

### Determinism

Every failing test must be reproducible with a printed seed. Store generator and episode seeds in artifacts.

### Coverage

Target at least:

- 90% line coverage for simulator, validation, execution, and verification core,
- 85% overall coverage.

Do not add meaningless assertions or exclude important code merely to reach a number.

### Regression fixtures

For every meaningful bug found during implementation:

1. add a minimal failing regression test,
2. preserve a compact trace fixture when useful,
3. fix the bug,
4. ensure the test would fail without the fix.

---

## 20. Required Demonstration

The offline demo must run without credentials and visibly prove the core idea.

It should execute a small set containing at least:

1. A normal bad-deployment rollback that the scripted agent solves.
2. A rollback that actually fails but returns a success-like observation, causing a false success claim.
3. A restart that succeeds but loses confirmation, causing an unsafe retry or unnecessary action.
4. A permission-limited case where escalation is required.
5. A distractor-service case where the wrong service may be modified.
6. A non-idempotent incident case where a repeated action creates a duplicate.

The demo output must show:

- scenario count,
- success rate,
- discovered failure signatures,
- one concise example timeline,
- paths to the Markdown and HTML reports.

Do not make the demo a hard-coded printout. It must run through the real simulator, agent harness, verifier, taxonomy, and reporter.

---

## 21. README Requirements

The README must include:

1. One-sentence pitch.
2. The problem with response-only or LLM-judge evaluation.
3. A diagram of the EvalForge loop using Mermaid or ASCII.
4. The reality-versus-observation design.
5. Quickstart commands.
6. An example scenario.
7. An example trace showing visible versus actual outcome.
8. An example verifier finding.
9. The manual vs. random vs. failure-directed experiment.
10. How to inspect a failure.
11. How to run with the optional live agent.
12. Current limitations.
13. Future RL-environment extension, explicitly labeled as future work.

Do not claim that failure-directed generation is better until an actual experiment artifact supports that claim.

---

## 22. Definition of Done

The implementation is complete only when all statements below are true.

### Functional

- The local simulator supports all required entities and tools.
- Actual outcomes are separated from visible observations.
- Permission and idempotency rules are enforced.
- Scenario specifications are versioned and serializable.
- The validator executes an oracle plan and rejects invalid scenarios.
- The manual corpus validates.
- The scripted agent runs through the real tool harness.
- Complete traces and state diffs are saved.
- Deterministic verifiers check outcomes, invariants, trace policy, and claims.
- Failure records receive canonical signatures.
- Random generation works offline and optionally with a live proposer.
- Failure-directed generation creates validated descendants with lineage.
- Equal-budget experiments run for all three sources.
- Markdown and HTML reports are generated.
- An individual failure can be inspected from the CLI.

### Quality

- All unit, property, integration, and golden tests pass.
- Ruff passes.
- mypy passes for the package.
- Coverage targets are met or any narrow exception is documented with justification.
- Default tests make no network calls.
- The quick experiment is deterministic under its seed.
- No checked-in artifact contains API keys or secrets.
- No core behavior is represented only by a mock or TODO.

### Required final commands

Run and record the output of:

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src/evalforge
uv run pytest --cov=evalforge --cov-report=term-missing
uv run evalforge validate scenarios/manual
uv run evalforge demo --seed 7
uv run evalforge experiment --config configs/quick.yaml
```

Then inspect at least one generated failure with the real CLI.

### Final implementation report

Before finishing, update `IMPLEMENTATION_STATUS.md` with:

- completed phases,
- important design decisions,
- commands executed,
- test counts,
- coverage,
- generated experiment ID,
- report paths,
- one discovered failure example,
- known limitations,
- exact live-run command if credentials are available.

Do not report completion if any required command is failing.

---

## 23. Preferred Implementation Order Within Each Phase

When several tasks are available, prioritize in this order:

1. Correct deterministic domain behavior.
2. Tests that expose realistic failure modes.
3. Artifact quality and replayability.
4. Scenario validation.
5. Experiment fairness.
6. Metrics and reporting.
7. Live model integration.
8. Cosmetic improvements.

A smaller complete system with trustworthy tests is better than a broad, partially mocked platform.

---

## 24. Final Execution Directive

Proceed through all phases without waiting for further confirmation.

The final repository must make this claim demonstrably true:

> When an agent says, “The service has been successfully rolled back,” EvalForge can determine from executable state transitions, permissions, invariants, and grounded final claims whether the rollback truly happened, whether it affected the correct service, and whether the agent behaved safely under uncertainty.
