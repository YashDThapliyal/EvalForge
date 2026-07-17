"""Hidden-plan agent used exclusively during validation and tests."""

from evalforge.agents.base import AgentFinal, AgentRequest, ToolRegistry
from evalforge.domain.scenario import OracleAction


class OracleAgent:
    """Execute a supplied private oracle plan."""

    def __init__(self, plan: list[OracleAction]):
        self.plan = [action.model_copy(deep=True) for action in plan]

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Execute every hidden action; request itself remains public."""

        del request
        for action in self.plan:
            tools.call(action.tool_name, action.arguments)
        return AgentFinal(status="resolved", summary="Oracle plan completed", claims=[])
