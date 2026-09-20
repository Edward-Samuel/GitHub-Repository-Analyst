# GitHub Repository Analyst

An AI-powered tool that analyzes GitHub repositories using LLM Agents (Gemini), GitHub API, and code intelligence.

## Features

- **Repository Overview** - Metadata, language breakdown, stats
- **Code Intelligence** - Cyclomatic complexity, dependency analysis, code patterns
- **AI Insights** - Gemini-powered analysis, recommendations, and risk assessment
- **Security Analysis** - Vulnerability patterns, hardcoded secrets detection
- **Architecture Assessment** - Design pattern recognition, coupling analysis
- **Report Generation** - Comprehensive analysis report

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

You have three ways to set your Gemini API key (any one is sufficient):

**Option A: Interactive setup**
```bash
python main.py config
```

**Option B: `.env` file** (copy template first)
```bash
cp .env.example .env
# Edit .env and add your key: GEMINI_API_KEY=your_key_here
```

**Option C: Environment variable**
```bash
export GEMINI_API_KEY=your_key_here
```

Optionally, set a GitHub Token for higher rate limits (default is 60 req/hour, with token it's 5000):
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

By default, the agent prefers Gemma 4 26B and falls back to Gemma 4 31B if the primary model is unavailable or rate-limited:
```bash
export PRIMARY_MODEL=gemma-4-26b-a4b-it
export FALLBACK_MODEL=gemma-4-31b-it
```

### 3. Run Analysis

#### Terminal UI

```bash
python main.py analyze owner/repo
python main.py analyze owner/repo --depth deep
python main.py analyze owner/repo --insights --security
```

#### Web UI (Streamlit)

**First time setup** (one-time):
```bash
python setup.bat        # Windows
bash setup.sh           # Mac/Linux
```

Then launch:
```bash
run_ui.bat              # Windows
./run_ui.sh             # Mac/Linux
```

Or directly:
```bash
venv\Scripts\streamlit run app.py    # Windows
./venv/bin/streamlit run app.py       # Mac/Linux
```

Requires `GEMINI_API_KEY` (env var, `.env` file, or sidebar input).
Opens at http://localhost:8501. Features: tabbed results, progress bar, example repos, one-click re-run.

#### Standalone FastAPI Chat UI

The repository chatbot is also available as a separate browser UI without Streamlit:

```bash
pip install -r requirements.txt
run_fastapi.bat                         # Windows
python -m uvicorn api:app --reload      # Mac/Linux
```

Open http://localhost:8000, enter an `owner/repo`, and ask questions grounded in the
repository's README, manifests, tree, and fetched source files.

#### Render + Vercel

Deploy the FastAPI backend on Render using the included `render.yaml` Blueprint:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn api:app --host 0.0.0.0 --port $PORT
```

In Render, choose **New + → Blueprint**, connect the repository, and select
`render.yaml`. Add the secret values for these environment variables when prompted:

```text
GEMINI_API_KEY=your_key
GITHUB_TOKEN=optional_token
PRIMARY_MODEL=gemma-4-26b-a4b-it
FALLBACK_MODEL=gemma-4-31b-it
```

Deploy the `web` directory to Vercel as a static frontend. Update the frontend API
base URL to the deployed Render URL, or configure a Vercel rewrite/proxy so
`/api/chat/stream`, `/api/chat`, and `/api/repository` forward to Render.

#### Demo (No API Key)

```bash
python demo.py
```

## Usage

```
python main.py [COMMAND] [ARGS]

Commands:
  analyze <repo>   Analyze a GitHub repository
  config           Configure API keys
  compare <r1> <r2> Compare two repositories
  batch <file>     Analyze repos listed in a file
```

## Examples

```bash
# Basic analysis
python main.py analyze microsoft/vscode

# Deep analysis with all agents
python main.py analyze facebook/react --depth deep

# Get AI insights
python main.py analyze vercel/next.js --insights

# Export report
python main.py analyze rust-lang/rust --report html -o report.html
```
