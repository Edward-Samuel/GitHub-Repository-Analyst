import os
import sys
import json
import platform
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn


def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 120


def print_header(text: str, console: Console):
    console.print(Panel(f"[bold cyan]{text}[/bold cyan]", style="bold blue", width=get_terminal_width()))


def print_section(text: str, console: Console):
    console.print(f"\n[bold magenta]{'=' * 40}[/bold magenta]")
    console.print(f"[bold yellow]{text}[/bold yellow]")
    console.print(f"[bold magenta]{'=' * 40}[/bold magenta][/bold magenta]")


def print_repo_info(repo_info: dict, console: Console):
    table = Table(title=f" Repository: {repo_info.get('full_name', 'N/A')} ", show_header=False)
    table.add_column("Property", style="cyan", width=25)
    table.add_column("Value", style="white")

    def add_row(prop, val):
        table.add_row(prop, str(val) if val is not None else "N/A")

    add_row("Description", repo_info.get("description", "N/A"))
    add_row("Language", repo_info.get("language", "N/A"))
    add_row("Stars", f"[yellow]{repo_info.get('stargazers_count', 0):,}[/yellow]")
    add_row("Forks", f"[green]{repo_info.get('forks_count', 0):,}[/green]")
    add_row("Open Issues", f"[red]{repo_info.get('open_issues_count', 0):,}[/red]")
    add_row("License", repo_info.get("license", {}).get("name", "N/A") if isinstance(repo_info.get("license"), dict) else "N/A")
    add_row("Created", repo_info.get("created_at", "N/A")[:10] if repo_info.get("created_at") else "N/A")
    add_row("Updated", repo_info.get("updated_at", "N/A")[:10] if repo_info.get("updated_at") else "N/A")
    add_row("Default Branch", repo_info.get("default_branch", "N/A"))
    add_row("Size", f"{repo_info.get('size', 0):,} KB")
    add_row("Visibility", repo_info.get("visibility", "N/A"))
    add_row("Topics", ", ".join(repo_info.get("topics", [])[:10]) or "N/A")
    add_row("Homepage", repo_info.get("homepage", "N/A"))
    add_row("Archived", str(repo_info.get("archived", False)))
    add_row("Fork", str(repo_info.get("fork", False)))
    add_row("URL", repo_info.get("url", "N/A"))

    console.print(table)


def print_languages(languages: dict, console: Console):
    if not languages:
        console.print("[dim]No language data available.[/dim]")
        return

    table = Table(title=" Language Breakdown ", show_header=False)
    table.add_column("Language", style="cyan")
    table.add_column("Lines", justify="right", style="white")
    table.add_column("Percentage", justify="right", style="green")

    total = sum(languages.values())
    for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:15]:
        pct = count / total * 100 if total > 0 else 0
        bar = f"[{'█' * int(pct / 3):green}]"
        table.add_row(lang, f"{count:,}", f"{pct:.1f}%")

    console.print(table)


def print_analysis_report(analysis_text: str, console: Console):
    console.print(f"\n[bold green]Analysis Report:[/bold green]")
    console.print(analysis_text)


def print_json(data: dict, console: Console):
    console.print(json.dumps(data, indent=2, default=str))


def prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        try:
            response = input(question + suffix).strip().lower()
            if not response:
                return default
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return default


def prompt_choice(question: str, choices: list[str]) -> str:
    while True:
        try:
            response = input(question + " " + " / ".join(choices) + " ").strip().lower()
            if response in [c.lower() for c in choices]:
                return response
            print(f"Invalid choice. Please choose from: {', '.join(choices)}")
        except (EOFError, KeyboardInterrupt):
            return choices[0]
