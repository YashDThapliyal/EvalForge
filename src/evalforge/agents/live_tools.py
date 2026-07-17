"""Strict provider tool schema conversion shared by live adapters."""

from __future__ import annotations

from copy import deepcopy
from typing import cast

from evalforge.agents.base import ClaimType
from evalforge.domain.world import JsonValue


def provider_tool(tool: dict[str, JsonValue], *, strict: bool) -> dict[str, object]:
    """Convert one public tool into a provider-neutral strict custom tool."""

    name = tool.get("name")
    description = tool.get("description")
    parameters = tool.get("input_schema")
    if (
        not isinstance(name, str)
        or not isinstance(description, str)
        or not isinstance(parameters, dict)
    ):
        raise ValueError("public tool schema is malformed")
    schema = cast(dict[str, object], deepcopy(parameters))
    if strict:
        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["required"] = list(properties)
        schema["additionalProperties"] = False
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": schema,
        "strict": strict,
    }


def anthropic_tool(tool: dict[str, JsonValue]) -> dict[str, object]:
    """Convert a public tool to Anthropic's custom-tool field names."""

    converted = provider_tool(tool, strict=True)
    return {
        "name": converted["name"],
        "description": converted["description"],
        "input_schema": _anthropic_schema(converted["parameters"]),
        "strict": True,
    }


def submit_final_schema() -> dict[str, object]:
    """Return a strict scalar-claim schema accepted by both providers."""

    nullable_string: dict[str, object] = {"type": ["string", "null"]}
    scalar: dict[str, object] = {
        "anyOf": [
            {"type": "null"},
            {"type": "boolean"},
            {"type": "integer"},
            {"type": "number"},
            {"type": "string"},
        ]
    }
    claim = {
        "type": "object",
        "properties": {
            "claim_type": {
                "type": "string",
                "enum": [item.value for item in ClaimType],
                "description": "Select the exact deterministic fact being asserted.",
            },
            "service_id": {
                **nullable_string,
                "description": "Relevant exact service ID, otherwise null.",
            },
            "tool_name": {
                **nullable_string,
                "description": "Relevant exact tool name, otherwise null.",
            },
            "key": {
                **nullable_string,
                "description": "Configuration key for config_value, otherwise null.",
            },
            "value": {
                **scalar,
                "description": (
                    "Exact observed scalar. Use the health/version/config value for state claims; "
                    "use true for incident_opened, action_succeeded, permission_limitation, or "
                    "unresolved_uncertainty when that condition actually occurred."
                ),
            },
        },
        "required": ["claim_type", "service_id", "tool_name", "key", "value"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["resolved", "not_resolved", "escalated"],
            },
            "summary": {"type": "string"},
            "claims": {"type": "array", "items": claim},
        },
        "required": ["status", "summary", "claims"],
        "additionalProperties": False,
    }


def submit_final_tool(*, strict: bool) -> dict[str, object]:
    """OpenAI custom function that terminates an episode structurally."""

    return {
        "type": "function",
        "name": "submit_final",
        "description": "Submit the final status and claims after all necessary tool work.",
        "parameters": submit_final_schema(),
        "strict": strict,
    }


def anthropic_submit_final_tool() -> dict[str, object]:
    """Anthropic custom tool that terminates an episode structurally."""

    return {
        "name": "submit_final",
        "description": "Submit the final status and claims after all necessary tool work.",
        "input_schema": submit_final_schema(),
        "strict": True,
    }


def _anthropic_schema(value: object) -> object:
    """Remove JSON Schema constraints unsupported by Anthropic strict custom tools."""

    if isinstance(value, dict):
        return {
            key: _anthropic_schema(item)
            for key, item in value.items()
            if key not in {"minimum", "maximum", "minLength"}
        }
    if isinstance(value, list):
        return [_anthropic_schema(item) for item in value]
    return value
