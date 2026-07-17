"""Validated bounded mutation of scenarios toward observed failure signatures."""

from __future__ import annotations

from collections import Counter
from typing import cast

from evalforge.domain.scenario import ScenarioSpec, SourceMethod
from evalforge.domain.world import JsonValue
from evalforge.scenarios.fingerprint import fingerprint
from evalforge.scenarios.mutators import apply_safe_mutation
from evalforge.scenarios.random_generator import GenerationResult, GenerationStats
from evalforge.scenarios.validator import ScenarioValidator
from evalforge.verification.taxonomy import FailureRecord


class FailureDirectedScenarioGenerator:
    """Create oracle-solvable descendants with explicit failure lineage."""

    def generate(
        self,
        parent: ScenarioSpec,
        failure: FailureRecord,
        count: int,
        seed: int,
        existing_fingerprints: set[str] | None = None,
    ) -> GenerationResult:
        """Generate accepted children targeting one observed canonical signature."""

        known = set(existing_fingerprints or set())
        known.add(fingerprint(parent))
        accepted: list[ScenarioSpec] = []
        reasons: Counter[str] = Counter()
        attempted = rejected = duplicates = 0
        max_attempts = max(count * 30, 30)
        while len(accepted) < count and attempted < max_attempts:
            child = parent.model_copy(deep=True)
            child.scenario_id = f"fd_{seed}_{attempted:04d}"
            child.title = f"Failure-directed child {attempted}"
            child.seed = seed * 10_000 + attempted
            child.source_method = SourceMethod.FAILURE_DIRECTED
            child.parent_scenario_id = parent.scenario_id
            child.parent_failure_signature = failure.canonical_signature
            mutations = apply_safe_mutation(child, attempted)
            child.tags = sorted(set([*child.tags, "failure_directed_child"]))
            child.metadata = {
                "target_failure_signature": failure.canonical_signature,
                "mutations": cast(JsonValue, mutations),
                "mutation_count": len(mutations),
                "generator_seed": seed,
            }
            attempted += 1
            child_fingerprint = fingerprint(child)
            if child_fingerprint in known:
                duplicates += 1
                continue
            validation = ScenarioValidator().validate(child)
            if not validation.valid:
                rejected += 1
                reasons.update(validation.codes)
                continue
            known.add(child_fingerprint)
            accepted.append(child)
        return GenerationResult(
            accepted=accepted,
            stats=GenerationStats(
                attempted=attempted,
                accepted=len(accepted),
                rejected=rejected,
                duplicates=duplicates,
                rejection_reasons=dict(sorted(reasons.items())),
            ),
        )
