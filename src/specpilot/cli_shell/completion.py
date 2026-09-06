from typing import Any, Iterable, List

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from specpilot.cli_shell.state import SessionState


class SpecPilotCompleter(Completer):
    """Dynamic completer for SpecPilot interactive shell commands, tool names, and tags."""

    COMMANDS = [
        "/use",
        "/api",
        "/tools",
        "/inspect",
        "/call",
        "/verbose",
        "/safety",
        "/history",
        "/clear",
        "/help",
        "/exit",
        "/quit",
    ]

    def __init__(self, state: SessionState) -> None:
        self.state = state

    def get_completions(self, document: Document, complete_event: Any = None) -> Iterable[Completion]:
        text = document.text_before_cursor
        stripped = text.lstrip()

        if not stripped.startswith("/"):
            return

        parts = stripped.split()
        if len(parts) == 0 or (len(parts) == 1 and not text.endswith(" ")):
            # Completing primary command name
            current = parts[0] if parts else "/"
            for cmd in self.COMMANDS:
                if cmd.startswith(current):
                    yield Completion(cmd, start_position=-len(current))
            return

        # Sub-argument completion
        cmd_name = parts[0].lower()
        arg_prefix = parts[1] if len(parts) > 1 else ""
        if text.endswith(" ") and len(parts) == 1:
            arg_prefix = ""

        if cmd_name in ("/inspect", "/call") and self.state.registry:
            # Complete tool names
            tools = self.state.registry.list_tools()
            for t in tools:
                if t.name.startswith(arg_prefix):
                    yield Completion(t.name, start_position=-len(arg_prefix))

        elif cmd_name == "/tools" and self.state.spec:
            # Complete tags
            tags = self.state.spec.tags
            for tag in tags:
                if tag.startswith(arg_prefix):
                    yield Completion(tag, start_position=-len(arg_prefix))

        elif cmd_name == "/verbose":
            for mode in ["on", "off"]:
                if mode.startswith(arg_prefix):
                    yield Completion(mode, start_position=-len(arg_prefix))

        elif cmd_name == "/safety":
            for mode in ["read-only", "interactive"]:
                if mode.startswith(arg_prefix):
                    yield Completion(mode, start_position=-len(arg_prefix))
