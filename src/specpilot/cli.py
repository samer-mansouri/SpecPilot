import click
from specpilot import __version__


@click.group()
@click.version_option(version=__version__, prog_name="specpilot")
def cli() -> None:
    """SpecPilot: OpenAPI-driven API automation CLI."""
    pass


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
