"""Permission lookup kept separate from transition logic."""

from evalforge.domain.trace import PermissionDecision
from evalforge.domain.world import Permission, WorldState

TOOL_PERMISSIONS: dict[str, Permission] = {
    "inspect_service": Permission.READ_SERVICE,
    "read_logs": Permission.READ_LOGS,
    "restart_service": Permission.RESTART_SERVICE,
    "rollback_deployment": Permission.ROLLBACK_DEPLOYMENT,
    "update_config": Permission.UPDATE_CONFIG,
    "open_incident": Permission.OPEN_INCIDENT,
}


def decide_permission(world: WorldState, actor_id: str, tool_name: str) -> PermissionDecision:
    """Return an auditable decision without mutating state."""

    required = TOOL_PERMISSIONS.get(tool_name)
    if required is None:
        return PermissionDecision(allowed=False, required="unknown", reason="Unknown tool")
    allowed = required in world.permissions.get(actor_id, [])
    return PermissionDecision(
        allowed=allowed,
        required=required.value,
        reason="Permission granted" if allowed else f"Actor lacks {required.value}",
    )

