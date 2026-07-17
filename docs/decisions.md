# Implementation decisions

- 2026-07-17: Pydantic models are used at all serialized boundaries; simulator mutations work on a private deep copy.
- 2026-07-17: Artifact persistence is JSON/YAML/JSONL only, with canonical JSON used for stable hashes.
- 2026-07-17: The offline programmatic proposer is the default; provider SDK imports remain optional.
- 2026-07-17: Manual variants use one reviewed manifest and deterministic family expansion so 50 complete specs remain reviewable without copying world-state boilerplate.
- 2026-07-17: Failure signatures encode behavioral context but exclude service and random IDs, keeping superficial variants stable.
- 2026-07-17: Failure-directed generation uses bounded data-only mutations and only prior failures from its own adaptive source run.
- 2026-07-17: Static reports are regenerated exclusively from artifacts and use Jinja auto-escaping for all episode content.
- 2026-07-17: Live provider clients are injected through minimal protocols in tests; default pytest runs explicitly exclude live tests and block socket connections.
