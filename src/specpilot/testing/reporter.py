import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from specpilot.testing.models import TestRunReport, TestStatus


class TestReporter:
    """Formats and exports API contract testing results."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def print_report(self, report: TestRunReport) -> None:
        """Render human-readable rich test execution report."""
        c = self.console
        c.print()
        c.print(
            Panel(
                f"[bold cyan]API Contract Test Report[/bold cyan]\n"
                f"[dim]API:[/dim] [bold]{report.api_title}[/bold] ({report.api_version})\n"
                f"[dim]Target Base URL:[/dim] [underline]{report.target_base_url}[/underline]\n"
                f"[dim]Duration:[/dim] {report.duration_ms:.2f}ms | [dim]Timestamp:[/dim] {report.timestamp}",
                expand=False,
            )
        )

        # Summary Table
        table = Table(title="Test Execution Summary", expand=True)
        table.add_column("Total", justify="right", style="cyan")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="bold red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Pass Rate", justify="right", style="bold magenta")

        pass_rate = (report.passed_count / report.total_scenarios * 100.0) if report.total_scenarios > 0 else 0.0
        table.add_row(
            str(report.total_scenarios),
            str(report.passed_count),
            str(report.failed_count),
            str(report.skipped_count),
            f"{pass_rate:.1f}%",
        )
        c.print(table)
        c.print()

        # Detailed Scenarios Breakdown
        c.print("[bold]Scenario Results:[/bold]")
        for res in report.results:
            sc = res.scenario
            op_label = f"{sc.method.upper():<6} {sc.path}"
            
            if res.status == TestStatus.PASSED:
                status_tag = "[bold green]PASS[/bold green]"
            elif res.status == TestStatus.SKIPPED:
                status_tag = "[bold yellow]SKIP[/bold yellow]"
            else:
                status_tag = "[bold red]FAIL[/bold red]"

            c.print(f"  {status_tag} {op_label:<35} [dim]{sc.description}[/dim] ({res.duration_ms:.1f}ms)")

        # Detailed Failure Panels
        failures = [r for r in report.results if r.status in (TestStatus.FAILED, TestStatus.ERROR)]
        if failures:
            c.print()
            c.print(f"[bold red]Contract Mismatches & Failures ({len(failures)}):[/bold red]")
            for f in failures:
                sc = f.scenario
                panel_content = (
                    f"[bold]Operation:[/bold] {sc.method.upper()} {sc.path}\n"
                    f"[bold]Scenario:[/bold] {sc.description} ({sc.scenario_type.value})\n"
                    f"[bold]Expected Status:[/bold] {sc.expectation.expected_status_codes}\n"
                    f"[bold]Actual Status:[/bold] {f.actual_status_code or 'N/A'}\n"
                    f"[bold]Failure Category:[/bold] {f.failure_category.value}\n"
                    f"[bold]Validation Errors:[/bold]\n"
                )
                for err in f.validation_errors:
                    panel_content += f"  - [red]{err}[/red]\n"

                c.print(Panel(panel_content, border_style="red", expand=False))

    def export_json(self, report: TestRunReport, file_path: str) -> None:
        """Export test run report to JSON file."""
        report_data = report.model_dump()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
