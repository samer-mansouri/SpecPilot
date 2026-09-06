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
def shell_cmd(location: Optional[str]) -> None:
    """Launch interactive SpecPilot shell session."""
    from specpilot.cli_shell import ShellEngine
    engine = ShellEngine()
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
