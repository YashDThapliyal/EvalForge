from __future__ import annotations

import inspect

from evalforge.domain.scenario import SourceMethod
from evalforge.scenarios.fingerprint import fingerprint
from evalforge.scenarios.manual import build_manual_scenario
from evalforge.scenarios.random_generator import (
    ProgrammaticProposer,
    RandomScenarioGenerator,
)
from evalforge.scenarios.validator import ScenarioValidator


def test_random_generation_is_offline_valid_deterministic_and_feedback_free() -> None:
    assert "failure" not in inspect.signature(RandomScenarioGenerator.generate).parameters
    first = RandomScenarioGenerator(ProgrammaticProposer()).generate(count=12, seed=7)
    second = RandomScenarioGenerator(ProgrammaticProposer()).generate(count=12, seed=7)
    assert [fingerprint(item) for item in first.accepted] == [
        fingerprint(item) for item in second.accepted
    ]
    assert first.stats.accepted == 12
    assert all(ScenarioValidator().validate(item).valid for item in first.accepted)
    assert all(item.source_method == "random" for item in first.accepted)


class SometimesInvalidProposer:
    def propose(self, attempt: int, seed: int):  # type: ignore[no-untyped-def]
        scenario = build_manual_scenario("bad_deployment", attempt % 5)
        scenario.source_method = SourceMethod.RANDOM
        scenario.scenario_id = f"proposal-{seed}-{attempt}"
        if attempt == 0:
            scenario.oracle_plan[0].arguments["service_id"] = "missing"
        return scenario


def test_invalid_and_duplicate_proposals_do_not_consume_budget() -> None:
    result = RandomScenarioGenerator(SometimesInvalidProposer()).generate(count=3, seed=11)
    assert result.stats.accepted == 3
    assert result.stats.attempted >= 4
    assert result.stats.rejected >= 1
    assert "REFERENTIAL_INTEGRITY" in result.stats.rejection_reasons

    duplicate = ProgrammaticProposer().propose(0, 7)
    result = RandomScenarioGenerator(ProgrammaticProposer()).generate(
        count=2, seed=7, existing_fingerprints={fingerprint(duplicate)}
    )
    assert result.stats.accepted == 2
    assert result.stats.duplicates >= 1
