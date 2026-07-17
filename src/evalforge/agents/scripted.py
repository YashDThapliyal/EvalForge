"""Deterministic competent-but-imperfect offline baseline agent."""

from __future__ import annotations

import re

from evalforge.agents.base import (
    AgentFinal,
    AgentRequest,
    ClaimType,
    FinalClaim,
    ToolRegistry,
)

SERVICE_PATTERN: re.Pattern[str] = re.compile(r"\b[a-z]+-(?:api|worker|analytics)\b")


class ScriptedBaselineAgent:
    """Apply general operational heuristics with realistic uncertainty weaknesses."""

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Inspect a shallowly selected service, then attempt a conventional repair."""

        service_id = self._select_service(request.task)
        inspection = tools.call("inspect_service", {"service_id": service_id})

        if "escalat" in request.task.lower():
            observation = tools.call(
                "open_incident",
                {
                    "service_id": service_id,
                    "severity": "high",
                    "summary": "Production issue requires attention",
                },
            )
            if observation.status == "uncertain":
                # Intentional weakness: blind non-idempotent retry after lost confirmation.
                tools.call(
                    "open_incident",
                    {
                        "service_id": service_id,
                        "severity": "high",
                        "summary": "Production issue requires attention",
                    },
                )
            return AgentFinal(
                status="escalated",
                summary=f"Opened an incident for {service_id}",
                claims=[
                    FinalClaim(
                        claim_type=ClaimType.INCIDENT_OPENED,
                        service_id=service_id,
                        value=True,
                    )
                ],
            )

        current_version = inspection.data.get("current_version")
        config = inspection.data.get("config")
        if isinstance(current_version, str) and current_version != "v1":
            observation = tools.call(
                "rollback_deployment", {"service_id": service_id, "target_version": "v1"}
            )
            if observation.status == "uncertain":
                # Intentional weakness: retry ambiguous mutations without an idempotency key.
                tools.call(
                    "rollback_deployment", {"service_id": service_id, "target_version": "v1"}
                )
            return AgentFinal(
                status="resolved",
                summary=f"Rolled back {service_id}",
                claims=[
                    FinalClaim(
                        claim_type=ClaimType.DEPLOYED_VERSION,
                        service_id=service_id,
                        value="v1",
                    ),
                    FinalClaim(
                        claim_type=ClaimType.SERVICE_HEALTH,
                        service_id=service_id,
                        value="healthy",
                    ),
                ],
            )
        timeout = config.get("timeout") if isinstance(config, dict) else None
        if isinstance(timeout, int) and timeout < 10:
            tools.call(
                "update_config",
                {"service_id": service_id, "key": "timeout", "value": 30},
            )
            return AgentFinal(
                status="resolved",
                summary=f"Corrected timeout for {service_id}",
                claims=[
                    FinalClaim(
                        claim_type=ClaimType.CONFIG_VALUE,
                        service_id=service_id,
                        key="timeout",
                        value=30,
                    )
                ],
            )
        observation = tools.call("restart_service", {"service_id": service_id})
        if observation.status == "uncertain":
            tools.call("restart_service", {"service_id": service_id})
        return AgentFinal(
            status="resolved",
            summary=f"Restarted {service_id}",
            claims=[
                FinalClaim(
                    claim_type=ClaimType.SERVICE_HEALTH,
                    service_id=service_id,
                    value="healthy",
                )
            ],
        )

    @staticmethod
    def _select_service(task: str) -> str:
        matches: list[str] = SERVICE_PATTERN.findall(task.lower())
        if not matches:
            return "payments-api"
        # Intentional shallow-name weakness: a payments cue wins over later exact context.
        if "payments" in task.lower() and "payments-api" in matches:
            return "payments-api"
        return matches[0]
