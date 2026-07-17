# Architecture

EvalForge uses a dependency-directed Python architecture: serialized domain models sit at the center; the simulator implements deterministic state transitions; scenarios build and validate executable inputs; live agents access only public requests and visible observations; execution records isolated episodes; verification independently checks state, safety, trace policy, claims, and runtime validity; reporting reads immutable artifacts. Production orchestration accepts only explicitly configured OpenAI or Anthropic tested agents and an explicit OpenAI proposal model; oracle/replay implementations are validation and debugging utilities, not selectable evaluation modes.

The simulator deep-copies every initial world. Permission checks occur before all transitions. Each `ToolEvent` retains arguments, the permission decision, actual outcome, visible observation, before/after hashes, a canonical state diff, side-effect identity, and applied fault IDs. Only `ToolObservation` crosses the agent boundary.

Scenario validation checks references, fault reachability, nontriviality, hidden-answer leakage, oracle legality, final predicates, invariants, step feasibility, fingerprints, and deterministic replay. Exact hashes exclude prose and creation metadata; structural hashes normalize behavioral shape.

Expected domain failures are structured data. Files are persisted atomically as YAML, JSON, and JSONL. No database, cloud account, arbitrary generated code, or semantic LLM correctness judge is used.
