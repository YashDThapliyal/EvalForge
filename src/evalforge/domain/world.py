"""Deterministic local cloud-operations world."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]


class Permission(StrEnum):
    """Fine-grained simulator permissions."""

    READ_SERVICE = "read_service"
    READ_LOGS = "read_logs"
    RESTART_SERVICE = "restart_service"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    UPDATE_CONFIG = "update_config"
    OPEN_INCIDENT = "open_incident"


class Service(BaseModel):
    """A simulated deployable service."""

    model_config = ConfigDict(extra="forbid")

    service_id: str
    current_version: str
    known_good_version: str
    health: str
    config: dict[str, JsonValue] = Field(default_factory=dict)
    owner_team: str
    region: str = "us-west-2"
    dependencies: list[str] = Field(default_factory=list)
    last_deployment_id: str | None = None


class Deployment(BaseModel):
    """Deployment history entry."""

    model_config = ConfigDict(extra="forbid")

    deployment_id: str
    service_id: str
    from_version: str
    to_version: str
    status: str
    created_at_step: int
    rollback_target: str | None = None


class Incident(BaseModel):
    """Operational incident opened by an actor."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str
    service_id: str
    severity: str
    status: str = "open"
    summary: str
    opened_by: str
    linked_action_ids: list[str] = Field(default_factory=list)


class MonitoringObservation(BaseModel):
    """A reading from a named monitoring source."""

    source: str
    service_id: str
    health: str
    observed_at_step: int = 0


class WorldState(BaseModel):
    """Complete copyable state of the local environment."""

    model_config = ConfigDict(extra="forbid")

    services: dict[str, Service]
    deployments: dict[str, Deployment] = Field(default_factory=dict)
    logs: dict[str, list[str]] = Field(default_factory=dict)
    permissions: dict[str, list[Permission]] = Field(default_factory=dict)
    incidents: dict[str, Incident] = Field(default_factory=dict)
    monitoring: list[MonitoringObservation] = Field(default_factory=list)
    action_history: list[str] = Field(default_factory=list)
    side_effects: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)
    idempotency_records: dict[str, str] = Field(default_factory=dict)


def default_world() -> WorldState:
    """Build the canonical small cloud environment used by tests and generators."""

    service_data = {
        "payments-api": ("payments", ["identity-api"]),
        "checkout-api": ("checkout", ["payments-api", "identity-api"]),
        "identity-api": ("identity", []),
        "notifications-worker": ("messaging", ["identity-api"]),
        "payments-analytics": ("analytics", ["payments-api"]),
    }
    services: dict[str, Service] = {}
    deployments: dict[str, Deployment] = {}
    for service_id, (team, dependencies) in service_data.items():
        deployment_id = f"dep-{service_id}-v1"
        services[service_id] = Service(
            service_id=service_id,
            current_version="v1",
            known_good_version="v1",
            health="healthy",
            config={"timeout": 30, "retries": 3},
            owner_team=team,
            dependencies=dependencies,
            last_deployment_id=deployment_id,
        )
        deployments[deployment_id] = Deployment(
            deployment_id=deployment_id,
            service_id=service_id,
            from_version="v0",
            to_version="v1",
            status="succeeded",
            created_at_step=0,
            rollback_target="v0",
        )
    all_permissions = list(Permission)
    return WorldState(
        services=services,
        deployments=deployments,
        logs={service_id: [f"{service_id}: service started"] for service_id in services},
        permissions={"operator": all_permissions, "viewer": [Permission.READ_SERVICE]},
        monitoring=[
            MonitoringObservation(source="primary", service_id=service_id, health="healthy")
            for service_id in services
        ],
    )
