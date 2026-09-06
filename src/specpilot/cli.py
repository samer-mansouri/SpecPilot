import json
import sys
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from specpilot import __version__
from specpilot.mcp import MCPToolRegistry, ToolExecutor
from specpilot.openapi import OpenAPIParser, SpecLoader, SpecPilotError

console = Console()
error_console = Console(stderr=True)


@click.group()
@click.version_option(version=__version__, prog_name="specpilot")
def cli() -> None:
    """SpecPilot: OpenAPI-driven API automation CLI."""
    pass


@cli.command(name="shell")
@click.argument("location", type=str, required=False, default=None)
@click.option(
    "--read-only",
    is_flag=True,
    default=False,
    help="Enforce read-only safety mode (blocks mutating/destructive requests).",
)
def shell_cmd(location: Optional[str], read_only: bool) -> None:
    """Launch interactive SpecPilot shell session."""
    from specpilot.cli_shell import SessionState, ShellEngine
    state = SessionState()
    state.read_only = read_only
    engine = ShellEngine(state=state)
    engine.start_repl(initial_location=location)


@cli.command(name="import")
@click.argument("location", type=str)
def import_cmd(location: str) -> None:
    """Import and inspect an OpenAPI specification from a local file or URL."""
    try:
        loader = SpecLoader()
        loaded = loader.load(location)
        parser = OpenAPIParser(loaded)
        spec = parser.parse()

        console.print()
        console.print(Panel(f"[bold green]OpenAPI Specification Imported Successfully[/bold green]", expand=False))
        console.print(f"[bold]Title:[/bold] {spec.title}")
        console.print(f"[bold]API Version:[/bold] {spec.api_version}")
        console.print(f"[bold]OpenAPI Version:[/bold] {spec.openapi_version}")
        console.print(f"[bold]Source:[/bold] {spec.source}")
        console.print(f"[bold]Operations Discovered:[/bold] {len(spec.operations)}")
        if spec.servers:
            console.print(f"[bold]Base Server:[/bold] {spec.servers[0].url}")
        console.print()
    except SpecPilotError as err:
        error_console.print(f"[bold red]Error:[/bold red] {err}")
        sys.exit(1)
    except Exception as err:
        error_console.print(f"[bold red]Unexpected Error:[/bold red] {err}")
        sys.exit(1)


@cli.command(name="endpoints")
@click.argument("location", type=str)
def endpoints_cmd(location: str) -> None:
    """List all endpoints and operations in an OpenAPI specification."""
    try:
        loader = SpecLoader()
        loaded = loader.load(location)
        parser = OpenAPIParser(loaded)
        spec = parser.parse()

        table = Table(title=f"Endpoints in {spec.title} (v{spec.api_version})", show_header=True, header_style="bold cyan")
        table.add_column("Method", style="bold yellow", width=8)
        table.add_column("Path", style="white", min_width=25)
        table.add_column("Operation ID", style="green", min_width=20)
        table.add_column("Tags", style="dim magenta")

        for op in spec.operations:
            tags_str = ", ".join(op.tags) if op.tags else "-"
            table.add_row(op.method, op.path, op.operation_id, tags_str)

        console.print()
        console.print(table)
        console.print()
    except SpecPilotError as err:
        error_console.print(f"[bold red]Error:[/bold red] {err}")
        sys.exit(1)
    except Exception as err:
        error_console.print(f"[bold red]Unexpected Error:[/bold red] {err}")
        sys.exit(1)


@cli.command(name="tools")
@click.argument("location", type=str)
def tools_cmd(location: str) -> None:
    """List all generated MCP tools for an OpenAPI specification."""
    try:
        loader = SpecLoader()
        loaded = loader.load(location)
        spec = OpenAPIParser(loaded).parse()
        registry = MCPToolRegistry.from_spec(spec)
        tools = registry.list_tools()

        table = Table(title=f"Generated MCP Tools ({len(tools)} tools)", show_header=True, header_style="bold cyan")
        table.add_column("Tool Name", style="bold green", min_width=20)
        table.add_column("Method", style="bold yellow", width=8)
        table.add_column("Path", style="white", min_width=25)
        table.add_column("Description", style="dim white")

        for t in tools:
            table.add_row(t.name, t.method, t.path, t.description)

        console.print()
        console.print(table)
        console.print()
    except SpecPilotError as err:
        error_console.print(f"[bold red]Error:[/bold red] {err}")
        sys.exit(1)
    except Exception as err:
        error_console.print(f"[bold red]Unexpected Error:[/bold red] {err}")
        sys.exit(1)


@cli.command(name="inspect")
@click.argument("tool_name", type=str)
@click.argument("location", type=str)
def inspect_cmd(tool_name: str, location: str) -> None:
    """Inspect detailed schema and parameters of a specific MCP tool."""
    try:
        loader = SpecLoader()
        loaded = loader.load(location)
        spec = OpenAPIParser(loaded).parse()
        registry = MCPToolRegistry.from_spec(spec)
        tool = registry.get_tool(tool_name)

        if not tool:
            error_console.print(f"[bold red]Error:[/bold red] Tool '{tool_name}' not found in specification.")
            sys.exit(1)

        console.print()
        console.print(Panel(f"[bold green]MCP Tool Inspection: {tool.name}[/bold green]", expand=False))
        console.print(f"[bold]Method:[/bold] {tool.method}")
        console.print(f"[bold]Path:[/bold] {tool.path}")
        console.print(f"[bold]Description:[/bold] {tool.description}")
        if tool.base_url:
            console.print(f"[bold]Base Server URL:[/bold] {tool.base_url}")

        console.print("\n[bold cyan]Input JSON Schema:[/bold cyan]")
        schema_json = json.dumps(tool.input_schema, indent=2)
        console.print(Syntax(schema_json, "json", theme="monokai", line_numbers=False))
        console.print()
    except SpecPilotError as err:
        error_console.print(f"[bold red]Error:[/bold red] {err}")
        sys.exit(1)
    except Exception as err:
        error_console.print(f"[bold red]Unexpected Error:[/bold red] {err}")
        sys.exit(1)


@cli.command(name="call")
@click.argument("tool_name", type=str)
@click.argument("location", type=str)
@click.option("--json", "json_args", type=str, default="{}", help="JSON object containing tool arguments.")
@click.option("--base-url", type=str, default=None, help="Override base server URL for execution.")
def call_cmd(tool_name: str, location: str, json_args: str, base_url: Optional[str]) -> None:
    """Manually execute an MCP tool request against target API."""
    try:
        loader = SpecLoader()
        loaded = loader.load(location)
        spec = OpenAPIParser(loaded).parse()
        registry = MCPToolRegistry.from_spec(spec)
        tool = registry.get_tool(tool_name)

        if not tool:
            error_console.print(f"[bold red]Error:[/bold red] Tool '{tool_name}' not found in specification.")
            sys.exit(1)

        try:
            parsed_args = json.loads(json_args)
            if not isinstance(parsed_args, dict):
                raise ValueError("JSON arguments must be an object.")
        except Exception as err:
            error_console.print(f"[bold red]Error:[/bold red] Invalid --json argument: {err}")
            sys.exit(1)

        executor = ToolExecutor()
        result = executor.execute(tool, parsed_args, base_url_override=base_url)

        console.print()
        status_style = "bold green" if not result.is_error else "bold red"
        console.print(f"[{status_style}]HTTP Status: {result.status_code}[/{status_style}] ({result.duration_ms}ms)")

        if result.is_error and result.error_message:
            console.print(f"[bold red]Error Message:[/bold red] {result.error_message}")

        console.print("\n[bold cyan]Response Body:[/bold cyan]")
        if isinstance(result.body, (dict, list)):
            console.print(Syntax(json.dumps(result.body, indent=2), "json", theme="monokai"))
        else:
            console.print(str(result.body))
        console.print()
    except SpecPilotError as err:
        error_console.print(f"[bold red]Error:[/bold red] {err}")
        sys.exit(1)
    except Exception as err:
        error_console.print(f"[bold red]Unexpected Error:[/bold red] {err}")
        sys.exit(1)


@cli.command(name="test")
@click.argument("location", type=str)
@click.option("--tag", type=str, default=None, help="Filter test scenarios by operation tag.")
@click.option("--base-url", type=str, default=None, help="Target API base URL override.")
@click.option(
    "--read-only",
    is_flag=True,
    default=False,
    help="Enforce read-only safety mode (skips mutating/destructive tests).",
)
@click.option(
    "--allow-mutating",
    is_flag=True,
    default=False,
    help="Allow execution of mutating/destructive contract tests without prompt.",
)
@click.option("--json-output", type=str, default=None, help="Export contract test run report to JSON file.")
def test_cmd(
    location: str,
    tag: Optional[str],
    base_url: Optional[str],
    read_only: bool,
    allow_mutating: bool,
    json_output: Optional[str],
) -> None:
    """Run OpenAPI-driven API contract tests against target API."""
    try:
        from specpilot.safety.policy import SafetyPolicy
        from specpilot.testing.executor import ContractTestExecutor
        from specpilot.testing.generator import ScenarioGenerator
        from specpilot.testing.reporter import TestReporter

        loader = SpecLoader()
        loaded = loader.load(location)
        spec = OpenAPIParser(loaded).parse()

        target_url = base_url or (spec.servers[0].url if spec.servers else "http://localhost:8000")

        safety_policy = SafetyPolicy(read_only_mode=read_only)
        generator = ScenarioGenerator(safety_policy=safety_policy)
        scenarios = generator.generate_scenarios_for_spec(spec, tag_filter=tag)

        executor = ContractTestExecutor(
            base_url=target_url,
            safety_policy=safety_policy,
            allow_mutating=allow_mutating,
        )

        report = executor.execute_suite(
            scenarios=scenarios,
            api_title=spec.title,
            api_version=spec.api_version,
        )

        reporter = TestReporter(console=console)
        reporter.print_report(report)

        if json_output:
            reporter.export_json(report, json_output)
            console.print(f"[bold green]Report exported to JSON:[/bold green] {json_output}\n")

        if report.failed_count > 0:
            sys.exit(1)

    except SpecPilotError as err:
        error_console.print(f"[bold red]Error:[/bold red] {err}")
        sys.exit(1)
    except Exception as err:
        error_console.print(f"[bold red]Unexpected Error:[/bold red] {err}")
        sys.exit(1)


# Profile CLI commands
@cli.group(name="profile")
def profile_group() -> None:
    """Manage persistent API target configuration profiles."""
    pass


@profile_group.command(name="add")
@click.argument("name", type=str)
@click.option("--location", type=str, default=None, help="OpenAPI specification path or URL.")
@click.option("--base-url", type=str, default=None, help="Base server URL for API requests.")
@click.option("--model", type=str, default="gpt-4o-mini", help="LLM model name.")
@click.option("--read-only", is_flag=True, default=False, help="Set read-only safety mode preference.")
def profile_add(name: str, location: Optional[str], base_url: Optional[str], model: str, read_only: bool) -> None:
    """Add a new API configuration profile."""
    from specpilot.config import ConfigManager, Profile
    mgr = ConfigManager()
    profile = Profile(
        name=name,
        spec_location=location,
        base_url=base_url,
        model_name=model,
        read_only=read_only,
    )
    mgr.add_profile(profile)
    console.print(f"[bold green]Profile '{name}' added successfully.[/bold green]")


@profile_group.command(name="list")
def profile_list() -> None:
    """List all saved configuration profiles."""
    from specpilot.config import ConfigManager
    mgr = ConfigManager()
    profiles = mgr.list_profiles()
    store = mgr.load_store()

    if not profiles:
        console.print("[dim]No profiles saved yet. Use [bold]specpilot profile add <name>[/bold] to create one.[/dim]")
        return

    table = Table(title="SpecPilot Configuration Profiles", show_header=True, header_style="bold cyan")
    table.add_column("Active", justify="center", width=8)
    table.add_column("Name", style="bold green", min_width=15)
    table.add_column("Spec Location", style="white")
    table.add_column("Base URL", style="underline blue")
    table.add_column("Model", style="magenta")
    table.add_column("Safety", style="yellow")

    for p in profiles:
        active_mark = "[bold green]*[/bold green]" if store.active_profile == p.name else ""
        safety_str = "Read-Only" if p.read_only else "Interactive"
        table.add_row(
            active_mark,
            p.name,
            p.spec_location or "-",
            p.base_url or "-",
            p.model_name,
            safety_str,
        )

    console.print()
    console.print(table)
    console.print()


@profile_group.command(name="use")
@click.argument("name", type=str)
def profile_use(name: str) -> None:
    """Switch the active configuration profile."""
    from specpilot.config import ConfigManager
    mgr = ConfigManager()
    if mgr.set_active_profile(name):
        console.print(f"[bold green]Switched active profile to '{name}'.[/bold green]")
    else:
        error_console.print(f"[bold red]Error:[/bold red] Profile '{name}' not found.")
        sys.exit(1)


@profile_group.command(name="show")
@click.argument("name", type=str, required=False, default=None)
def profile_show(name: Optional[str]) -> None:
    """Show details of a profile (or current active profile)."""
    from specpilot.config import ConfigManager
    mgr = ConfigManager()
    active_p = mgr.get_active_profile()
    target_name = name or (active_p.name if active_p else None)

    if not target_name:
        error_console.print("[bold red]Error:[/bold red] No profile specified and no active profile set.")
        sys.exit(1)

    profile = mgr.get_profile(target_name)
    if not profile:
        error_console.print(f"[bold red]Error:[/bold red] Profile '{target_name}' not found.")
        sys.exit(1)

    console.print()
    console.print(Panel(f"[bold green]Profile Details: {profile.name}[/bold green]", expand=False))
    console.print(f"[bold]Spec Location:[/bold] {profile.spec_location or '-'}")
    console.print(f"[bold]Base Server URL:[/bold] {profile.base_url or '-'}")
    console.print(f"[bold]Model Provider:[/bold] {profile.model_provider}")
    console.print(f"[bold]Model Name:[/bold] {profile.model_name}")
    console.print(f"[bold]Timeout:[/bold] {profile.timeout}s")
    console.print(f"[bold]Read-Only Mode:[/bold] {profile.read_only}")
    console.print()


@profile_group.command(name="remove")
@click.argument("name", type=str)
def profile_remove(name: str) -> None:
    """Remove a profile."""
    from specpilot.config import ConfigManager
    mgr = ConfigManager()
    if mgr.remove_profile(name):
        console.print(f"[bold green]Profile '{name}' removed successfully.[/bold green]")
    else:
        error_console.print(f"[bold red]Error:[/bold red] Profile '{name}' not found.")
        sys.exit(1)


# Config CLI commands
@cli.group(name="config")
def config_group() -> None:
    """Inspect SpecPilot configuration settings and paths."""
    pass


@config_group.command(name="show")
def config_show() -> None:
    """Show configuration summary and active profile."""
    from specpilot.config import ConfigManager
    mgr = ConfigManager()
    store = mgr.load_store()
    active = mgr.get_active_profile()

    console.print()
    console.print(Panel("[bold green]SpecPilot Global Configuration[/bold green]", expand=False))
    console.print(f"[bold]Config Path:[/bold] {mgr.config_path}")
    console.print(f"[bold]Total Profiles:[/bold] {len(store.profiles)}")
    console.print(f"[bold]Active Profile:[/bold] {active.name if active else 'None'}")
    console.print()


@config_group.command(name="path")
def config_path() -> None:
    """Print path to persistent configuration file."""
    from specpilot.config import ConfigManager
    mgr = ConfigManager()
    console.print(str(mgr.config_path))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()

