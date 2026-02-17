"""openlab init -- create database tables."""

import typer
from rich.console import Console

from openlab.db import get_engine, Base

console = Console()


def init_cmd():
    """Initialize the database (create all tables)."""
    console.print("[bold]Creating database tables...[/bold]")
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        console.print("[green]Database tables created successfully.[/green]")
    except Exception as exc:
        console.print(f"[red]Error creating tables: {exc}[/red]")
        raise typer.Exit(code=1)
