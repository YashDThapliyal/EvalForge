# EvalForge Live Model Comparison

Equal accepted budget: 12 scenarios per source.

| Provider / model | Episodes | Task success | Stress success | Unique failures | Weighted discoveries | FD children | Input tokens | Output tokens | Provider API calls | Estimated cost | Agent runtime errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| openai / `gpt-5.6-sol` | 36 | 91.7% | 91.7% | 2 | 6 | 11 | 240122 | 13828 | 199 | $0.9476 | 0 |
| openai / `gpt-5` | 36 | 63.9% | 58.3% | 5 | 16 | 9 | 460647 | 65038 | 267 | $0.8060 | 1 |
| openai / `gpt-5-mini` | 36 | 58.3% | 52.8% | 9 | 30 | 7 | 300508 | 34743 | 222 | $0.0961 | 0 |
| anthropic / `claude-opus-4-8` | 36 | 58.3% | 58.3% | 2 | 6 | 10 | 612941 | 35349 | 233 | $3.9484 | 0 |
| anthropic / `claude-sonnet-5` | 36 | 58.3% | 30.6% | 9 | 34 | 10 | 709849 | 48385 | 255 | $1.9035 | 0 |
| anthropic / `claude-haiku-4-5-20251001` | 36 | 63.9% | 50.0% | 9 | 31 | 7 | 483847 | 25977 | 231 | $0.6137 | 0 |

## Runtime-error sensitivity

Raw rates include every episode. Exclusion-adjusted rates remove provider/API infrastructure errors only; model protocol errors remain model failures.

| Provider / model | Infrastructure errors | Protocol errors | Task raw | Task excl. infra | Stress raw | Stress excl. infra |
|---|---:|---:|---:|---:|---:|---:|
| openai / `gpt-5.6-sol` | 0 | 0 | 91.7% | 91.7% | 91.7% | 91.7% |
| openai / `gpt-5` | 0 | 1 | 63.9% | 63.9% | 58.3% | 58.3% |
| openai / `gpt-5-mini` | 0 | 0 | 58.3% | 58.3% | 52.8% | 52.8% |
| anthropic / `claude-opus-4-8` | 0 | 0 | 58.3% | 58.3% | 58.3% | 58.3% |
| anthropic / `claude-sonnet-5` | 0 | 0 | 58.3% | 58.3% | 30.6% | 30.6% |
| anthropic / `claude-haiku-4-5-20251001` | 0 | 0 | 63.9% | 63.9% | 50.0% | 50.0% |

## Source-level discovery comparison

Signatures are deduplicated across models within each source. Success is full deterministic stress-test success over all model episodes.

| Source | Success | Unique signatures | Weighted discoveries |
|---|---:|---:|---:|
| Manual | 81.9% | 8 | 26 |
| Random | 58.3% | 11 | 41 |
| Failure-Directed | 30.6% | 6 | 19 |

## Method

Every model received the same public interface and matched manual and random scenarios. Failure-directed scenarios are model-specific because each adaptive arm uses only that model's earlier failures. Hidden faults, actual outcomes, oracle plans, and verifier predicates were not provided. The comparison uses equal accepted scenario budgets and deterministic verification; invalid generated scenarios do not consume the evaluation budget.

Costs are estimates from recorded provider token usage and the explicit rates saved in each resolved experiment configuration.
