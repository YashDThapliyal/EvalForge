from evalforge.simulator.tools import tool_schemas


def test_tool_schemas_describe_every_argument_and_reject_unknown_fields() -> None:
    schemas = {item["name"]: item["input_schema"] for item in tool_schemas()}
    assert set(schemas) == {
        "inspect_service",
        "read_logs",
        "restart_service",
        "rollback_deployment",
        "update_config",
        "open_incident",
    }
    assert schemas["read_logs"]["properties"]["limit"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
    }
    assert schemas["rollback_deployment"]["properties"]["target_version"]["type"] == [
        "string",
        "null",
    ]
    assert schemas["open_incident"]["properties"]["severity"]["enum"] == [
        "low",
        "medium",
        "high",
        "critical",
    ]
    assert all(schema["additionalProperties"] is False for schema in schemas.values())
