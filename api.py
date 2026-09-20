"""FastAPI backend for the standalone GitHub repository chatbot."""

import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents.github_agent import GitHubAgent
from agents.gemini_agent import GeminiAgent
from utils import get_repo_owner_repo, truncate_text


PROJECT_ROOT = Path(__file__).parent.resolve()
STATIC_DIR = PROJECT_ROOT / "web"

app = FastAPI(title="GitHub Repository Chatbot", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
REPOSITORY_CACHE_TTL_SECONDS = 600
repository_cache: dict[str, dict[str, Any]] = {}


class RepositoryRequest(BaseModel):
    repository: str = Field(min_length=3, max_length=200)


class ChatRequest(BaseModel):
    repository: str = Field(min_length=3, max_length=200)
    question: str = Field(min_length=1, max_length=10000)


def _load_repository(repository: str) -> dict[str, Any]:
    try:
        owner, repo = get_repo_owner_repo(repository)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cache_key = f"{owner}/{repo}".lower()
    cached = repository_cache.get(cache_key)
    if cached and time.time() - cached["loaded_at"] < REPOSITORY_CACHE_TTL_SECONDS:
        return cached["data"]

    github = GitHubAgent()
    try:
        repo_info = github.get_repo_metadata(owner, repo)
        languages = github.get_languages(owner, repo)
        tree = github.get_repo_tree(owner, repo, repo_info.get("default_branch", "main"))
        code_files = github.get_code_files(owner, repo, tree, max_files=30)
        package_files = github.get_package_files(owner, repo, tree)
        readme = github.get_readme(owner, repo, repo_info.get("default_branch", "main"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub request failed: {exc}") from exc

    context_parts = [
        f"Repository: {repo_info.get('full_name', repository)}",
        f"Description: {repo_info.get('description', 'N/A')}",
        f"Languages: {json.dumps(languages)}",
        "Repository files:\n" + "\n".join(
            item.get("path", "") for item in tree if item.get("type") == "blob"
        )[:12000],
    ]
    if readme:
        context_parts.append(f"FILE: README.md\n{truncate_text(readme, 12000)}")

    file_names = []
    for package_file in package_files:
        path = package_file["path"]
        file_names.append(path)
        context_parts.append(
            f"FILE: {path}\n{truncate_text(package_file.get('content', ''), 8000)}"
        )

    loaded_files = []
    for code_file in code_files[:15]:
        path = code_file["path"]
        content = github.get_file_content(
            owner, repo, path, repo_info.get("default_branch", "main")
        )
        if content and len(content) <= 100000:
            loaded_files.append(path)
            context_parts.append(f"FILE: {path}\n{truncate_text(content, 12000)}")

    data = {
        "repository": repo_info,
        "languages": languages,
        "file_count": sum(1 for item in tree if item.get("type") == "blob"),
        "loaded_files": loaded_files + file_names + (["README.md"] if readme else []),
        "context": "\n\n".join(context_parts),
    }
    repository_cache[cache_key] = {"loaded_at": time.time(), "data": data}
    return data


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/repository")
def repository(request: RepositoryRequest) -> dict[str, Any]:
    return _load_repository(request.repository)


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    repository_data = _load_repository(request.repository)
    try:
        answer = GeminiAgent().answer_question(
            context=repository_data["context"],
            question=request.question,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}") from exc
    return {"answer": answer}


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    repository_data = _load_repository(request.repository)

    def events():
        try:
            for chunk in GeminiAgent().stream_answer_question(
                context=repository_data["context"],
                question=request.question,
            ):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
