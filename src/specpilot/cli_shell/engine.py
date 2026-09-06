import json
import sys
from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from specpilot import __version__
from specpilot.cli_shell.state import SessionState
from specpilot.mcp.executor import ToolExecutor
from specpilot.openapi.errors import SpecPilotError

console = Console()
error_console = Console(stderr=True)


class ShellEngine:
    """Interactive REPL shell engine for SpecPilot."""

    def __init__(self, state: Optional[SessionState] = None) -> None:
        self.state = state or SessionState()
        self._prompt_session: Optional[PromptSession[str]] = None

    def _get_prompt_session(self) -> PromptSession[str]:
        if self._prompt_session is None:
            from prompt_toolkit.output import DummyOutput
            import sys
            output = None if sys.stdout.isatty() else DummyOutput()
            self._prompt_session = PromptSession(history=InMemoryHistory(), output=output)
        return self._prompt_session

    def start_repl(self, initial_location: Optional[str] = None) -> None:
        """Start the interactive REPL shell loop."""
        self._print_welcome()

        if initial_location:
            self.execute_command(f"/use {initial_location}")

        while True:
            try:
                prompt_text = self._build_prompt()
                user_input = self._get_prompt_session().prompt(prompt_text)

                if not user_input.strip():
                    continue

                should_exit = self.execute_command(user_input.strip())
                if should_exit:
                    console.print("[dim]Exiting SpecPilot interactive shell. Goodbye![/dim]\n")
                    break

            except KeyboardInterrupt:
                console.print("\n[dim]Use /exit or Ctrl+D to quit shell.[/dim]")
                continue
            except EOFError:
                console.print("\n[dim]Exiting SpecPilot interactive shell. Goodbye![/dim]\n")
                break
            except Exception as err:
                error_console.print(f"[bold red]Shell Error:[/bold red] {err}")

    def execute_command(self, raw_command: str) -> bool:
        """Parse and execute a shell input string. Returns True if shell should exit."""
        self.state.add_history_entry(raw_command)
        cmd_str = raw_command.strip()

        if not cmd_str.startswith("/"):
            # If line doesn't start with /, treat as /help hint or run command
            console.print("[yellow]Unknown input. Type [bold]/help[/bold] for available commands.[/yellow]")
            return False

        parts = cmd_str.split(maxsplit=1)
        command_name = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""

        if command_name in ("/exit", "/quit"):
            return True
        elif command_name == "/help":
            self._handle_help()
        elif command_name == "/use":
            self._handle_use(args_str)
        elif command_name == "/api":
            self._handle_api()
        elif command_name == "/tools":
            self._handle_tools(args_str)
        elif command_name == "/inspect":
            self._handle_inspect(args_str)
        elif command_name == "/history":
            self._handle_history()
        elif command_name == "/verbose":
            self._handle_verbose(args_str)
        elif command_name == "/clear":
            console.clear()
        elif command_name == "/call":
            self._handle_call(args_str)
        else:
            console.print(f"[yellow]Unknown command '{command_name}'. Type [bold]/help[/bold] for command list.[/yellow]")

        return False

    def _print_welcome(self) -> None:
        console.print()
        console.print(Panel(f"[bold green]SpecPilot Interactive Shell v{__version__}[/bold green]", expand=False))
        console.print("Type [bold]/help[/bold] to list available commands, or [bold]/exit[/bold] to quit.\n")

    def _build_prompt(self) -> str:
        if self.state.spec:
            api_name = self.state.spec.title
            return f"specpilot ({api_name})> "
        return "specpilot> "

    def _handle_help(self) -> None:
        table = Table(title="SpecPilot Interactive Shell Commands", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="bold green", min_width=20)
        table.add_column("Description", style="white")

        table.add_row("/use <location>", "Load or switch active OpenAPI specification (path or URL)")
        table.add_row("/api", "Show active OpenAPI specification metadata")
        table.add_row("/tools [tag]", "List available MCP tools (optionally filter by tag)")
        table.add_row("/inspect <tool>", "Inspect detailed schema for an MCP tool")
        table.add_row("/call <tool> [json]", "Execute an MCP tool request against target API")
        table.add_row("/verbose [on|off]", "Toggle or inspect verbose operational logging mode")
        table.add_row("/history", "View session command history (secrets redacted)")
        table.add_row("/clear", "Clear terminal screen")
        table.add_row("/help", "Display this help reference")
        table.add_row("/exit", "Exit interactive shell")

        console.print()
        console.print(table)
        console.print()

    def _handle_use(self, location: str) -> None:
        if not location:
            error_console.print("[bold red]Usage:[/bold red] /use <file-path-or-url>")
            return

        try:
            spec = self.state.load_specification(location)
            console.print(f"[bold green]Loaded OpenAPI specification:[/bold green] {spec.title} (v{spec.api_version})")
            if self.state.verbose:
                console.print(f"[dim]Source: {location} | Operations: {len(spec.operations)} | MCP Tools: {len(self.state.registry.list_tools() if self.state.registry else [])}[/dim]")
        except SpecPilotError as err:
            error_console.print(f"[bold red]Failed to load specification:[/bold red] {err}")
        except Exception as err:
            error_console.print(f"[bold red]Unexpected error loading specification:[/bold red] {err}")

    def _handle_api(self) -> None:
        if not self.state.spec:
            console.print("[yellow]No API specification loaded. Use [bold]/use <location>[/bold] to load one.[/yellow]")
            return

        spec = self.state.spec
        console.print()
        console.print(Panel(f"[bold green]Active Specification: {spec.title}[/bold green]", expand=False))
        console.print(f"[bold]API Version:[/bold] {spec.api_version}")
        console.print(f"[bold]OpenAPI Version:[/bold] {spec.openapi_version}")
        console.print(f"[bold]Source:[/bold] {self.state.location}")
        console.print(f"[bold]Operations Discovered:[/bold] {len(spec.operations)}")
        if spec.servers:
            console.print(f"[bold]Base Server URL:[/bold] {spec.servers[0].url}")
        console.print()

    def _handle_tools(self, tag_filter: str) -> None:
        if not self.state.registry:
            console.print("[yellow]No API specification loaded. Use [bold]/use <location>[/bold] to load one.[/yellow]")
            return

        tools = self.state.registry.list_tools()
        if tag_filter:
            filter_lower = tag_filter.lower()
            tools = [
                t for t in tools
                if t.original_operation and any(filter_lower in tag.lower() for tag in t.original_operation.tags)
            ]

        title = f"Available MCP Tools ({len(tools)} tools)"
        if tag_filter:
            title += f" [filtered by tag '{tag_filter}']"

        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Tool Name", style="bold green", min_width=20)
        table.add_column("Method", style="bold yellow", width=8)
        table.add_column("Path", style="white", min_width=25)
        table.add_column("Description", style="dim white")

        for t in tools:
            table.add_row(t.name, t.method, t.path, t.description)

        console.print()
        console.print(table)
        console.print()

    def _handle_inspect(self, tool_name: str) -> None:
        if not self.state.registry:
            console.print("[yellow]No API specification loaded. Use [bold]/use <location>[/bold] to load one.[/yellow]")
            return

        if not tool_name:
            error_console.print("[bold red]Usage:[/bold red] /inspect <tool-name>")
            return

        tool = self.state.registry.get_tool(tool_name.strip())
        if not tool:
            error_console.print(f"[bold red]Tool '{tool_name}' not found.[/bold red]")
            return

        console.print()
        console.print(Panel(f"[bold green]MCP Tool Inspection: {tool.name}[/bold green]", expand=False))
        console.print(f"[bold]Method:[/bold] {tool.method}")
        console.print(f"[bold]Path:[/bold] {tool.path}")
        console.print(f"[bold]Description:[/bold] {tool.description}")
        if tool.base_url:
            console.print(f"[bold]Base Server URL:[/bold] {tool.base_url}")

        console.print("\n[bold cyan]Input JSON Schema:[/bold cyan]")
        schema_json = json.dumps(tool.input_schema, indent=2)
        console.print(Syntax(schema_json, "json", theme="monokai"))
        console.print()

    def _handle_history(self) -> None:
        console.print()
        console.print(Panel("[bold green]Session Command History[/bold green]", expand=False))
        if not self.state.history:
            console.print("[dim]No commands executed yet.[/dim]\n")
            return

        for idx, item in enumerate(self.state.history, start=1):
            console.print(f"  [dim]{idx:2d}.[/dim] {item}")
        console.print()

    def _handle_verbose(self, mode: str) -> None:
        sub = mode.strip().lower()
        if sub == "on":
            self.state.verbose = True
            console.print("[bold green]Verbose mode enabled.[/bold green]")
        elif sub == "off":
            self.state.verbose = False
            console.print("[dim]Verbose mode disabled.[/dim]")
        elif not sub:
            status = "enabled" if self.state.verbose else "disabled"
            console.print(f"Verbose mode is currently [bold]{status}[/bold].")
        else:
            error_console.print("[bold red]Usage:[/bold red] /verbose [on|off]")

    def _handle_call(self, args_str: str) -> None:
        if not self.state.registry:
            console.print("[yellow]No API specification loaded. Use [bold]/use <location>[/bold] to load one.[/yellow]")
            return

        parts = args_str.split(maxsplit=1)
        if not parts:
            error_console.print("[bold red]Usage:[/bold red] /call <tool-name> [json-args]")
            return

        tool_name = parts[0]
        json_raw = parts[1] if len(parts) > 1 else "{}"

        tool = self.state.registry.get_tool(tool_name)
        if not tool:
            error_console.print(f"[bold red]Tool '{tool_name}' not found.[/bold red]")
            return

        try:
            args = json.loads(json_raw)
        except Exception as err:
            error_console.print(f"[bold red]Invalid JSON args:[/bold red] {err}")
            return

        executor = ToolExecutor()
        result = executor.execute(tool, args)

        status_style = "bold green" if not result.is_error else "bold red"
        console.print(f"[{status_style}]HTTP Status: {result.status_code}[/{status_style}] ({result.duration_ms}ms)")
        if self.state.verbose:
            console.print(f"[dim]URL: {tool.method} {result.headers}[/dim]")

        console.print("\n[bold cyan]Response Body:[/bold cyan]")
        if isinstance(result.body, (dict, list)):
            console.print(Syntax(json.dumps(result.body, indent=2), "json", theme="monokai"))
        else:
            console.print(str(result.body))
        console.print()
