import sys
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from specpilot import __version__
from specpilot.openapi import OpenAPIParser, SpecLoader, SpecPilotError

console = Console()
error_console = Console(stderr=True)


@click.group()
@click.version_option(version=__version__, prog_name="specpilot")
def cli() -> None:
    """SpecPilot: OpenAPI-driven API automation CLI."""
    pass


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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
