"""
Demo script showing all capabilities of GitHub Repository Analyst.
Run this to see the system in action without needing real API keys.
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from agents.code_agent import CodeIntelligenceAgent
from agents.github_agent import GitHubAgent
from utils import get_repo_owner_repo, classify_language


def demo_code_intelligence():
    print("=" * 60)
    print("DEMO: Code Intelligence Agent")
    print("=" * 60)

    agent = CodeIntelligenceAgent()

    python_code = '''
import os
import sys
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class User:
    name: str
    email: str
    age: int

    def is_adult(self) -> bool:
        return self.age >= 18

class Database:
    def __init__(self, connection_string: str):
        self.conn = connection_string
        self.cache = {}

    def get_user(self, user_id: int) -> Optional[User]:
        if user_id in self.cache:
            return self.cache[user_id]

        query = f"SELECT * FROM users WHERE id = {user_id}"
        result = self.execute_query(query)

        if result:
            user = User(
                name=result["name"],
                email=result["email"],
                age=result["age"]
            )
            self.cache[user_id] = user
            return user
        return None

    def execute_query(self, query: str):
        print(f"Executing: {query}")
        return None

def process_users(user_ids: List[int]) -> List[User]:
    db = Database("postgresql://localhost/mydb")
    users = []
    for uid in user_ids:
        user = db.get_user(uid)
        if user and user.is_adult():
            users.append(user)
    return users
'''

    result = agent.analyze_python_file(python_code, "database.py")

    print("\nFile: database.py")
    print("Lines of Code: {}".format(result["lines_of_code"]))
    print("Blank Lines: {}".format(result["blank_lines"]))
    print("Comments: {}".format(result["comments"]))
    print("Cyclomatic Complexity: {}".format(result["complexity"]))
    print("Functions Found: {}".format(len(result["functions"])))
    for func in result["functions"]:
        print("  - {} (line {}, complexity: {}, docstring: {})".format(
            func["name"], func["line"], func["complexity"], func["docstring"]))
    print("Classes Found: {}".format(len(result["classes"])))
    for cls in result["classes"]:
        print("  - {} (line {}, methods: {})".format(
            cls["name"], cls["line"], cls["methods"]))
    print("Imports: {}".format(result["imports"]))

    return result


def demo_js_analysis():
    print("\n" + "=" * 60)
    print("DEMO: JavaScript Analysis")
    print("=" * 60)

    agent = CodeIntelligenceAgent()

    js_code = '''
const express = require("express");
const cors = require("cors");
const app = express();

app.use(cors());
app.use(express.json());

const authenticate = (req, res, next) => {
    const token = req.headers["authorization"];
    if (!token) {
        return res.status(401).json({ error: "No token" });
    }
    next();
};

app.get("/api/users", authenticate, (req, res) => {
    const users = getUsersFromDB();
    res.json(users);
});

app.post("/api/users", authenticate, (req, res) => {
    const { name, email } = req.body;
    if (!name || !email) {
        return res.status(400).json({ error: "Missing fields" });
    }
    const user = createUser(name, email);
    res.status(201).json(user);
});

function getUsersFromDB() {
    return [];
}

function createUser(name, email) {
    return { id: Date.now(), name, email };
}

app.listen(3000, () => {
    console.log("Server running on port 3000");
});
'''

    result = agent.analyze_javascript_file(js_code, "server.js")

    print("\nFile: server.js")
    print("Lines of Code: {}".format(result["lines_of_code"]))
    print("Comments: {}".format(result["comments"]))
    print("Blank Lines: {}".format(result["blank_lines"]))
    print("Cyclomatic Complexity: {}".format(result["complexity"]))
    print("Functions Found: {}".format(len(result["functions"])))
    for func in result["functions"]:
        print("  - {}".format(func["name"]))
    print("Imports: {}".format(result["imports"]))
    print("Issues: {}".format(result["issues"] if result["issues"] else "None detected"))

    return result


def demo_structure_analysis():
    print("\n" + "=" * 60)
    print("DEMO: Project Structure Analysis")
    print("=" * 60)

    agent = CodeIntelligenceAgent()

    tree_summary = {
        "total_files": 250,
        "total_dirs": 15,
        "files": [
            {"path": "src/components/Header.tsx", "size": 2048},
            {"path": "src/pages/Home.tsx", "size": 4096},
            {"path": "src/utils/api.ts", "size": 1024},
            {"path": "tests/unit/api.test.ts", "size": 512},
            {"path": "tests/integration/auth.test.ts", "size": 768},
            {"path": "package.json", "size": 1200},
            {"path": "tsconfig.json", "size": 300},
            {"path": "README.md", "size": 5000},
            {"path": ".github/workflows/ci.yml", "size": 800},
            {"path": "Dockerfile", "size": 400},
        ]
    }

    languages = {
        "TypeScript": 45000,
        "TypeScript React": 12000,
        "JavaScript": 8000,
        "CSS": 5000,
        "JSON": 2000,
        "Markdown": 3000,
        "YAML": 500,
        "Shell": 800,
    }

    structure = agent.analyze_project_structure(tree_summary, languages)

    print("\nStructure Type: {}".format(structure["structure_type"]))
    print("Total Files: {}".format(structure["total_files"]))
    print("Total Directories: {}".format(structure["total_directories"]))
    print("Has Tests: {}".format(structure["has_tests"]))
    print("Has CI/CD: {}".format(structure["has_ci_cd"]))
    print("Has License: {}".format(structure["has_license"]))
    print("Has README: {}".format(structure["has_readme"]))
    print("Root Directories: {}".format(structure["root_directories"]))
    print("File Extensions: {}".format(structure["file_extensions"]))

    return structure


def demo_complexity():
    print("\n" + "=" * 60)
    print("DEMO: Complexity Estimation")
    print("=" * 60)

    agent = CodeIntelligenceAgent()

    analyses = [
        {"complexity": 3, "file": "src/utils.ts", "functions": [{"name": "formatDate"}, {"name": "parseUrl"}], "classes": [], "imports": ["moment"]},
        {"complexity": 7, "file": "src/api.ts", "functions": [{"name": "fetchData"}, {"name": "handleResponse"}], "classes": [], "imports": ["axios", "lodash"]},
        {"complexity": 15, "file": "src/database.ts", "functions": [{"name": "query"}, {"name": "migrate"}], "classes": [{"name": "DatabaseManager"}], "imports": ["pg", "uuid"]},
        {"complexity": 22, "file": "src/router.ts", "functions": [{"name": "handleRequest"}, {"name": "route"}], "classes": [], "imports": ["express", "passport"]},
    ]

    result = agent.estimate_complexity(analyses)

    print("\nAverage Complexity: {}".format(result["average_complexity"]))
    print("Max Complexity: {}".format(result["max_complexity"]))
    print("High Complexity Files (>10): {}".format(result["high_complexity_files"]))
    print("Total Functions: {}".format(result["total_functions"]))
    print("Total Classes: {}".format(result["total_classes"]))

    return result


def demo_gemini_agent():
    print("\n" + "=" * 60)
    print("DEMO: Gemini Agent (API Structure)")
    print("=" * 60)

    os.environ["GEMINI_API_KEY"] = "demo_key"
    from agents.gemini_agent import GeminiAgent

    agent = GeminiAgent()

    print("\nAgent Name: {}".format(agent.name))
    print("Agent Role: {}".format(agent.role))
    print("API URL: {}".format(agent.url))
    print("Max Tokens: {}".format(agent.max_tokens))
    print("Temperature: {}".format(agent.temperature))
    print("\nAvailable Methods:")
    methods = [m for m in dir(agent) if not m.startswith("_")]
    for m in methods:
        print("  - {}".format(m))

    return agent


def demo_github_agent():
    print("\n" + "=" * 60)
    print("DEMO: GitHub Agent (API Structure)")
    print("=" * 60)

    agent = GitHubAgent()

    print("\nAgent Name: {}".format(agent.name))
    print("Agent Role: {}".format(agent.role))
    print("\nAvailable Methods:")
    methods = [m for m in dir(agent) if not m.startswith("_")]
    for m in methods:
        print("  - {}".format(m))

    return agent


def demo_repo_parsing():
    print("\n" + "=" * 60)
    print("DEMO: Repository Parsing")
    print("=" * 60)

    test_cases = [
        "fastapi/fastapi",
        "facebook/react",
        "microsoft/vscode",
        "torvalds/linux",
    ]

    for repo in test_cases:
        try:
            owner, name = get_repo_owner_repo(repo)
            print("  {} -> owner: {}, repo: {}".format(repo, owner, name))
        except ValueError as e:
            print("  {} -> ERROR: {}".format(repo, e))

    bad_cases = ["invalid", "no/slash/here"]
    for repo in bad_cases:
        try:
            get_repo_owner_repo(repo)
            print("  {} -> UNEXPECTED SUCCESS".format(repo))
        except ValueError:
            print("  {} -> CORRECTLY REJECTED".format(repo))


def demo_classification():
    print("\n" + "=" * 60)
    print("DEMO: Language Classification")
    print("=" * 60)

    extensions = [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".rb", ".html", ".css", ".yaml", ".md", ".unknown"]
    for ext in extensions:
        lang = classify_language(ext)
        print("  {} -> {}".format(ext, lang))


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("GitHub Repository Analyst - Demo")
    print("#" * 60)

    demo_github_agent()
    demo_gemini_agent()
    demo_repo_parsing()
    demo_classification()
    demo_code_intelligence()
    demo_js_analysis()
    demo_structure_analysis()
    demo_complexity()

    print("\n" + "#" * 60)
    print("All demos completed successfully!")
    print("#" * 60)
