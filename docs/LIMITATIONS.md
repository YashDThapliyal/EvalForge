# Limitations

## Experimental limitations

- **Single domain and seed (high interpretive impact):** results cover one cloud-operations simulator, seed 7, and a 12-scenario-per-source quick budget.
- **No inferential statistics (high interpretive impact):** raw counts and rates do not establish statistical significance or general provider superiority.
- **Adaptive inputs differ by model (medium):** failure-directed children depend on each model's earlier failures, unlike shared manual and random inputs.
- **Live sampling varies (medium):** a rerun can produce different trajectories even with the same saved seed and configuration.
- **Tracked cost is incomplete (low):** evaluated-agent usage is included; the one-time shared random-proposal cost is not.

## Implementation limitations

- **Compact simulator (high scope impact):** no real AWS, GCP, Azure, Kubernetes, distributed timing, or infrastructure mutation.
- **Bounded adaptive generator (medium):** current children use distractor and diagnostic/root-cause transformations, not every mutation family contemplated in the original design.
- **OpenAI-only random proposer (medium):** Anthropic models are evaluated, but random scenario proposal currently uses OpenAI only.
- **Validation heuristics (medium):** hidden-answer leakage checks configured literal answers; they are not a complete semantic leakage detector. Near fingerprints exist but generation currently enforces exact semantic fingerprints only.
- **Execution limits (medium):** step, malformed-call, and repeat limits exist; there is no hard cross-platform wall-clock cancellation or serialized final-output byte cap.
- **Partial-side-effect abstraction (low):** it records a completed local mutation as a partial actual outcome; it does not simulate multi-resource transactional fragments.
- **Manual corpus representation (low):** 50 variants are deterministically expanded from a reviewed manifest rather than stored as 50 boilerplate-heavy YAML files.

## Packaging and governance

- Full raw live artifacts are gitignored because they are approximately 46 MB and contain provider transcripts. The repository commits only the compact aggregate report.
- Some OpenAI raw messages contain `sk-`-prefixed encrypted continuation content. These opaque provider fields are not API keys, but they are another reason to redact and review raw artifacts before sharing.
- Token prices are configuration inputs and can become stale; update them before new cost comparisons.
- The repository does not currently contain a license file. It is ready for private technical review, but the owner should choose a license before public redistribution or external contribution.
- RL training, fine-tuning, DPO, policy optimization, a production database, and an LLM correctness judge are not implemented.
