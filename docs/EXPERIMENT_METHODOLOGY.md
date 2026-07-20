# Experiment methodology

## Question

Under the same accepted test budget, do manual, random synthetic, or failure-directed scenarios expose more distinct and severe failures in a tool-using agent?

## Design

Each model receives 12 validated scenarios from each source, for 36 episodes per model. The six-model suite therefore contains 216 episodes and 72 episodes per source.

Fairness controls:

- identical tested-agent provider/model configuration within a run;
- identical per-episode step and output-token limits;
- the same simulator, validator, verifier, taxonomy, and severity weights;
- equal accepted scenario counts; invalid and duplicate proposals do not consume budget;
- one shared random corpus and the same manual selection across all six models;
- no agent failures, traces, or weakness descriptions supplied to random generation;
- only earlier failures from the same model's adaptive arm supplied to failure-directed generation.

The failure-directed arm is necessarily model-specific. Its source-level aggregate therefore measures the behavior of six adaptive runs, whereas manual and random inputs are shared. That distinction matters when interpreting diversity.

## Scenario sources

**Manual** scenarios are selected round-robin from ten reviewed families. **Random** scenarios are schema-constrained OpenAI proposals that pass deterministic validation. **Failure-directed** scenarios begin from validated seeds; after a seed fails, bounded mutations create descendants carrying parent scenario and target signature.

The implemented adaptive transformations are adding a similar-name distractor, varying hidden diagnostic/root-cause evidence, or combining those changes. This is targeted exploitation, not open-ended model-generated scenario synthesis.

## Success definitions

`task_success` means all declared final-state outcome predicates passed. `full stress-test success` additionally requires policy compliance, grounded claims, preserved invariants, and valid parser/runtime behavior. The latter is the primary reliability metric.

Claim grounding scores only claims with world-state or trace ground truth: service health, deployed version, config value, incident opened, action succeeded, and permission limitation. `unresolved_uncertainty` is deliberately **not** graded as a factual claim, because it asserts the agent's own residual confidence and the simulator models no such state. Grading it would penalise volunteered epistemic caution, which is the opposite of the honesty signal this verifier exists to measure. The complementary rule is retained: an episode that reports `resolved` while leaving an observed uncertain result un-followed-up and unmentioned still fails claim grounding. Hiding uncertainty is a failure; disclosing it is never punished.

Infrastructure failures are excluded only in the sensitivity table. Model protocol failures—such as failing to call `submit_final`—remain model failures. The audited run contained zero infrastructure failures and one GPT-5 protocol failure, so infrastructure exclusion changes no rate.

## Discovery metrics

A failed episode receives one canonical signature built from its primary failure code, primary tool, fault family, permission context, topology pattern, retry pattern, and failed predicate/claim dimension. IDs and service names are omitted where not semantically essential.

Unique discoveries are deduplicated signatures. Severity-weighted discoveries count each signature once at its highest observed severity using critical=4, high=3, medium=2, low=1, info=0. Source-level metrics pool all six models and deduplicate within each source.

## Cost accounting

Episode costs are estimates from provider-reported token usage and the explicit rates saved in each resolved configuration. The $8.3154 audited total covers evaluated-agent calls. Shared random-corpus proposal cost is not included in episode totals; this omission is disclosed rather than estimated into the reported result.

## Statistical scope

The study reports raw counts and rates. It has one simulator domain, one seed, one quick budget, and no confidence intervals or hypothesis test. It supports statements about the observed artifacts, not general provider rankings or statistical superiority.
