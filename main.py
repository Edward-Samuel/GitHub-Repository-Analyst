"""
GitHub Repository Analyst - Main Entry Point

A multi-agent system that analyzes GitHub repositories using:
- GitHub Agent: Fetches repository data via GitHub API
- Code Intelligence Agent: Analyzes code structure and complexity
- Gemini Agent: Provides AI-powered insights and analysis

Usage:
    python main.py analyze <owner/repo> [options]
    python main.py config
    python main.py compare <owner/repo1> <owner/repo2>
"""

import json
import os
import sys
from typing import Optional

import click
from rich.console import Console

from config import load_config, configure, get_api_key, get_github_token
from agents.github_agent import GitHubAgent
from agents.gemini_agent import GeminiAgent
from agents.code_agent import CodeIntelligenceAgent
from ui import (
    print_header, print_section, print_repo_info, print_languages,
    print_analysis_report, print_json, prompt_yes_no
)
from utils import (
    get_repo_owner_repo, truncate_text,
)


def run_analysis(repo_input: str, depth: str = "medium", report_format: str = "markdown",
                 insights: bool = False, security: bool = False, output: Optional[str] = None,
                 verbose: bool = False):
    """Run the full analysis pipeline."""

    console = Console()
    click.echo()
    print_header("GitHub Repository Analyst", console)
    click.echo()

    config = load_config()
    if not config.get("gemini_api_key") and not os.environ.get("GEMINI_API_KEY"):
        click.echo("[red]Error: Gemini API key not configured.[/red]")
        click.echo("Run `python main.py config` to set it up, or export GEMINI_API_KEY env var.")
        sys.exit(1)

    try:
        owner, repo = get_repo_owner_repo(repo_input)
    except ValueError as e:
        click.echo("[red]Error: {}[/red]".format(e))
        sys.exit(1)

    click.echo("[bold]Analyzing:[/bold] [cyan]{}/{}[/cyan]".format(owner, repo))
    click.echo("[dim]Depth: {} | Format: {}[/dim]".format(depth, report_format))
    click.echo()

    github_agent = GitHubAgent()
    gemini_agent = GeminiAgent()
    code_agent = CodeIntelligenceAgent()

    click.echo("[bold]Step 1/6:[/bold] [cyan]GitHub Agent[/cyan] - Fetching repository metadata...")
    repo_info = github_agent.get_repo_metadata(owner, repo)
    languages = github_agent.get_languages(owner, repo)

    click.echo("[bold]Step 2/6:[/bold] [cyan]GitHub Agent[/cyan] - Fetching repository tree...")
    tree = github_agent.get_repo_tree(owner, repo)
    tree_summary = {
        "total_files": sum(1 for item in tree if item.get("type") == "blob"),
        "total_dirs": sum(1 for item in tree if item.get("type") == "tree"),
        "files": [{"path": f["path"], "size": f.get("size", 0)} for f in tree if f.get("type") == "blob"][:50],
    }

    click.echo("[bold]Step 3/6:[/bold] [green]Code Intelligence Agent[/green] - Analyzing project structure...")
    structure = code_agent.analyze_project_structure(tree_summary, languages)

    click.echo("[bold]Step 4/6:[/bold] [green]Code Intelligence Agent[/green] - Analyzing code files...")
    code_files = github_agent.get_code_files(owner, repo, tree, max_files=30)
    code_analyses = []
    code_files_content = {}
    for cf in code_files[:10]:
        content = github_agent.get_file_content(owner, repo, cf["path"])
        if content and len(content) < 100000:
            analysis = code_agent.analyze_file(content, cf["path"])
            code_analyses.append(analysis)
            code_files_content[cf["path"]] = content

    click.echo("[bold]Step 5/6:[/bold] [green]Code Intelligence Agent[/green] - Analyzing dependencies...")
    package_files = github_agent.get_package_files(owner, repo, tree)
    deps = code_agent.analyze_dependencies(package_files)
    complexity = code_agent.estimate_complexity(code_analyses)

    click.echo("[bold]Step 6/6:[/bold] [yellow]Gemini Agent[/yellow] - Running AI analysis...")
    commits = github_agent.get_commits(owner, repo, per_page=20)
    contributors = github_agent.get_contributors(owner, repo, per_page=20)
    readme = github_agent.get_readme(owner, repo)

    analysis_text = gemini_agent.analyze_repository(
        repo_info=repo_info,
        languages=languages,
        tree_summary=tree_summary,
        commits=commits,
        contributors=contributors,
        code_samples={k: truncate_text(v, 2000) for k, v in code_files_content.items()},
        readme=readme,
        package_files=[{"path": pf["path"], "content": truncate_text(pf.get("content", ""), 2000)} for pf in package_files],
    )

    print_section("Repository Overview", console)
    print_repo_info(repo_info, console)

    print_section("Language Breakdown", console)
    print_languages(languages, console)

    if insights:
        print_section("AI Insights Summary", console)
        summary = gemini_agent.generate_summary(repo_info, analysis_text)
        console.print(summary)

    if security:
        print_section("Security Scan", console)
        security_result = gemini_agent.security_scan(code_files_content, repo_info)
        console.print(security_result)

    print_section("Code Analysis Summary", console)
    summary_data = {
        "project_structure": structure,
        "complexity": complexity,
        "dependencies": {"total": deps["total"], "frameworks": deps["frameworks"]},
        "files_analyzed": len(code_analyses),
    }
    print_json(summary_data, console)

    print_section("Full AI Analysis Report", console)
    print_analysis_report(analysis_text, console)

    if output:
        save_output(report_format, analysis_text, repo_info, output, console)

    click.echo()
    click.echo("[bold green]Analysis complete![/bold green]")
    click.echo("[dim]Analyzed {} code files across {} total files.[/dim]".format(
        len(code_analyses), tree_summary.get('total_files', 0)))

    return {
        "repo_info": repo_info,
        "languages": languages,
        "analysis": analysis_text,
        "structure": structure,
        "complexity": complexity,
        "dependencies": deps,
    }


def save_output(format: str, analysis: str, repo_info: dict, output_path: str, console: Console):
    """Save analysis to file."""
    with open(output_path, "w", encoding="utf-8") as f:
        if format == "json":
            data = {
                "repository": repo_info.get("full_name"),
                "analysis": analysis,
            }
            json.dump(data, f, indent=2, default=str)
        else:
            f.write("# GitHub Repository Analysis Report\n")
            f.write("## {}\n\n".format(repo_info.get('full_name', 'N/A')))
            f.write(analysis)
    console.print("\n[green]Report saved to: {}[/green]".format(output_path))


def run_compare(repo1: str, repo2: str):
    """Compare two repositories."""
    console = Console()
    click.echo("[bold]Comparing two repositories...[/bold]")

    github = GitHubAgent()
    gemini = GeminiAgent()

    click.echo("Fetching data for {}...".format(repo1))
    info1 = github.get_repo_metadata(*repo1.split("/"))
    click.echo("Fetching data for {}...".format(repo2))
    info2 = github.get_repo_metadata(*repo2.split("/"))

    click.echo("Running AI comparison...")
    comparison = gemini.compare_repositories(info1, "", info2, "")
    console.print(comparison)


@click.group()
def cli():
    """GitHub Repository Analyst - AI-powered repository analysis tool."""
    pass


@cli.command()
@click.argument("repo_input")
@click.option("--depth", "-d", default="medium", type=click.Choice(["shallow", "medium", "deep"]),
              help="Analysis depth (shallow, medium, deep)")
@click.option("--report", "-r", default="markdown", type=click.Choice(["markdown", "json"]),
              help="Report format")
@click.option("--insights", "-i", is_flag=True, help="Show AI insights summary")
@click.option("--security", "-s", is_flag=True, help="Run security scan")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def analyze(repo_input, depth, report, insights, security, output, verbose):
    """Analyze a GitHub repository (owner/repo)."""
    run_analysis(repo_input, depth=depth, report_format=report,
                 insights=insights, security=security, output=output, verbose=verbose)


@cli.command()
@click.argument("repo1")
@click.argument("repo2")
def compare(repo1, repo2):
    """Compare two GitHub repositories."""
    run_compare(repo1, repo2)


@cli.command()
def config():
    """Configure API keys."""
    configure()


@cli.command()
@click.argument("file")
def batch(file):
    """Analyze multiple repositories from a file (one repo per line)."""
    console = Console()
    with open(file, "r") as f:
        repos = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    click.echo("Found {} repositories to analyze".format(len(repos)))
    results = []
    for repo in repos:
        click.echo()
        click.echo("{}".format("=" * 60))
        click.echo("Analyzing: {}".format(repo))
        try:
            result = run_analysis(repo)
            results.append({"repo": repo, "status": "success"})
        except Exception as e:
            click.echo("[red]Error analyzing {}: {}[/red]".format(repo, e))
            results.append({"repo": repo, "status": "error", "error": str(e)})

    click.echo()
    click.echo("[bold]Batch Analysis Summary:[/bold]")
    for r in results:
        status = "[green]\u2713[/green]" if r["status"] == "success" else "[red]\u2717[/green]"
        click.echo("  {} {}".format(status, r["repo"]))


if __name__ == "__main__":
    cli()
