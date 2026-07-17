# Implementation decisions

- 2026-07-17: Pydantic models are used at all serialized boundaries; simulator mutations work on a private deep copy.
- 2026-07-17: Artifact persistence is JSON/YAML/JSONL only, with canonical JSON used for stable hashes.
- 2026-07-17: The offline programmatic proposer is the default; provider SDK imports remain optional.

