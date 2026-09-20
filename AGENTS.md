# GitHub Repository Analyst - Agent Instructions

## Project Overview
Multi-agent system analyzing GitHub repositories using Gemini API, GitHub API, and code intelligence.

## Architecture

### Three Agents
1. **GitHub Agent** (`agents/github_agent.py`) - Fetches repo metadata, trees, files, commits, contributors via GitHub REST API
2. **Gemini Agent** (`agents/gemini_agent.py`) - AI-powered analysis via Google Gemini API (direct HTTP)
3. **Code Intelligence Agent** (`agents/code_agent.py`) - AST-based Python analysis, regex-based JS/TS/Go analysis, project structure analysis

### Key Modules
- `main.py` - CLI entry point with click; Rich console for output
- `config.py` - Config management (config.json + env vars)
- `utils.py` - Shared helpers (HTTP, parsing, classification)
- `ui.py` - Rich terminal UI components (tables, panels, headers)
- `demo.py` - Demonstration script showing all capabilities

## Agent Workflow
1. GitHub Agent fetches repo metadata, tree, languages, commits, contributors, package files
2. Code Intelligence Agent analyzes code files (AST for Python, regex for JS/TS/Go)
3. All data fed to Gemini Agent for comprehensive AI analysis report
4. Results displayed via Rich console, optionally saved to file

## Adding New Features
- **New analysis**: Add method to relevant agent, call from `run_analysis()` in `main.py`
- **New language support**: Add `analyze_*.py` method to `CodeIntelligenceAgent`
- **New CLI command**: Add `@cli.command()` in `main.py`

## Running
```bash
pip install -r requirements.txt
python main.py config          # Set API keys
python main.py analyze owner/repo [options]
python demo.py                 # Demo without API key
```

## API Keys
- Gemini API key: Required for AI features, set via `python main.py config` or `GEMINI_API_KEY` env var
- GitHub Token: Optional, higher rate limits, set via config or `GITHUB_TOKEN` env var

## Notes
- Without a GitHub token, unauthenticated API rate limit is ~60 req/hour
- Large repos (10k+ files) may timeout on tree fetch; use depth=shallow
- Gemini API has its own rate limits; default temp=0.3 for consistent output
