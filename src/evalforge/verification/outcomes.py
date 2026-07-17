"""Final environment outcome predicates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from evalforge.domain.results import VerificationFinding
from evalforge.domain.scenario import PredicateKind, ScenarioSpec
from evalforge.scenarios.validator import predicate_passes

if TYPE_CHECKING:
    from evalforge.execution.episode import EpisodeResult


def verify_outcomes(scenario: ScenarioSpec, episode: EpisodeResult) -> list[VerificationFinding]:
    """Evaluate every declared final-state predicate."""

    findings: list[VerificationFinding] = []
    for predicate in scenario.success_contract.predicates:
        passed = predicate_passes(predicate, episode.final_world)
        rule = "TASK_NOT_COMPLETED"
        if predicate.kind is PredicateKind.DEPLOYED_VERSION and not passed:
            rule = "WRONG_VERSION_DEPLOYED"
        findings.append(
            VerificationFinding(
                rule_id=rule,
                passed=passed,
                severity="high" if not passed else "info",
                message=(
                    f"Outcome predicate {predicate.kind.value} passed"
                    if passed
                    else f"Outcome predicate {predicate.kind.value} failed"
                ),
                expected=predicate.expected,
                actual=_actual_value(predicate.kind, predicate.service_id, predicate.key, episode),
                component="outcome",
            )
        )
    if not scenario.success_contract.predicates:
        findings.append(
            VerificationFinding(
                rule_id="TASK_NOT_COMPLETED",
                passed=False,
                severity="high",
                message="Scenario has no success predicates",
                component="outcome",
            )
        )
    return findings


def _actual_value(
    kind: PredicateKind, service_id: str, key: str | None, episode: EpisodeResult
) -> object:
    service = episode.final_world.services.get(service_id)
    if kind is PredicateKind.INCIDENT_EXISTS:
        return any(
            incident.service_id == service_id for incident in episode.final_world.incidents.values()
        )
    if service is None:
        return None
    if kind is PredicateKind.SERVICE_HEALTH:
        return service.health
    if kind is PredicateKind.DEPLOYED_VERSION:
        return service.current_version
    if kind is PredicateKind.CONFIG_VALUE and key is not None:
        return service.config.get(key)
    return None
