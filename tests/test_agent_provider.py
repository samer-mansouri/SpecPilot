import pytest
import respx
import httpx

from specpilot.agent import (
    ChatMessage,
    LLMConfig,
    LLMError,
    OpenAICompatibleProvider,
)


def test_llm_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPECPILOT_LLM_API_KEY", "test_key_123")
    monkeypatch.setenv("SPECPILOT_LLM_BASE_URL", "https://api.custom.com/v1/")
    monkeypatch.setenv("SPECPILOT_LLM_MODEL", "gpt-4o")

    config = LLMConfig.from_env()
    assert config.api_key == "test_key_123"
    assert config.base_url == "https://api.custom.com/v1"
    assert config.model == "gpt-4o"
    assert config.is_configured() is True


def test_llm_config_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPECPILOT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = LLMConfig.from_env()
    assert config.api_key is None
    assert config.is_configured() is False


@respx.mock
def test_openai_provider_complete_text() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "Hello! How can I assist you?",
                        },
                    }
                ]
            },
        )
    )

    config = LLMConfig(api_key="test_key")
    provider = OpenAICompatibleProvider(config)
    messages = [ChatMessage(role="user", content="Hi")]

    resp = provider.complete(messages)
    assert resp.finish_reason == "stop"
    assert resp.message.role == "assistant"
    assert resp.message.content == "Hello! How can I assist you?"
    assert resp.message.tool_calls is None


@respx.mock
def test_openai_provider_complete_tool_call() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_999",
                                    "type": "function",
                                    "function": {
                                        "name": "list_pets",
                                        "arguments": '{"limit": 5}',
                                    },
                                }
                            ],
                        },
                    }
                ]
            },
        )
    )

    config = LLMConfig(api_key="test_key")
    provider = OpenAICompatibleProvider(config)
    messages = [ChatMessage(role="user", content="List 5 pets")]

    resp = provider.complete(messages)
    assert resp.finish_reason == "tool_calls"
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].function.name == "list_pets"
    assert resp.message.tool_calls[0].function.arguments == '{"limit": 5}'


def test_openai_provider_unconfigured_error() -> None:
    config = LLMConfig(api_key=None)
    provider = OpenAICompatibleProvider(config)
    messages = [ChatMessage(role="user", content="Hello")]

    with pytest.raises(LLMError, match="provider is not configured"):
        provider.complete(messages)


@respx.mock
def test_openai_provider_http_error() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="Internal Error")
    )

    config = LLMConfig(api_key="test_key")
    provider = OpenAICompatibleProvider(config)
    messages = [ChatMessage(role="user", content="Hi")]

    with pytest.raises(LLMError, match="LLM HTTP error 500"):
        provider.complete(messages)
