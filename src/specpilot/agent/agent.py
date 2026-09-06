from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from specpilot.agent.graph import SpecPilotGraph
from specpilot.agent.provider import LLMProvider
from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.models import ExecutionResult
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.safety.policy import SafetyPolicy


class ExecutedToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    status_code: Optional[int] = None
    is_error: bool = False
    result_summary: str = ""


from specpilot.agent.provider import ChatMessage, LLMProvider

class AgentResponse(BaseModel):
    content: str
    steps: int = 0
    tool_calls: List[ExecutedToolCall] = Field(default_factory=list)
    is_error: bool = False
    error_message: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)


class SpecPilotAgent:
    """Agent orchestrator backed by stateful LangGraph workflows."""

    def __init__(
        self,
        registry: MCPToolRegistry,
        provider: LLMProvider,
        executor: Optional[ToolExecutor] = None,
        max_steps: int = 5,
        safety_policy: Optional[SafetyPolicy] = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.executor = executor or ToolExecutor()
        self.max_steps = max_steps
        self.safety_policy = safety_policy or SafetyPolicy()
        self.graph = SpecPilotGraph(
            registry=self.registry,
            provider=self.provider,
            executor=self.executor,
            safety_policy=self.safety_policy,
        )

    def run(
        self,
        user_prompt: str,
        read_only: bool = False,
        approval_handler: Optional[Callable[[str, str, Dict[str, Any]], bool]] = None,
        verbose_callback: Optional[Callable[[str, Dict[str, Any], ExecutionResult], None]] = None,
        existing_messages: Optional[List[ChatMessage]] = None,
    ) -> AgentResponse:
        """Run the agentic tool execution loop via LangGraph."""
        res_state = self.graph.run(
            user_prompt=user_prompt,
            read_only=read_only or self.safety_policy.read_only_mode,
            approval_handler=approval_handler,
            verbose_callback=verbose_callback,
            max_steps=self.max_steps,
            existing_messages=existing_messages,
        )

        tool_calls: List[ExecutedToolCall] = []
        for raw_call in res_state.get("tool_calls_executed", []):
            tool_calls.append(
                ExecutedToolCall(
                    tool_name=raw_call.get("tool_name", ""),
                    arguments=raw_call.get("arguments", {}),
                    status_code=raw_call.get("status_code"),
                    is_error=raw_call.get("is_error", False),
                    result_summary=raw_call.get("result_summary", ""),
                )
            )

        content = res_state.get("final_content")
        is_err = res_state.get("is_error", False)
        err_msg = res_state.get("error_message")

        if content is None:
            if res_state.get("steps", 0) >= self.max_steps:
                content = "Agent reached maximum execution step limit without completing."
                is_err = True
                err_msg = "Max steps exceeded"
            else:
                content = ""

        return AgentResponse(
            content=content,
            steps=res_state.get("steps", 0),
            tool_calls=tool_calls,
            is_error=is_err,
            error_message=err_msg,
            messages=res_state.get("messages", []),
        )

    def generate_plan(self, user_prompt: str) -> AgentResponse:
        """Generate a structured step-by-step API execution plan without executing network requests."""
        plan_prompt = (
            f"You are an API Planning Specialist. Review the available tools and construct an explicit, step-by-step execution plan "
            f"to accomplish the following user request:\n\n"
            f"User Request: {user_prompt}\n\n"
            f"Provide a clear, numbered list of planned steps. For each step specify:\n"
            f"1. Planned Tool / Endpoint\n"
            f"2. Proposed Parameters / Arguments\n"
            f"3. Reasoning / Expected Outcome\n\n"
            f"DO NOT call any tools yet. Simply output the complete plan."
        )

        from langchain_core.messages import HumanMessage
        llm = self.provider.get_llm()
        res_msg = llm.invoke([HumanMessage(content=plan_prompt)])
        content = res_msg.content if hasattr(res_msg, "content") else str(res_msg)

        return AgentResponse(
            content=str(content),
            steps=1,
            tool_calls=[],
            is_error=False,
        )

