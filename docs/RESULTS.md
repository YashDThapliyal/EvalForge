# Audited six-model results

## Run scope

- 6 live provider models
- 36 episodes per model
- 12 accepted scenarios per source and model
- 216 total episodes
- 72 episodes per source
- Seed 7
- Zero provider/API infrastructure failures
- Tracked evaluated-agent cost: **$8.3154**

## Model results

| Model | Task success | Full verified success | Unique signatures | Weighted discoveries | Tracked cost |
|---|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | 91.7% | 91.7% | 2 | 6 | $0.9476 |
| GPT-5 | 63.9% | 58.3% | 5 | 16 | $0.8060 |
| GPT-5 mini | 58.3% | 52.8% | 9 | 30 | $0.0961 |
| Claude Opus 4.8 | 58.3% | 58.3% | 2 | 6 | $3.9484 |
| Claude Sonnet 5 | 58.3% | 30.6% | 9 | 34 | $1.9035 |
| Claude Haiku 4.5 | 63.9% | 50.0% | 9 | 31 | $0.6137 |

These results are not a general model leaderboard. Sonnet 5's 27.7-point task/full gap is the clearest example in this run of task completion overstating grounded, policy-compliant reliability.

## Scenario-source results

| Source | Full verified success | Unique signatures | Severity-weighted discoveries |
|---|---:|---:|---:|
| Manual | 81.9% | 8 | 26 |
| Random | 58.3% | 11 | 41 |
| Failure-directed | 30.6% | 6 | 19 |

Random synthetic scenarios discovered the largest distinct and severity-weighted failure set. Failure-directed scenarios produced the lowest success rate, but fewer distinct discoveries. The correct exploration-versus-exploitation interpretation is:

- random generation explored more broadly in this run;
- adaptive generation repeatedly stressed previously observed weaknesses;
- adaptive generation is useful here as targeted robustness/regression testing, not evidence of superior broad failure discovery.

## GPT-5 protocol failure

GPT-5 completed its provider request but returned prose instead of calling the required `submit_final` tool. EvalForge recorded `AgentProtocolError: malformed final output: submit_final was not called`. This is a tested-model protocol failure, not provider infrastructure.

Raw GPT-5 task success was 23/36 (63.9%) and full success was 21/36 (58.3%). Because the run contained no infrastructure failures, both rates remain 63.9% and 58.3% after infrastructure exclusion. The protocol episode remains in the denominator.

## Evidence locations

The curated comparison is in [`results/model-suite/`](../results/model-suite/). Full local episode artifacts, when present, live under `artifacts/model-suite/` and are intentionally gitignored. Reports can be reconstructed from those saved artifacts without provider calls; see [reproducibility](REPRODUCIBILITY.md).
