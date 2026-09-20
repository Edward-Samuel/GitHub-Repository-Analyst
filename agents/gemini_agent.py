import json
import os
import time
from typing import Any

import requests

from config import get_api_key, load_config
from utils import truncate_text


class GeminiAgent:
    """Agent responsible for AI-powered analysis using Google Gemini API."""

    def __init__(self):
        self.name = "Gemini Agent"
        self.role = "Provide AI-powered analysis and insights"
        self.api_key = get_api_key()
        config = load_config()
        self.primary_model = config.get("primary_model", "gemma-4-26b-a4b-it")
        self.fallback_model = config.get("fallback_model", "gemma-4-31b-it")
        self.models = list(dict.fromkeys([
            self.primary_model,
            self.fallback_model,
        ]))
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.max_tokens = 8192
        self.temperature = 0.3

    def _build_model_url(self, model_name: str) -> str:
        return f"{self.base_url}/{model_name}:generateContent"

    def _build_stream_url(self, model_name: str) -> str:
        return f"{self.base_url}/{model_name}:streamGenerateContent"

    def _call(self, prompt: str, system_instruction: str = None) -> str:
        """Call the configured model with fallback support."""
        params = {"key": self.api_key}
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        last_error = None
        for index, model_name in enumerate(self.models):
            url = self._build_model_url(model_name)
            try:
                response = requests.post(url, params=params, json=payload, timeout=120)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2))
                    print(f"Rate limited on {model_name}. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    if index < len(self.models) - 1:
                        continue
                    raise Exception(f"Gemini API rate limit exceeded for {model_name}: {response.text}")

                if response.status_code == 404:
                    if index < len(self.models) - 1:
                        print(
                            f"Model {model_name} is unavailable for this Gemini API. "
                            f"Trying {self.models[index + 1]}..."
                        )
                        continue
                    raise Exception(
                        f"None of the configured Gemini models are available. "
                        f"Last response: {response.text}"
                    )

                if response.status_code in {500, 502, 503, 504} and index < len(self.models) - 1:
                    print(f"Model {model_name} failed with {response.status_code}. Trying {self.models[index + 1]}...")
                    continue

                if response.status_code != 200:
                    if index < len(self.models) - 1:
                        print(f"Model {model_name} failed with {response.status_code}. Trying {self.models[index + 1]}...")
                        continue
                    raise Exception(f"Gemini API error {response.status_code}: {response.text}")

                data = response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    return str(data)
            except requests.RequestException as exc:
                last_error = exc
                if index < len(self.models) - 1:
                    print(f"Request failed for {model_name}. Trying fallback model {self.models[index + 1]}...")
                    continue
                raise

        if last_error:
            raise last_error
        raise Exception("Unable to generate a response from the configured model list.")

    def stream_answer_question(self, context: str, question: str):
        """Yield answer text as it arrives from the configured Gemini models."""
        prompt = f"""You are a repository-aware coding assistant. Answer the user's question
using only the repository context below. Cite relevant file paths when possible.
If the context does not contain enough information, say so clearly instead of guessing.

Repository context:
{context[:50000]}

User question: {question}

Give a direct, practical answer in Markdown. Include short code excerpts only when they
are present in the supplied context."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        params = {"key": self.api_key, "alt": "sse"}
        last_error = None

        for index, model_name in enumerate(self.models):
            try:
                response = requests.post(
                    self._build_stream_url(model_name),
                    params=params,
                    json=payload,
                    timeout=(30, 300),
                    stream=True,
                )
                if response.status_code != 200:
                    error = f"Gemini API error {response.status_code}: {response.text}"
                    if index < len(self.models) - 1 and response.status_code in {
                        404, 429, 500, 502, 503, 504
                    }:
                        print(f"Streaming model {model_name} failed. Trying {self.models[index + 1]}...")
                        continue
                    raise Exception(error)

                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = json.loads(line[5:].strip())
                    for candidate in data.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            text = part.get("text")
                            if text:
                                yield text
                return
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if index < len(self.models) - 1:
                    continue
                raise

        if last_error:
            raise last_error
        raise Exception("Unable to stream a response from the configured model list.")

    def analyze_repository(
        self,
        repo_info: dict,
        languages: dict = None,
        tree_summary: dict = None,
        commits: list = None,
        contributors: list = None,
        code_samples: dict = None,
        readme: str = None,
        package_files: list = None,
    ) -> str:
        """Comprehensive repository analysis using Gemini."""
        prompt = f"""You are an expert software engineer and code analyst. Analyze the following GitHub repository information and provide a comprehensive analysis.

## Repository Information
- **Name**: {repo_info.get('full_name', 'N/A')}
- **Description**: {repo_info.get('description', 'N/A')}
- **Language**: {repo_info.get('language', 'N/A')}
- **Stars**: {repo_info.get('stargazers_count', 0)}
- **Forks**: {repo_info.get('forks_count', 0)}
- **Open Issues**: {repo_info.get('open_issues_count', 0)}
- **License**: {repo_info.get('license', {}).get('name', 'N/A') if isinstance(repo_info.get('license'), dict) else 'N/A'}
- **Created**: {repo_info.get('created_at', 'N/A')}
- **Last Updated**: {repo_info.get('updated_at', 'N/A')}
- **Default Branch**: {repo_info.get('default_branch', 'N/A')}
- **Size**: {repo_info.get('size', 0)} KB
- **Visibility**: {repo_info.get('visibility', 'N/A')}
- **Topics**: {', '.join(repo_info.get('topics', [])) or 'N/A'}
- **Homepage**: {repo_info.get('homepage', 'N/A')}
- **Archived**: {repo_info.get('archived', False)}

## Language Breakdown"""
        if languages:
            total_lines = sum(languages.values())
            for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:15]:
                pct = (count / total_lines * 100) if total_lines > 0 else 0
                prompt += f"\n- **{lang}**: {count:,} lines ({pct:.1f}%)"

        prompt += f"""

## Repository Tree Summary
{json.dumps(tree_summary, indent=2) if tree_summary else 'N/A'}
"""
        if readme:
            prompt += f"\n## README Content (first 3000 chars)\n{truncate_text(readme, 3000)}\n"

        if package_files:
            prompt += "\n## Package/Manifest Files Found:\n"
            for pf in package_files:
                prompt += f"\n### {pf['path']}\n{truncate_text(pf['content'], 2000)}\n"

        if commits:
            prompt += "\n## Recent Commits:\n"
            for c in commits[:15]:
                msg = c.get("commit", {}).get("message", "").split("\n")[0][:100]
                author = c.get("commit", {}).get("author", {}).get("name", "Unknown")
                date = c.get("commit", {}).get("author", {}).get("date", "N/A")
                sha = c.get("sha", "")[:8]
                prompt += f"\n- `{sha}` {msg} ({author}, {date})"

        if contributors:
            prompt += "\n## Top Contributors:\n"
            for contrib in contributors[:10]:
                login = contrib.get("login", "Unknown")
                contributions = contrib.get("contributions", 0)
                prompt += f"\n- @{login}: {contributions} contributions"

        if code_samples:
            prompt += "\n## Code Samples for Analysis:\n"
            for path, sample in list(code_samples.items())[:5]:
                prompt += f"\n### {path}\n{truncate_text(sample, 2000)}\n"

        prompt += """

## Your Task

Provide a comprehensive analysis in the following sections:

### 1. Project Overview Summary
- What does this project do in 2-3 sentences?
- What is its purpose and primary use case?

### 2. Code Quality Assessment
- Overall code quality rating (1-10)
- Code organization and structure assessment
- Readability and maintainability observations
- Testing practices and coverage notes

### 3. Architecture Analysis
- Architecture patterns identified
- Key design decisions observed
- Module coupling and cohesion assessment
- Scalability considerations

### 4. Technology Stack Assessment
- Strengths and weaknesses of the chosen stack
- Technology compatibility and ecosystem assessment
- Dependencies and external library observations

### 5. Security Assessment
- Potential security concerns or patterns
- Authentication/authorization observations
- Data handling and privacy considerations
- Common vulnerability patterns to watch

### 6. Performance Considerations
- Performance-related observations
- Potential bottlenecks
- Optimization opportunities

### 7. Development Practices
- CI/CD observations
- Documentation quality
- Developer experience assessment
- Version control practices

### 8. Community and Maintenance
- Project health and activity indicators
- Maintainer responsiveness
- Issue/PR management practices
- Long-term sustainability assessment

### 9. Recommendations for Improvement
- Top 3-5 actionable recommendations
- Quick wins vs. long-term improvements
- Best practices to adopt

### 10. Risk Assessment
- Technical debt indicators
- Dependency risks
- Bus factor concerns
- Potential breaking change risks

Be specific, practical, and insightful. Reference specific evidence from the data provided. Use code/metric references where applicable. Format with markdown headers and bullet points.
"""
        return self._call(prompt)

    def analyze_code_snippet(self, code: str, language: str, question: str = "") -> str:
        """Analyze a specific code snippet."""
        prompt = f"""Analyze the following {language} code:

```{language}
{code}
```

{question if question else "Provide a thorough analysis covering: purpose, potential bugs, performance issues, security concerns, and improvement suggestions."}"""
        return self._call(prompt)

    def generate_summary(self, repo_info: dict, analysis_text: str) -> str:
        """Generate a concise executive summary."""
        prompt = f"""Based on this repository analysis, write a concise executive summary (150-200 words):

Repository: {repo_info.get('full_name', 'N/A')}
Description: {repo_info.get('description', 'N/A')}
Stars: {repo_info.get('stargazers_count', 0)} | Forks: {repo_info.get('forks_count', 0)}

Analysis:
{analysis_text[:10000]}"""
        return self._call(prompt)

    def answer_question(self, context: str, question: str) -> str:
        """Answer a specific question about a repository based on context."""
        prompt = f"""You are a repository-aware coding assistant. Answer the user's question
using only the repository context below. Cite relevant file paths when possible.
If the context does not contain enough information, say so clearly instead of guessing.

Repository context:

{context[:50000]}

User question: {question}

Give a direct, practical answer. Include short code excerpts only when they are present
in the supplied context."""
        return self._call(prompt)

    def compare_repositories(self, repo1_info: dict, repo1_analysis: str, repo2_info: dict, repo2_analysis: str) -> str:
        """Compare two repositories."""
        prompt = f"""Compare these two GitHub repositories:

## Repository A
- Name: {repo1_info.get('full_name', 'N/A')}
- Description: {repo1_info.get('description', 'N/A')}
- Stars: {repo1_info.get('stargazers_count', 0)}
- Language: {repo1_info.get('language', 'N/A')}

Analysis: {repo1_analysis[:5000]}

## Repository B
- Name: {repo2_info.get('full_name', 'N/A')}
- Description: {repo2_info.get('description', 'N/A')}
- Stars: {repo2_info.get('stargazers_count', 0)}
- Language: {repo2_info.get('language', 'N/A')}

Analysis: {repo2_analysis[:5000]}

Provide a detailed comparison covering architecture, code quality, community, and technology choices. Format as a comparison table where applicable."""
        return self._call(prompt)

    def security_scan(self, code_files_content: dict, repo_info: dict) -> str:
        """Security-focused analysis of code files."""
        combined = ""
        for path, content in list(code_files_content.items())[:10]:
            combined += f"\n### {path}\n{truncate_text(content, 3000)}\n"

        prompt = f"""You are a security expert. Scan the following code from the repository for security vulnerabilities and concerns:

Repository: {repo_info.get('full_name', 'N/A')}

Code:
{combined}

Look for:
1. SQL injection vulnerabilities
2. XSS vulnerabilities
3. Hardcoded secrets, API keys, passwords
4. Insecure authentication patterns
5. Unsafe deserialization
6. Path traversal risks
7. Command injection risks
8. Insecure cryptographic practices
9. Insufficient input validation
10. Insecure file handling

For each finding, provide: severity (Critical/High/Medium/Low), location, description, and recommended fix."""
        return self._call(prompt)
