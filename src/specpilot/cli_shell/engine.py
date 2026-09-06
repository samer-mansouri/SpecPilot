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
            from specpilot.cli_shell.completion import SpecPilotCompleter
            import sys
            output = None if sys.stdout.isatty() else DummyOutput()
            self._prompt_session = PromptSession(
                history=InMemoryHistory(),
                completer=SpecPilotCompleter(self.state),
                output=output,
            )
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
            self._handle_agent_prompt(cmd_str)
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
        elif command_name == "/safety":
            self._handle_safety(args_str)
        elif command_name == "/plan":
            self._handle_plan(args_str)
        elif command_name == "/save":
            self._handle_save(args_str)
        elif command_name == "/load":
            self._handle_load(args_str)
        elif command_name == "/clear":
            console.clear()
        elif command_name == "/reset":
            self.state.clear_conversation()
            console.print("[bold green]Conversational memory reset.[/bold green]")
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
        table.add_row("/plan <prompt>", "Generate step-by-step API execution plan before executing")
        table.add_row("/save [name]", "Save active session state and credentials to disk")
        table.add_row("/load <name>", "Restore session state and credentials from disk")
        table.add_row("/verbose [on|off]", "Toggle or inspect verbose operational logging mode")
        table.add_row("/safety [read-only|interactive]", "Inspect or set safety execution mode")
        table.add_row("/history", "View session command history (secrets redacted)")
        table.add_row("/clear", "Clear terminal screen")
        table.add_row("/reset", "Reset conversational message memory")
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
        if result.captured_token:
            console.print("[bold green][Auth Token Detected][/bold green] Automatically saved SPECPILOT_BEARER_TOKEN to runtime environment and .env")
        if self.state.verbose:
            console.print(f"[dim]URL: {tool.method} {result.headers}[/dim]")

        console.print("\n[bold cyan]Response Body:[/bold cyan]")
        if isinstance(result.body, (dict, list)):
            console.print(Syntax(json.dumps(result.body, indent=2), "json", theme="monokai", word_wrap=True))
        else:
            console.print(str(result.body), soft_wrap=True)
        console.print()

    def _handle_safety(self, mode: str) -> None:
        sub = mode.strip().lower()
        if sub in ("read-only", "readonly"):
            self.state.read_only = True
            console.print("[bold green]Safety mode set to Read-Only.[/bold green]")
        elif sub in ("interactive", "normal"):
            self.state.read_only = False
            console.print("[bold green]Safety mode set to Interactive.[/bold green]")
        elif not sub:
            status = "Read-Only" if self.state.read_only else "Interactive"
            console.print(f"Safety mode is currently [bold]{status}[/bold].")
        else:
            error_console.print("[bold red]Usage:[/bold red] /safety [read-only|interactive]")

    def _handle_agent_prompt(self, prompt: str) -> None:
        if not self.state.registry:
            console.print(
                "[yellow]No API specification loaded. Use [bold]/use <location>[/bold] to load one.[/yellow]"
            )
            return

        from specpilot.agent import LLMConfig, OpenAICompatibleProvider, SpecPilotAgent
        from specpilot.mcp.models import ExecutionResult

        config = LLMConfig.from_env()
        if not config.is_configured():
            console.print(
                "[yellow]LLM provider is not configured. Set [bold]SPECPILOT_LLM_API_KEY[/bold] (or [bold]OPENAI_API_KEY[/bold]) to enable natural language API instructions.[/yellow]"
            )
            return

        provider = OpenAICompatibleProvider(config)
        agent = SpecPilotAgent(registry=self.state.registry, provider=provider, max_steps=config.max_steps)

        def _verbose_callback(tool_name: str, args: Dict[str, Any], result: ExecutionResult) -> None:
            clean_args = self.state.redact_secrets(json.dumps(args))
            console.print(f"[dim cyan][Tool][/dim cyan] [bold]{tool_name}[/bold]")
            console.print(f"[dim cyan][Arguments][/dim cyan] {clean_args}")
            status = result.status_code if result.status_code is not None else "error"
            console.print(f"[dim cyan][Result][/dim cyan] Status {status}")

        def _approval_handler(method: str, path: str, args: Dict[str, Any]) -> bool:
            clean_args = self.state.redact_secrets(json.dumps(args, indent=2))
            console.print()
            console.print(Panel("[bold yellow]Safety Policy Approval Required[/bold yellow]", expand=False))
            console.print(f"[bold]Operation:[/bold] {method.upper()} {path}")
            console.print(f"[bold]Arguments:[/bold]\n{Syntax(clean_args, 'json', theme='monokai')}")
            console.print("[dim]This operation modifies remote data.[/dim]")
            try:
                session = self._get_prompt_session()
                ans = session.prompt("Execute? [y/N]: ").strip().lower()
                return ans in ("y", "yes")
            except (KeyboardInterrupt, EOFError):
                return False

        response = agent.run(
            prompt,
            read_only=self.state.read_only,
            approval_handler=_approval_handler,
            verbose_callback=_verbose_callback if self.state.verbose else None,
            existing_messages=self.state.messages,
        )

        if response.messages:
            self.state.messages = response.messages

        if response.is_error:
            error_console.print(f"[bold red]Agent Error:[/bold red] {response.content}")
        else:
            console.print(f"\n[bold green]SpecPilot Agent:[/bold green]\n{response.content}\n")

    def _handle_plan(self, prompt: str) -> None:
        if not self.state.registry:
            console.print("[yellow]No API specification loaded. Use [bold]/use <location>[/bold] to load one.[/yellow]")
            return

        if not prompt.strip():
            error_console.print("[bold red]Usage:[/bold red] /plan <natural language request>")
            return

        from specpilot.agent import LLMConfig, OpenAICompatibleProvider, SpecPilotAgent

        config = LLMConfig.from_env()
        if not config.is_configured():
            console.print("[yellow]LLM provider is not configured. Set [bold]SPECPILOT_LLM_API_KEY[/bold] to use /plan mode.[/yellow]")
            return

        provider = OpenAICompatibleProvider(config)
        agent = SpecPilotAgent(registry=self.state.registry, provider=provider)

        console.print()
        console.print("[dim cyan]Generating API execution plan...[/dim cyan]")
        response = agent.generate_plan(prompt.strip())

        console.print()
        console.print(Panel(f"[bold cyan]Generated API Execution Plan[/bold cyan]\n\n{response.content}", expand=False))
        console.print()

        try:
            session = self._get_prompt_session()
            ans = session.prompt("Execute this plan? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                console.print("[bold green]Executing planned API workflow...[/bold green]\n")
                self._handle_agent_prompt(prompt.strip())
            else:
                console.print("[dim]Plan execution cancelled.[/dim]\n")
        except (KeyboardInterrupt, EOFError):
            console.print("[dim]Plan execution cancelled.[/dim]\n")

    def _handle_save(self, session_name: str) -> None:
        name = session_name.strip() if session_name and session_name.strip() else "default"
        try:
            file_path = self.state.save_session(name)
            console.print(f"[bold green]Session state saved to:[/bold green] {file_path}")
        except Exception as err:
            error_console.print(f"[bold red]Failed to save session:[/bold red] {err}")

    def _handle_load(self, session_name: str) -> None:
        if not session_name.strip():
            saved = self.state.list_saved_sessions()
            if saved:
                console.print("[bold cyan]Available saved sessions:[/bold cyan] " + ", ".join(saved))
            else:
                console.print("[yellow]No saved sessions found. Usage: /load <session-name>[/yellow]")
            return

        try:
            file_path = self.state.load_session(session_name.strip())
            console.print(f"[bold green]Session state restored from:[/bold green] {file_path}")
            if self.state.spec:
                console.print(f"[dim]Loaded API: {self.state.spec.title} (v{self.state.spec.api_version})[/dim]")
        except Exception as err:
            error_console.print(f"[bold red]Failed to load session:[/bold red] {err}")

