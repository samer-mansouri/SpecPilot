from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel

from specpilot.agent.config import LLMConfig
from specpilot.openapi.errors import SpecPilotError


class LLMError(SpecPilotError):
    """Raised when an error occurs during LLM provider communication."""

    pass


class FunctionCall(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: FunctionCall


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"role": self.role}
        if self.content is not None:
            data["content"] = self.content
        if self.name is not None:
            data["name"] = self.name
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            data["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        return data


class CompletionResponse(BaseModel):
    message: ChatMessage
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """Abstract base class for LLM model providers."""

    @abstractmethod
    def complete(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> CompletionResponse:
        """Send chat messages and optional tool definitions to the LLM provider."""
        pass


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible HTTP chat completion provider."""

    def __init__(self, config: LLMConfig, client: Optional[httpx.Client] = None) -> None:
        self.config = config
        self._client = client

    def complete(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> CompletionResponse:
        if not self.config.is_configured():
            raise LLMError(
                "LLM provider is not configured. Set SPECPILOT_LLM_API_KEY or OPENAI_API_KEY."
            )

        endpoint = f"{self.config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        client = self._client or httpx.Client(timeout=self.config.timeout)
        should_close = self._client is None

        try:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as err:
            raise LLMError(f"LLM request timed out after {self.config.timeout}s: {err}") from err
        except httpx.HTTPStatusError as err:
            status = err.response.status_code
            text = err.response.text
            raise LLMError(f"LLM HTTP error {status}: {text}") from err
        except Exception as err:
            raise LLMError(f"LLM communication error: {err}") from err
        finally:
            if should_close:
                client.close()

        try:
            choice = data["choices"][0]
            msg_data = choice["message"]
            finish_reason = choice.get("finish_reason", "stop")

            tool_calls = None
            if "tool_calls" in msg_data and msg_data["tool_calls"]:
                tool_calls = []
                for tc in msg_data["tool_calls"]:
                    fn_data = tc.get("function", {})
                    tool_calls.append(
                        ToolCall(
                            id=tc.get("id", ""),
                            type=tc.get("type", "function"),
                            function=FunctionCall(
                                name=fn_data.get("name", ""),
                                arguments=fn_data.get("arguments", "{}"),
                            ),
                        )
                    )

            res_msg = ChatMessage(
                role=msg_data.get("role", "assistant"),
                content=msg_data.get("content"),
                tool_calls=tool_calls,
            )
            return CompletionResponse(message=res_msg, finish_reason=finish_reason)

        except (KeyError, IndexError, TypeError) as err:
            raise LLMError(f"Malformed LLM completion response payload: {err}") from err
