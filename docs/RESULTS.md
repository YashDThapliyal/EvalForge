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
| Claude Sonnet 5 | 58.3% | 44.4% | 4 | 14 | $1.9035 |
| Claude Haiku 4.5 | 63.9% | 50.0% | 9 | 31 | $0.6137 |

These results are not a general model leaderboard. Sonnet 5 and Haiku 4.5 show the widest task/full gaps in this run, both 13.9 points, and are the clearest examples of task completion overstating grounded, policy-compliant reliability.

## Scenario-source results

| Source | Full verified success | Unique signatures | Severity-weighted discoveries |
|---|---:|---:|---:|
| Manual | 83.3% | 7 | 22 |
| Random | 63.9% | 7 | 25 |
| Failure-directed | 30.6% | 6 | 19 |

Failure-directed scenarios produced by far the lowest success rate, so they were the hardest. On discovery breadth, random and failure-directed generation are effectively tied: 7 versus 6 unique signatures and 25 versus 19 weighted. With one seed, one domain, one budget, and no confidence intervals, a one-signature difference is not a result. The defensible reading is:

- adaptive generation reliably produced harder scenarios;
- neither source demonstrated superior broad failure discovery at this sample size;
- adaptive generation is best characterised here as targeted robustness/regression testing, and the broad-discovery comparison is underpowered rather than settled.

## Correction (2026-07-20)

An earlier published version of this table reported Sonnet 5 at **30.6%** full verified success with 9 signatures and 34 weighted discoveries, and reported random generation as the clear discovery winner (58.3%, 11 signatures, 41 weighted). Both were measurement artifacts of a verifier defect, now fixed.

`verification/claims.py` graded the `unresolved_uncertainty` claim as a factual assertion, resolving it to `any(observation.status == "uncertain")`. That claim actually asserts the agent's own residual confidence, which the simulator does not model, so it has no world-state ground truth. Models that volunteered honest epistemic caution in runs where no uncertain observation happened to fire were scored with a **critical** "final claim contradicts actual state" finding.

The agent-facing schema never communicated the narrow reading; it said only to use the claim "when that condition actually occurred." Sonnet 5 submitted 10 of the 19 uncertainty claims in the entire 216-episode suite and absorbed 9 of the 9 spurious criticals — so the defect was effectively a single-model penalty. Because 8 of those 9 landed in the random arm and none in the failure-directed arm, it also inflated random's apparent discovery advantage.

The claim type is now excluded from factual grading. The separate rule that penalises **omitting** uncertainty after an un-followed-up uncertain observation is retained and covered by regression tests, so hiding observed uncertainty is still a failure.

No other model's figures changed. Scenario sets, traces, costs, and token counts are untouched: the same executed episodes were re-scored offline via `scripts/rescore_from_artifacts.py`, deliberately not by re-running the experiment, since corrected pass/fail signal would otherwise alter failure-directed lineage and produce a different experiment rather than a correction of this one.

## GPT-5 protocol failure

GPT-5 completed its provider request but returned prose instead of calling the required `submit_final` tool. EvalForge recorded `AgentProtocolError: malformed final output: submit_final was not called`. This is a tested-model protocol failure, not provider infrastructure.

Raw GPT-5 task success was 23/36 (63.9%) and full success was 21/36 (58.3%). Because the run contained no infrastructure failures, both rates remain 63.9% and 58.3% after infrastructure exclusion. The protocol episode remains in the denominator.

## Evidence locations

The curated comparison is in [`results/model-suite/`](../results/model-suite/). Full local episode artifacts, when present, live under `artifacts/model-suite/` and are intentionally gitignored. Reports can be reconstructed from those saved artifacts without provider calls; see [reproducibility](REPRODUCIBILITY.md).
