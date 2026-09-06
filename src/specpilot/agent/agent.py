import json
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from specpilot.agent.provider import ChatMessage, LLMError, LLMProvider
from specpilot.agent.tools import convert_registry_to_llm_tools
from specpilot.mcp.models import ExecutionResult
from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.registry import MCPToolRegistry


class ExecutedToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    status_code: Optional[int] = None
    is_error: bool = False
    result_summary: str = ""


class AgentResponse(BaseModel):
    content: str
    steps: int = 0
    tool_calls: List[ExecutedToolCall] = Field(default_factory=list)
    is_error: bool = False
    error_message: Optional[str] = None


class SpecPilotAgent:
    """Agent orchestrator for bounded LLM tool calling loops."""

    def __init__(
        self,
        registry: MCPToolRegistry,
        provider: LLMProvider,
        executor: Optional[ToolExecutor] = None,
        max_steps: int = 5,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.executor = executor or ToolExecutor()
        self.max_steps = max_steps

    def run(
        self,
        user_prompt: str,
        verbose_callback: Optional[Callable[[str, Dict[str, Any], ExecutionResult], None]] = None,
    ) -> AgentResponse:
        """Run the agentic tool execution loop for a user natural language prompt."""
        llm_tools = convert_registry_to_llm_tools(self.registry)
        
        system_msg = ChatMessage(
            role="system",
            content=(
                "You are SpecPilot, an API automation assistant. "
                "Use the available tools to query and interact with the target API as requested by the user. "
                "Synthesize concise, helpful final answers after executing tools."
            ),
        )

        messages: List[ChatMessage] = [system_msg, ChatMessage(role="user", content=user_prompt)]
        executed_calls: List[ExecutedToolCall] = []
        steps = 0

        while steps < self.max_steps:
            try:
                response = self.provider.complete(messages, tools=llm_tools if llm_tools else None)
            except LLMError as err:
                return AgentResponse(
                    content=f"LLM Provider Error: {err}",
                    steps=steps,
                    tool_calls=executed_calls,
                    is_error=True,
                    error_message=str(err),
                )
            except Exception as err:
                return AgentResponse(
                    content=f"Unexpected Error: {err}",
                    steps=steps,
                    tool_calls=executed_calls,
                    is_error=True,
                    error_message=str(err),
                )

            steps += 1
            assistant_msg = response.message

            # If LLM didn't request any tool calls, return final assistant content
            if not assistant_msg.tool_calls:
                messages.append(assistant_msg)
                return AgentResponse(
                    content=assistant_msg.content or "",
                    steps=steps,
                    tool_calls=executed_calls,
                )

            # Append assistant's tool-call request message to history
            messages.append(assistant_msg)

            # Process each requested tool call
            for tc in assistant_msg.tool_calls:
                tool_name = tc.function.name
                tool_id = tc.id

                # Parse arguments
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

                # Retrieve tool from registry
                tool = self.registry.get_tool(tool_name)
                if not tool:
                    err_msg = json.dumps({"error": f"Tool '{tool_name}' not found in registry."})
                    messages.append(
                        ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=err_msg)
                    )
                    executed_calls.append(
                        ExecutedToolCall(
                            tool_name=tool_name,
                            arguments=args,
                            is_error=True,
                            result_summary=f"Tool '{tool_name}' not found",
                        )
                    )
                    continue

                # Execute tool
                exec_result = self.executor.execute(tool, args)

                if verbose_callback:
                    verbose_callback(tool_name, args, exec_result)

                # Format tool output for LLM
                if exec_result.is_error:
                    content_str = json.dumps(
                        {"error": exec_result.error_message or "Tool execution failed", "status": exec_result.status_code}
                    )
                    summary = f"Error {exec_result.status_code}: {exec_result.error_message}"
                else:
                    if isinstance(exec_result.body, (dict, list)):
                        content_str = json.dumps(exec_result.body)
                    else:
                        content_str = str(exec_result.body)
                    summary = f"Status {exec_result.status_code}"

                executed_calls.append(
                    ExecutedToolCall(
                        tool_name=tool_name,
                        arguments=args,
                        status_code=exec_result.status_code,
                        is_error=exec_result.is_error,
                        result_summary=summary,
                    )
                )

                messages.append(
                    ChatMessage(role="tool", name=tool_name, tool_call_id=tool_id, content=content_str)
                )

        return AgentResponse(
            content="Agent reached maximum execution step limit without completing.",
            steps=steps,
            tool_calls=executed_calls,
            is_error=True,
            error_message="Max steps exceeded",
        )
