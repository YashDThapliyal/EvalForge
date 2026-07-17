"""Exact tool-call replay agent."""

from evalforge.agents.base import AgentFinal, AgentRequest, ToolCall, ToolRegistry


class ReplayAgent:
    """Replay stored calls and a stored terminal result."""

    def __init__(self, calls: list[ToolCall], final: AgentFinal | None):
        self.calls = [call.model_copy(deep=True) for call in calls]
        self.final = final or AgentFinal(
            status="not_resolved", summary="Stored run had no final result", claims=[]
        )

    def run(self, request: AgentRequest, tools: ToolRegistry) -> AgentFinal:
        """Replay the stored provider-neutral sequence."""

        del request
        for call in self.calls:
            tools.call(call.tool_name, call.arguments)
        return self.final.model_copy(deep=True)

