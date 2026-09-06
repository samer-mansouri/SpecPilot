import json
from typing import Any, Callable, Dict, List, Optional, TypedDict
from langgraph.graph import END, StateGraph

from specpilot.agent.provider import ChatMessage, LLMError, LLMProvider, ToolCall
from specpilot.agent.tools import convert_registry_to_llm_tools
from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.models import ExecutionResult
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.safety.policy import SafetyPolicy


class ExecutedToolCall(TypedDict, total=False):
    tool_name: str
    arguments: Dict[str, Any]
    status_code: Optional[int]
    is_error: bool
    result_summary: str


class GraphState(TypedDict, total=False):
    messages: List[ChatMessage]
    steps: int
    max_steps: int
    read_only: bool
    approval_handler: Optional[Callable[[str, str, Dict[str, Any]], bool]]
    verbose_callback: Optional[Callable[[str, Dict[str, Any], ExecutionResult], None]]
    tool_calls_executed: List[ExecutedToolCall]
    pending_tool_calls: List[ToolCall]
    approved_tool_calls: List[ToolCall]
    is_error: bool
    error_message: Optional[str]
    final_content: Optional[str]


class SpecPilotGraph:
    """LangGraph workflow orchestrator for multi-step agent execution and safety enforcement."""

    def __init__(
        self,
        registry: MCPToolRegistry,
        provider: LLMProvider,
        executor: Optional[ToolExecutor] = None,
        safety_policy: Optional[SafetyPolicy] = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.executor = executor or ToolExecutor()
        self.safety_policy = safety_policy or SafetyPolicy()
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(GraphState)

        workflow.add_node("agent", self._agent_node)
        workflow.add_node("safety", self._safety_node)
        workflow.add_node("execute_tools", self._tool_execution_node)

        workflow.set_entry_point("agent")

        workflow.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {
                "safety": "safety",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "safety",
            self._route_after_safety,
            {
                "execute_tools": "execute_tools",
                "agent": "agent",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "execute_tools",
            self._route_after_execution,
            {
                "agent": "agent",
                "end": END,
            },
        )

        return workflow.compile()

    def _agent_node(self, state: GraphState) -> Dict[str, Any]:
        steps = state.get("steps", 0) + 1
        messages = list(state.get("messages", []))
        llm_tools = convert_registry_to_llm_tools(self.registry)

        try:
            response = self.provider.complete(messages, tools=llm_tools if llm_tools else None)
        except LLMError as err:
            return {
                "steps": steps,
                "is_error": True,
                "error_message": str(err),
                "final_content": f"LLM Provider Error: {err}",
            }
        except Exception as err:
            return {
                "steps": steps,
                "is_error": True,
                "error_message": str(err),
                "final_content": f"Unexpected Error: {err}",
            }

        assistant_msg = response.message
        messages.append(assistant_msg)

        if not assistant_msg.tool_calls:
            return {
                "steps": steps,
                "messages": messages,
                "final_content": assistant_msg.content or "",
                "pending_tool_calls": [],
                "approved_tool_calls": [],
            }

        return {
            "steps": steps,
            "messages": messages,
            "pending_tool_calls": assistant_msg.tool_calls,
            "approved_tool_calls": [],
        }

    def _safety_node(self, state: GraphState) -> Dict[str, Any]:
        pending = state.get("pending_tool_calls", [])
        messages = list(state.get("messages", []))
        executed_calls = list(state.get("tool_calls_executed", []))
        read_only = state.get("read_only", False)
        approval_handler = state.get("approval_handler")

        approved: List[ToolCall] = []

        for tc in pending:
            tool_name = tc.function.name
            tool_id = tc.id

            tool = self.registry.get_tool(tool_name)
            if not tool:
                err_msg = json.dumps({"error": f"Tool '{tool_name}' not found in registry."})
                messages.append(
                    ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=err_msg)
                )
                executed_calls.append(
                    {
                        "tool_name": tool_name,
                        "arguments": {},
                        "is_error": True,
                        "result_summary": f"Tool '{tool_name}' not found",
                    }
                )
                continue

            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                if not isinstance(args, dict):
                    args = {}
            except json.JSONDecodeError as err:
                err_msg = json.dumps({"error": f"Invalid JSON arguments: {err}"})
                messages.append(
                    ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=err_msg)
                )
                continue

            # Check read-only policy
            if not self.safety_policy.is_allowed(tool.method, read_only_override=read_only):
                err_msg = json.dumps(
                    {
                        "error": f"Operation '{tool.method} {tool.path}' blocked by read-only safety mode."
                    }
                )
                messages.append(
                    ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=err_msg)
                )
                executed_calls.append(
                    {
                        "tool_name": tool_name,
                        "arguments": args,
                        "is_error": True,
                        "result_summary": "Blocked by read-only mode",
                    }
                )
                continue

            # Check human approval requirement
            if self.safety_policy.requires_approval(tool.method, read_only_override=read_only):
                if approval_handler:
                    is_approved = approval_handler(tool.method, tool.path, args)
                    if not is_approved:
                        err_msg = json.dumps(
                            {
                                "error": f"Operation '{tool.method} {tool.path}' cancelled by user."
                            }
                        )
                        messages.append(
                            ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=err_msg)
                        )
                        executed_calls.append(
                            {
                                "tool_name": tool_name,
                                "arguments": args,
                                "is_error": True,
                                "result_summary": "Rejected by user",
                            }
                        )
                        continue

            approved.append(tc)

        return {
            "messages": messages,
            "tool_calls_executed": executed_calls,
            "pending_tool_calls": [],
            "approved_tool_calls": approved,
        }

    def _tool_execution_node(self, state: GraphState) -> Dict[str, Any]:
        approved = state.get("approved_tool_calls", [])
        messages = list(state.get("messages", []))
        executed_calls = list(state.get("tool_calls_executed", []))
        verbose_callback = state.get("verbose_callback")

        for tc in approved:
            tool_name = tc.function.name
            tool_id = tc.id
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}

            tool = self.registry.get_tool(tool_name)
            if not tool:
                continue

            result = self.executor.execute(tool, args)

            if verbose_callback:
                verbose_callback(tool_name, args, result)

            if result.is_error:
                content_str = json.dumps(
                    {"error": result.error_message or "Tool execution failed", "status": result.status_code}
                )
                summary = f"Error {result.status_code}: {result.error_message}"
            else:
                if isinstance(result.body, (dict, list)):
                    content_str = json.dumps(result.body)
                else:
                    content_str = str(result.body)
                summary = f"Status {result.status_code}"

            executed_calls.append(
                {
                    "tool_name": tool_name,
                    "arguments": args,
                    "status_code": result.status_code,
                    "is_error": result.is_error,
                    "result_summary": summary,
                }
            )

            messages.append(
                ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=content_str)
            )

        return {
            "messages": messages,
            "tool_calls_executed": executed_calls,
            "approved_tool_calls": [],
        }

    def _route_after_agent(self, state: GraphState) -> str:
        if state.get("is_error") or state.get("final_content") is not None:
            return "end"
        if state.get("steps", 0) >= state.get("max_steps", 5):
            return "end"
        if state.get("pending_tool_calls"):
            return "safety"
        return "end"

    def _route_after_safety(self, state: GraphState) -> str:
        if state.get("approved_tool_calls"):
            return "execute_tools"
        if state.get("steps", 0) >= state.get("max_steps", 5):
            return "end"
        return "agent"

    def _route_after_execution(self, state: GraphState) -> str:
        if state.get("steps", 0) >= state.get("max_steps", 5):
            return "end"
        return "agent"

    def run(
        self,
        user_prompt: str,
        read_only: bool = False,
        approval_handler: Optional[Callable[[str, str, Dict[str, Any]], bool]] = None,
        verbose_callback: Optional[Callable[[str, Dict[str, Any], ExecutionResult], None]] = None,
        max_steps: int = 5,
    ) -> Dict[str, Any]:
        """Invoke the LangGraph workflow for a prompt."""
        system_msg = ChatMessage(
            role="system",
            content=(
                "You are SpecPilot, an API automation assistant. "
                "Use available tools to interact with the target API as requested by the user. "
                "Synthesize concise, helpful final answers after executing tools."
            ),
        )

        initial_state: GraphState = {
            "messages": [system_msg, ChatMessage(role="user", content=user_prompt)],
            "steps": 0,
            "max_steps": max_steps,
            "read_only": read_only,
            "approval_handler": approval_handler,
            "verbose_callback": verbose_callback,
            "tool_calls_executed": [],
            "pending_tool_calls": [],
            "approved_tool_calls": [],
            "is_error": False,
            "error_message": None,
            "final_content": None,
        }

        final_state = self._graph.invoke(initial_state)
        return final_state
