import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from specpilot.mcp.registry import MCPToolRegistry
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.models import NormalizedSpec
from specpilot.openapi.parser import OpenAPIParser
from specpilot.safety.redactor import SecretRedactor


class SessionState:
    """Manages state for an interactive SpecPilot CLI session."""

    SESSIONS_DIR = Path.home() / ".specpilot" / "sessions"

    def __init__(self) -> None:
        self.spec: Optional[NormalizedSpec] = None
        self.registry: Optional[MCPToolRegistry] = None
        self.location: Optional[str] = None
        self.verbose: bool = False
        self.read_only: bool = False
        self.history: List[str] = []
        self.messages: List[Any] = []

    def clear_conversation(self) -> None:
        """Clear agent conversational message history."""
        self.messages.clear()

    def load_specification(self, location: str) -> NormalizedSpec:
        """Load and normalize an OpenAPI specification and update session registry."""
        loader = SpecLoader()
        loaded = loader.load(location)
        parsed_spec = OpenAPIParser(loaded).parse()

        self.spec = parsed_spec
        self.registry = MCPToolRegistry.from_spec(parsed_spec)
        self.location = location
        return parsed_spec

    def add_history_entry(self, command: str) -> None:
        """Add a command entry to session history, redacting sensitive patterns."""
        if not command or not command.strip():
            return

        clean_cmd = self.redact_secrets(command.strip())
        self.history.append(clean_cmd)

    def redact_secrets(self, text: str) -> str:
        """Redact sensitive credentials from text strings."""
        return SecretRedactor.redact(text)

    def save_session(self, session_name: str) -> Path:
        """Save active session state to ~/.specpilot/sessions/<session_name>.json."""
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = session_name.strip() if session_name and session_name.strip() else "default"
        if not safe_name.endswith(".json"):
            safe_name += ".json"
        
        session_file = self.SESSIONS_DIR / safe_name

        # Serialize messages
        serialized_messages = []
        for msg in self.messages:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                serialized_messages.append({"type": msg.type, "content": msg.content})
            elif isinstance(msg, dict):
                serialized_messages.append(msg)
            else:
                serialized_messages.append({"content": str(msg)})

        payload = {
            "location": self.location,
            "verbose": self.verbose,
            "read_only": self.read_only,
            "history": self.history,
            "messages": serialized_messages,
        }

        clean_data = SecretRedactor.redact(json.dumps(payload, indent=2))
        session_file.write_text(clean_data, encoding="utf-8")
        return session_file

    def load_session(self, session_name: str) -> Path:
        """Restore session state from ~/.specpilot/sessions/<session_name>.json."""
        safe_name = session_name.strip() if session_name and session_name.strip() else "default"
        if not safe_name.endswith(".json"):
            safe_name += ".json"

        session_file = self.SESSIONS_DIR / safe_name
        if not session_file.exists():
            raise FileNotFoundError(f"Session file '{session_file}' does not exist.")

        raw_data = session_file.read_text(encoding="utf-8")
        payload = json.loads(raw_data)

        location = payload.get("location")
        if location:
            self.load_specification(location)

        self.verbose = payload.get("verbose", False)
        self.read_only = payload.get("read_only", False)
        self.history = payload.get("history", [])

        # Restore message structures
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        restored_msgs = []
        for item in payload.get("messages", []):
            m_type = item.get("type") if isinstance(item, dict) else None
            m_content = item.get("content", "") if isinstance(item, dict) else str(item)
            if m_type == "human":
                restored_msgs.append(HumanMessage(content=m_content))
            elif m_type == "ai":
                restored_msgs.append(AIMessage(content=m_content))
            elif m_type == "system":
                restored_msgs.append(SystemMessage(content=m_content))
            else:
                restored_msgs.append(HumanMessage(content=m_content))

        self.messages = restored_msgs
        return session_file

    @classmethod
    def list_saved_sessions(cls) -> List[str]:
        """List all saved session names in ~/.specpilot/sessions/."""
        if not cls.SESSIONS_DIR.exists():
            return []
        return [f.stem for f in cls.SESSIONS_DIR.glob("*.json")]

