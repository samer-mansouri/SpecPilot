from typing import List, Optional

from specpilot.mcp.registry import MCPToolRegistry
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.models import NormalizedSpec
from specpilot.openapi.parser import OpenAPIParser
from specpilot.safety.redactor import SecretRedactor


class SessionState:
    """Manages state for an interactive SpecPilot CLI session."""

    def __init__(self) -> None:
        self.spec: Optional[NormalizedSpec] = None
        self.registry: Optional[MCPToolRegistry] = None
        self.location: Optional[str] = None
        self.verbose: bool = False
        self.read_only: bool = False
        self.history: List[str] = []

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
