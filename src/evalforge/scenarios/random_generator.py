"""Validation and deduplication for failure-feedback-free scenario proposals."""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from pydantic import BaseModel, Field

from evalforge.domain.scenario import ScenarioSpec
from evalforge.scenarios.fingerprint import fingerprint
from evalforge.scenarios.validator import ScenarioValidator


class ScenarioProposer(Protocol):
    """Schema-only scenario proposal boundary."""

    def propose(self, attempt: int, seed: int) -> ScenarioSpec:
        """Return a complete data-only ScenarioSpec proposal."""


class GenerationStats(BaseModel):
    """Generation attempts and common-validator rejection accounting."""

    attempted: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)

    @property
    def validation_rate(self) -> float:
        """Accepted proposals divided by nonduplicate attempts."""

        denominator = self.attempted - self.duplicates
        return self.accepted / denominator if denominator else 0.0


class GenerationResult(BaseModel):
    """Accepted scenarios plus transparent generation accounting."""

    accepted: list[ScenarioSpec]
    stats: GenerationStats


class RandomScenarioGenerator:
    """Validate and deduplicate failure-blind scenario proposals."""

    def __init__(self, proposer: ScenarioProposer):
        self.proposer = proposer

    def generate(
        self,
        count: int,
        seed: int,
        existing_fingerprints: set[str] | None = None,
        max_attempts: int | None = None,
    ) -> GenerationResult:
        """Generate exactly `count` accepted valid scenarios when feasible."""

        if max_attempts is not None and max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        known = set(existing_fingerprints or set())
        accepted: list[ScenarioSpec] = []
        reasons: Counter[str] = Counter()
        attempted = rejected = duplicates = 0
        attempt_limit = max(count * 30, 30) if max_attempts is None else max_attempts
        while len(accepted) < count and attempted < attempt_limit:
            proposal = self.proposer.propose(attempted, seed)
            attempted += 1
            proposal_fingerprint = fingerprint(proposal)
            if proposal_fingerprint in known:
                duplicates += 1
                continue
            validation = ScenarioValidator().validate(proposal)
            if not validation.valid:
                rejected += 1
                reasons.update(validation.codes)
                continue
            known.add(proposal_fingerprint)
            accepted.append(proposal)
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
