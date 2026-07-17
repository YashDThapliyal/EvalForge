"""Public tool metadata and schemas."""

from __future__ import annotations

from evalforge.domain.world import JsonValue


def tool_schemas() -> list[dict[str, JsonValue]]:
    """Return provider-neutral JSON-schema-like public tool descriptions."""

    service_id: dict[str, JsonValue] = {
        "type": "string",
        "description": "Exact service identifier from the environment.",
    }
    idempotency_key: dict[str, JsonValue] = {
        "type": ["string", "null"],
        "description": "Stable retry key, or null when intentionally making an unkeyed call.",
    }
    return [
        {
            "name": "inspect_service",
            "description": "Read current service health, deployed version, and configuration.",
            "input_schema": {
                "type": "object",
                "properties": {"service_id": service_id},
                "required": ["service_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "read_logs",
            "description": "Read the most recent local logs for one service.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": service_id,
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["service_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "restart_service",
            "description": "Restart a service; use an idempotency key when retrying.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": service_id,
                    "idempotency_key": idempotency_key,
                },
                "required": ["service_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "rollback_deployment",
            "description": "Roll back a service to a target or its known-good version.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": service_id,
                    "target_version": {"type": ["string", "null"]},
                    "idempotency_key": idempotency_key,
                },
                "required": ["service_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "update_config",
            "description": "Set one configuration key, with optional retry idempotency.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": service_id,
                    "key": {"type": "string"},
                    "value": {
                        "anyOf": [
                            {"type": "null"},
                            {"type": "boolean"},
                            {"type": "integer"},
                            {"type": "number"},
                            {"type": "string"},
                        ]
                    },
                    "idempotency_key": idempotency_key,
                },
                "required": ["service_id", "key", "value"],
                "additionalProperties": False,
            },
        },
        {
            "name": "open_incident",
            "description": "Open an incident; unkeyed retries create duplicate incidents.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": service_id,
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "summary": {"type": "string", "minLength": 1},
                    "idempotency_key": idempotency_key,
                },
                "required": ["service_id", "severity", "summary"],
                "additionalProperties": False,
            },
        },
    ]
