import base64
import time
from typing import Any, Optional

import requests

from config import get_api_key, get_github_token, load_config
from utils import make_github_request, get_repo_owner_repo, truncate_text, safe_license, safe_parent


class GitHubAgent:
    """Agent responsible for fetching repository data from GitHub API."""

    def __init__(self):
        self.name = "GitHub Agent"
        self.role = "Fetch and retrieve repository data from GitHub"
        self.gh_base = "https://api.github.com"
        config = load_config()
        self.primary_model = config.get("primary_model", "gemma-4-26b-a4b-it")
        self.fallback_model = config.get("fallback_model", "gemma-4-31b-it")
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.primary_model}:generateContent"

    def _gh_request(self, path: str, params: Optional[dict] = None) -> dict:
        return make_github_request(f"{self.gh_base}{path}", params)

    def _gh_raw_request(self, url: str, params: Optional[dict] = None) -> requests.Response:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Repository-Analyst",
        }
        token = get_github_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return requests.get(url, headers=headers, params=params, timeout=30)

    def get_repo_metadata(self, owner: str, repo: str) -> dict:
        """Fetch comprehensive repository metadata."""
        data = self._gh_request(f"/repos/{owner}/{repo}")
        return {
            "full_name": data.get("full_name", ""),
            "name": data.get("name", ""),
            "owner": data.get("owner", {}).get("login", ""),
            "description": data.get("description", ""),
            "url": data.get("html_url", ""),
            "clone_url": data.get("clone_url", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "pushed_at": data.get("pushed_at", ""),
            "stargazers_count": data.get("stargazers_count", 0),
            "watchers_count": data.get("watchers_count", 0),
            "forks_count": data.get("forks_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
            "language": data.get("language", "Unknown"),
            "topics": data.get("topics", []),
            "license": safe_license(data),
            "default_branch": data.get("default_branch", "main"),
            "size": data.get("size", 0),
            "archived": data.get("archived", False),
            "disabled": data.get("disabled", False),
            "has_issues": data.get("has_issues", False),
            "has_projects": data.get("has_projects", False),
            "has_wiki": data.get("has_wiki", False),
            "has_pages": data.get("has_pages", False),
            "has_downloads": data.get("has_downloads", False),
            "visibility": data.get("visibility", "unknown"),
            "homepage": data.get("homepage", ""),
            "network_count": data.get("network_count", 0),
            "subscribers_count": data.get("subscribers_count", 0),
            "parent": safe_parent(data),
            "fork": data.get("fork", False),
            "allow_squash_merge": data.get("allow_squash_merge"),
            "allow_merge_commit": data.get("allow_merge_commit"),
            "allow_rebase_merge": data.get("allow_rebase_merge"),
            "organization": data.get("organization"),
        }

    def get_languages(self, owner: str, repo: str) -> dict:
        """Get language breakdown for the repository."""
        return self._gh_request(f"/repos/{owner}/{repo}/languages")

    def get_repo_tree(self, owner: str, repo: str, branch: str = "main") -> list:
        """Get repository file tree recursively."""
        try:
            return self._gh_request(
                f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            ).get("tree", [])
        except Exception as e:
            print(f"Warning: Could not fetch tree: {e}")
            return []

    def get_file_content(self, owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
        """Fetch raw content of a file."""
        try:
            url = f"{self.gh_base}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            response = self._gh_raw_request(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("encoding") == "base64":
                    content = data.get("content", "")
                    content = content.replace("\n", "")
                    return base64.b64decode(content).decode("utf-8", errors="replace")
                return data.get("content", "")
        except Exception as e:
            print(f"Warning: Could not fetch {path}: {e}")
        return None

    def get_commits(self, owner: str, repo: str, per_page: int = 30) -> list:
        """Fetch recent commits."""
        return self._gh_request(
            f"/repos/{owner}/{repo}/commits", {"per_page": per_page}
        )

    def get_contributors(self, owner: str, repo: str, per_page: int = 50) -> list:
        """Fetch repository contributors."""
        return self._gh_request(
            f"/repos/{owner}/{repo}/contributors", {"per_page": per_page}
        )

    def get_tags(self, owner: str, repo: str) -> list:
        """Fetch repository tags/releases."""
        try:
            return self._gh_request(f"/repos/{owner}/{repo}/tags")
        except Exception:
            return []

    def get_releases(self, owner: str, repo: str) -> list:
        """Fetch releases."""
        try:
            return self._gh_request(f"/repos/{owner}/{repo}/releases")
        except Exception:
            return []

    def get_readme(self, owner: str, repo: str, branch: str = "main") -> Optional[str]:
        """Fetch README content."""
        return self.get_file_content(owner, repo, "README.md", branch)

    def get_package_files(self, owner: str, repo: str, tree: list) -> list:
        """Find and fetch package/manifest files."""
        package_names = [
            "package.json", "requirements.txt", "setup.py", "setup.cfg",
            "pyproject.toml", "Gemfile", "go.mod", "Cargo.toml",
            "pom.xml", "build.gradle", "composer.json", "build.sbt",
            "Makefile", "CMakeLists.txt", "tsconfig.json", ".editorconfig",
            "Dockerfile", "docker-compose.yml", ".env", ".env.example",
            "requirements-dev.txt", "Pipfile", "poetry.lock",
            "yarn.lock", "package-lock.json", "pnpm-lock.yaml",
            "tsconfig.json", "next.config.js", "next.config.mjs",
            "vite.config.ts", "webpack.config.js", ".babelrc",
            ".babelrc.js", ".babelrc.json",
        ]
        found_files = []
        for item in tree:
            if item.get("type") == "blob" and item.get("path", "").lower() in package_names:
                content = self.get_file_content(owner, repo, item["path"])
                if content:
                    found_files.append({"path": item["path"], "content": content})
        return found_files

    def get_code_files(self, owner: str, repo: str, tree: list, max_files: int = 50) -> list:
        """Get source code files from the tree."""
        code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c",
            ".h", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
            ".scala", ".r", ".sh", ".yaml", ".yml", ".json", ".xml",
            ".html", ".css", ".sql", ".vue", ".svelte", ".dart",
        }
        code_files = []
        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path", "")
                ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                if ext in code_extensions and "node_modules" not in path and ".git" not in path:
                    if item.get("size", 0) > 500000:
                        continue
                    code_files.append({
                        "path": path,
                        "size": item.get("size", 0),
                        "extension": ext,
                    })
                    if len(code_files) >= max_files:
                        break
        return code_files

    def get_workflows(self, owner: str, repo: str) -> list:
        """Fetch GitHub Actions workflows."""
        try:
            return self._gh_request(f"/repos/{owner}/{repo}/actions/workflows")
        except Exception:
            return []

    def get_issues(self, owner: str, repo: str, state: str = "open", per_page: int = 20) -> list:
        """Fetch issues."""
        try:
            return self._gh_request(
                f"/repos/{owner}/{repo}/issues",
                {"state": state, "per_page": per_page},
            )
        except Exception:
            return []

    def search_code(self, owner: str, repo: str, query: str) -> list:
        """Search within a repository."""
        try:
            results = self._gh_request(
                f"/code/search", {"q": f"repo:{owner}/{repo} {query}"}
            )
            return results.get("items", [])
        except Exception:
            return []
