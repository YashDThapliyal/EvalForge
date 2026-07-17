# Six-model evaluation suite

The checked-in quick suite evaluates six real API models with 12 accepted scenarios per source
and 36 episodes per model:

| Provider | Model ID | Input / cached / output per MTok |
|---|---|---:|
| OpenAI | `gpt-5.6-sol` | $5 / $0.50 / $30 |
| OpenAI | `gpt-5` | $1.25 / $0.125 / $10 |
| OpenAI | `gpt-5-mini` | $0.25 / $0.025 / $2 |
| Anthropic | `claude-opus-4-8` | $5 / $0.50 / $25 |
| Anthropic | `claude-sonnet-5` | $2 / $0.20 / $10 |
| Anthropic | `claude-haiku-4-5-20251001` | $1 / $0.10 / $5 |

Anthropic's Sonnet 5 rates above are introductory prices valid through 2026-08-31. Before a run
on or after 2026-09-01, update its config to $3 input, $0.30 cache read, $3.75 five-minute cache
write, and $15 output per MTok.

The suite generates one 12-scenario random corpus using the real OpenAI proposer, validates it,
and reuses those exact random scenarios for every model. Manual scenarios are also identical.
Failure-directed scenarios remain model-specific because they are generated only from failures
observed earlier in that model's own adaptive run.

## Run everything

From the repository root:

```bash
uv sync --extra live
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
bash scripts/run_model_suite.sh
```

The script runs two provider lanes concurrently: OpenAI models run sequentially within one lane,
while Anthropic models run sequentially within the other. This overlaps independent provider API
latency without launching three simultaneous requests against either provider's rate limit.
Completed episodes are reused by EvalForge if the same experiment is restarted. The shared random
corpus is generated only when it does not already exist. Lane output is saved in
`artifacts/model-suite/logs/openai.log` and `artifacts/model-suite/logs/anthropic.log`. At
completion, the combined reports are written to:

```text
artifacts/model-suite/comparison/report.md
artifacts/model-suite/comparison/report.html
```

## Run models individually

Generate the common random corpus once before the first individual model run:

```bash
uv run evalforge generate \
  --method random --count 12 --seed 7 \
  --output artifacts/model-suite/shared-random \
  --proposer openai --proposer-model gpt-5.6-sol
```

Then run any or all of these commands:

```bash
uv run evalforge experiment --config configs/model_suite/openai_gpt_5_6_sol.yaml
uv run evalforge experiment --config configs/model_suite/openai_gpt_5.yaml
uv run evalforge experiment --config configs/model_suite/openai_gpt_5_mini.yaml
uv run evalforge experiment --config configs/model_suite/anthropic_opus_4_8.yaml
uv run evalforge experiment --config configs/model_suite/anthropic_sonnet_5.yaml
uv run evalforge experiment --config configs/model_suite/anthropic_haiku_4_5.yaml
```

The report's estimated model cost covers evaluated-agent token usage. OpenAI calls used to create
the shared scenario corpus are recorded in generation statistics but are not currently included
in the episode-token cost totals.

Pricing sources: OpenAI's model pages for
[`gpt-5`](https://developers.openai.com/api/docs/models/gpt-5) and
[`gpt-5-mini`](https://developers.openai.com/api/docs/models/gpt-5-mini), and Anthropic's
[`models`](https://platform.claude.com/docs/en/about-claude/models/overview) and
[`pricing`](https://platform.claude.com/docs/en/about-claude/pricing) documentation.
