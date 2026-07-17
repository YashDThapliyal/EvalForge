# Implementation decisions

- 2026-07-17: Pydantic models are used at all serialized boundaries; simulator mutations work on a private deep copy.
- 2026-07-17: Artifact persistence is JSON/YAML/JSONL only, with canonical JSON used for stable hashes.
- 2026-07-17: The offline programmatic proposer is the default; provider SDK imports remain optional.
- 2026-07-17: Manual variants use one reviewed manifest and deterministic family expansion so 50 complete specs remain reviewable without copying world-state boilerplate.
- 2026-07-17: Failure signatures encode behavioral context but exclude service and random IDs, keeping superficial variants stable.
- 2026-07-17: Failure-directed generation uses bounded data-only mutations and only prior failures from its own adaptive source run.
- 2026-07-17: Static reports are regenerated exclusively from artifacts and use Jinja auto-escaping for all episode content.
- 2026-07-17: Live provider clients are injected through minimal protocols in tests; default pytest runs explicitly exclude live tests and block socket connections.
- 2026-07-17: Live agents terminate through a strict provider-side `submit_final` tool. OpenAI preserves native `response.output` continuations (including reasoning items); Anthropic preserves assistant tool-use blocks followed immediately by user tool-result blocks.
- 2026-07-17: Live experiments have no scripted fallback. Provider/model identity, raw messages, tokens, provider turns, and explicit-price cost estimates are persisted per episode.
- 2026-07-17: Quick manual selection is round-robin by reviewed family. Configuration scenarios expose the required numeric value through ordinary logs rather than hidden oracle state.
- 2026-07-17: Interrupted runs reuse exact completed model outcomes, including policy failures, and retry only provider/API runtime errors to prevent selective resampling.
- 2026-07-17: Canonical signatures derive their semantic claim dimension from the failed outcome predicate instead of final-claim ordering.
