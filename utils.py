import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests

from config import get_github_token, get_api_key


def make_github_request(url: str, params: Optional[dict] = None) -> dict:
    """Make an authenticated GitHub API request with pagination support."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Repository-Analyst",
    }
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    all_results = []
    page = 1
    while True:
        paginated_params = dict(params) if params else {}
        paginated_params["page"] = page
        paginated_params["per_page"] = 100

        response = requests.get(url, headers=headers, params=paginated_params, timeout=30)

        if response.status_code == 403:
            rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "0")
            if rate_limit_remaining == "0":
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_time - time.time(), 0) + 1
                print(f"Rate limit hit. Waiting {wait:.0f}s...")
                time.sleep(wait)
                continue

        if response.status_code != 200:
            raise Exception(f"GitHub API error {response.status_code}: {response.text}")

        data = response.json()
        if isinstance(data, list):
            all_results.extend(data)
            if len(data) < 100:
                break
        else:
            return data

        link_header = response.headers.get("Link", "")
        if 'rel="next"' not in link_header:
            break
        page += 1

    return all_results


def get_repo_owner_repo(repo_input: str) -> tuple[str, str]:
    """Parse owner/repo from various input formats."""
    if "/" in repo_input:
        parts = repo_input.split("/", 1)
        owner = parts[0].strip()
        repo = parts[1].strip().rstrip("/")
        if owner and repo and "/" not in repo:
            return owner, repo
    raise ValueError(f"Invalid repo format: '{repo_input}'. Use 'owner/repo'.")


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def truncate_text(text: str, max_length: int = 5000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"\n... [truncated at {max_length} chars]"


def safe_license(data: dict) -> dict:
    return safe_get(data, "license", default={}) or {}


def safe_parent(data: dict) -> dict:
    return safe_get(data, "parent", default={}) or {}


def safe_get(data: dict, *keys, default=None):
    """Safely navigate nested dicts."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def classify_language(extension: str) -> str:
    lang_map = {
        "py": "Python", "js": "JavaScript", "ts": "TypeScript", "tsx": "TypeScript",
        "jsx": "JavaScript", "java": "Java", "cpp": "C++", "c": "C", "h": "C Header",
        "cs": "C#", "go": "Go", "rs": "Rust", "rb": "Ruby", "php": "PHP",
        "swift": "Swift", "kt": "Kotlin", "scala": "Scala", "r": "R",
        "sh": "Shell", "bash": "Shell", "zsh": "Shell", "yaml": "YAML",
        "yml": "YAML", "json": "JSON", "xml": "XML", "html": "HTML",
        "css": "CSS", "scss": "SCSS", "less": "LESS", "sql": "SQL",
        "md": "Markdown", "txt": "Text", "dockerfile": "Docker",
        "toml": "TOML", "ini": "INI", "cfg": "Config", "vue": "Vue",
        "svelte": "Svelte", "graphql": "GraphQL", "gql": "GraphQL",
        "proto": "Protocol Buffers", "dart": "Dart",
        "lua": "Lua", "ex": "Elixir", "exs": "Elixir", "erl": "Erlang",
        "hs": "Haskell", "ml": "OCaml", "clj": "Clojure", "edn": "EDN",
        "ps1": "PowerShell", "psm1": "PowerShell",
        "nb": "Jupyter Notebook", "ipynb": "Jupyter Notebook",
    }
    ext = extension.lower().lstrip(".")
    return lang_map.get(ext, "Unknown")


def get_tree_summary(tree_data: list, base_path: str = "") -> dict:
    """Recursively summarize a GitHub tree."""
    summary = {"files": [], "directories": {}, "total_files": 0, "total_dirs": 0}
    for item in tree_data:
        path = f"{base_path}/{item['path']}" if base_path else item["path"]
        if item["type"] == "tree":
            summary["directories"][item["path"]] = path
            summary["total_dirs"] += 1
        elif item["type"] == "blob":
            summary["files"].append({
                "name": item["path"],
                "path": path,
                "size": item.get("size", 0),
            })
            summary["total_files"] += 1
    return summary
