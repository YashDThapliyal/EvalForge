# Implementation decisions

- 2026-07-17: Pydantic models are used at all serialized boundaries; simulator mutations work on a private deep copy.
- 2026-07-17: Artifact persistence is JSON/YAML/JSONL only, with canonical JSON used for stable hashes.
- 2026-07-17: Production experiment configs require an explicit live provider, tested model, OpenAI proposal model, and token prices. There is no programmatic proposer or scripted-agent fallback.
- 2026-07-17: Manual variants use one reviewed manifest and deterministic family expansion so 50 complete specs remain reviewable without copying world-state boilerplate.
- 2026-07-17: Failure signatures encode behavioral context but exclude service and random IDs, keeping superficial variants stable.
- 2026-07-17: Failure-directed generation uses bounded data-only mutations and only prior failures from its own adaptive source run.
- 2026-07-17: Static reports are regenerated exclusively from artifacts and use Jinja auto-escaping for all episode content.
- 2026-07-17: Live provider clients are injected through minimal protocols in tests; default pytest runs explicitly exclude live tests and block socket connections.
- 2026-07-17: Live agents terminate through a strict provider-side `submit_final` tool. OpenAI preserves native `response.output` continuations (including reasoning items); Anthropic preserves assistant tool-use blocks followed immediately by user tool-result blocks.
- 2026-07-17: Provider/model identity, raw messages, tokens, provider turns, and explicit-price cost estimates are persisted per episode. Provider failures remain structured failures and are never substituted.
- 2026-07-17: Deterministic doubles used by the offline test suite live only under `tests/` and enter orchestration through explicit dependency injection.
- 2026-07-17: Cross-model runs generate one live-proposed, validated random corpus and reuse it for every model. Manual and random inputs are therefore matched; failure-directed inputs remain model-adaptive.
- 2026-07-17: Quick manual selection is round-robin by reviewed family. Configuration scenarios expose the required numeric value through ordinary logs rather than hidden oracle state.
- 2026-07-17: Interrupted runs reuse exact completed model outcomes, including policy failures, and retry only provider/API runtime errors to prevent selective resampling.
- 2026-07-17: Canonical signatures derive their semantic claim dimension from the failed outcome predicate instead of final-claim ordering.
- 2026-07-17: Model protocol failures are completed model outcomes and are preserved on resume; only provider/API infrastructure failures are eligible for retry.
- 2026-07-17: Public comparison artifacts use repository-relative paths and a compact aggregate snapshot is committed under `results/model-suite/`; full provider transcripts remain ignored.
- 2026-07-17: Failure-directed capability descriptions enumerate only executable bounded transformations. Additional contemplated operators remain future work.
