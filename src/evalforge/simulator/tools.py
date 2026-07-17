"""Public tool metadata and schemas."""

from __future__ import annotations

from typing import cast

from evalforge.domain.world import JsonValue


def tool_schemas() -> list[dict[str, JsonValue]]:
    """Return provider-neutral JSON-schema-like public tool descriptions."""

    specs = [
        ("inspect_service", ["service_id"]),
        ("read_logs", ["service_id"]),
        ("restart_service", ["service_id"]),
        ("rollback_deployment", ["service_id"]),
        ("update_config", ["service_id", "key", "value"]),
        ("open_incident", ["service_id", "severity", "summary"]),
    ]
    return [
        {
            "name": name,
            "description": name.replace("_", " "),
            "input_schema": {
                "type": "object",
                "required": cast(JsonValue, required),
                "additionalProperties": True,
            },
        }
        for name, required in specs
    ]
