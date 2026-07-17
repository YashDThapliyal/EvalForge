"""Budget-matched experiment metric aggregation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from evalforge.domain.scenario import ScenarioSpec
from evalforge.execution.episode import EpisodeResult
from evalforge.verification.taxonomy import FailureCode

SEVERITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


class SourceMetrics(BaseModel):
    """All required measurements for one equal-budget source."""

    source: str
    attempted_scenarios: int
    accepted_valid_scenarios: int
    rejected_scenarios: int
    duplicate_scenarios: int
    validation_rate: float
    duplicate_rate: float
    evaluated: int
    task_success_rate: float
    stress_test_success_rate: float
    total_failure_episodes: int
    unique_failure_signatures: int
    high_critical_failure_signatures: int
    severity_weighted_discoveries: int
    failures_per_10_tests: float
    discovery_curve: list[int]
    scenario_family_coverage: int
    fault_family_coverage: int
    average_tool_calls: float
    unsafe_retry_rate: float
    false_success_claim_rate: float
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    provider_api_calls: int = 0
    estimated_cost_usd: float = 0.0
    severity_breakdown: dict[str, int] = Field(default_factory=dict)


class ExperimentMetrics(BaseModel):
    """Three-source comparison metrics."""

    sources: dict[str, SourceMetrics]


def compute_source_metrics(
    source: str,
    scenarios: list[ScenarioSpec],
    episodes: list[EpisodeResult],
    attempted: int,
    rejected: int,
    duplicates: int,
) -> SourceMetrics:
    """Compute raw counts and rates without significance claims."""

    evaluated = len(episodes)
    failures = [episode.failure for episode in episodes if episode.failure is not None]
    signature_severity: dict[str, str] = {}
    severity_breakdown: dict[str, int] = {}
    discovery_curve: list[int] = []
    discovered: set[str] = set()
    for episode in episodes:
        if episode.failure is not None:
            failure = episode.failure
            discovered.add(failure.canonical_signature)
            severity_breakdown[failure.severity] = severity_breakdown.get(failure.severity, 0) + 1
            previous = signature_severity.get(failure.canonical_signature)
            if previous is None or SEVERITY_WEIGHTS[failure.severity] > SEVERITY_WEIGHTS[previous]:
                signature_severity[failure.canonical_signature] = failure.severity
        discovery_curve.append(len(discovered))
    task_successes = sum(
        episode.verification is not None and episode.verification.task_success
        for episode in episodes
    )
    stress_successes = sum(
        episode.verification is not None and episode.verification.success for episode in episodes
    )
    unsafe = sum(
        FailureCode.UNSAFE_NON_IDEMPOTENT_RETRY in failure.all_codes for failure in failures
    )
    false_success = sum(
        FailureCode.CLAIMED_SUCCESS_AFTER_FAILED_ACTION in failure.all_codes for failure in failures
    )
    accepted = len(scenarios)
    valid_denominator = attempted - duplicates
    usage = [episode.provider_usage for episode in episodes if episode.provider_usage is not None]
    return SourceMetrics(
        source=source,
        attempted_scenarios=attempted,
        accepted_valid_scenarios=accepted,
        rejected_scenarios=rejected,
        duplicate_scenarios=duplicates,
        validation_rate=accepted / valid_denominator if valid_denominator else 0.0,
        duplicate_rate=duplicates / attempted if attempted else 0.0,
        evaluated=evaluated,
        task_success_rate=task_successes / evaluated if evaluated else 0.0,
        stress_test_success_rate=stress_successes / evaluated if evaluated else 0.0,
        total_failure_episodes=len(failures),
        unique_failure_signatures=len(signature_severity),
        high_critical_failure_signatures=sum(
            severity in {"high", "critical"} for severity in signature_severity.values()
        ),
        severity_weighted_discoveries=sum(
            SEVERITY_WEIGHTS[severity] for severity in signature_severity.values()
        ),
        failures_per_10_tests=(len(failures) * 10 / evaluated if evaluated else 0.0),
        discovery_curve=discovery_curve,
        scenario_family_coverage=len(
            {str(scenario.metadata.get("family")) for scenario in scenarios}
        ),
        fault_family_coverage=len(
            {fault.kind.value for scenario in scenarios for fault in scenario.fault_plan}
        ),
        average_tool_calls=(
            sum(len(episode.events) for episode in episodes) / evaluated if evaluated else 0.0
        ),
        unsafe_retry_rate=unsafe / evaluated if evaluated else 0.0,
        false_success_claim_rate=false_success / evaluated if evaluated else 0.0,
        input_tokens=sum(item.input_tokens for item in usage),
        cached_input_tokens=sum(item.cached_input_tokens for item in usage),
        cache_write_input_tokens=sum(item.cache_write_input_tokens for item in usage),
        output_tokens=sum(item.output_tokens for item in usage),
        provider_api_calls=sum(item.api_calls for item in usage),
        estimated_cost_usd=sum(item.estimated_cost_usd for item in usage),
        severity_breakdown=dict(sorted(severity_breakdown.items())),
    )
