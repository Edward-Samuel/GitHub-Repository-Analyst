import ast
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


JS_KEYWORDS = {
    "if", "else", "while", "for", "catch", "switch", "class",
    "return", "export", "import", "await", "function", "const",
    "let", "var", "typeof", "instanceof", "new", "this", "try",
    "finally", "throw", "extends", "super", "yield", "void",
    "type", "interface", "enum", "namespace", "declare", "module",
}


class CodeIntelligenceAgent:
    """Agent responsible for deep code analysis and intelligence."""

    def __init__(self):
        self.name = "Code Intelligence Agent"
        self.role = "Analyze code structure, complexity, and patterns"

    def analyze_python_file(self, content: str, filepath: str) -> dict:
        """Analyze a Python file using AST."""
        result = {
            "file": filepath,
            "language": "Python",
            "functions": [],
            "classes": [],
            "imports": [],
            "lines_of_code": 0,
            "comments": 0,
            "blank_lines": 0,
            "complexity": 0,
            "issues": [],
        }

        lines = content.split("\n")
        result["lines_of_code"] = len(lines)
        result["blank_lines"] = sum(1 for line in lines if not line.strip())
        result["comments"] = sum(1 for line in lines if line.strip().startswith("#"))

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            result["issues"].append(f"Syntax error: {e}")
            return result

        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        result["complexity"] = complexity

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [
                        self._decorator_name(d) for d in node.decorator_list
                    ],
                    "complexity": self._function_complexity(node),
                    "docstring": ast.get_docstring(node) is not None,
                    "returns": False,
                }
                result["functions"].append(func_info)

            elif isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [],
                    "bases": [self._expr_name(b) for b in node.bases],
                    "docstring": ast.get_docstring(node) is not None,
                }
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_info["methods"].append(item.name)
                result["classes"].append(class_info)

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                else:
                    for alias in node.names:
                        result["imports"].append(node.module + "." + alias.name if node.module else alias.name)

        return result

    def analyze_javascript_file(self, content: str, filepath: str) -> dict:
        """Analyze a JavaScript/TypeScript file."""
        result = {
            "file": filepath,
            "language": "JavaScript",
            "functions": [],
            "classes": [],
            "imports": [],
            "lines_of_code": 0,
            "comments": 0,
            "blank_lines": 0,
            "complexity": 1,
            "issues": [],
        }

        lines = content.split("\n")
        result["lines_of_code"] = len(lines)
        result["blank_lines"] = sum(1 for line in lines if not line.strip())
        result["comments"] = sum(1 for line in lines if line.strip().startswith("//") or line.strip().startswith("/*") or line.strip().startswith("*"))

        func_patterns = [
            r'function\s+(\w+)\s*\(',
            r'(\w+)\s*\([^)]*\)\s*\{',
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
            r'const\s+(\w+)\s*=\s*function\s*\(',
            r'async\s+function\s+(\w+)\s*\(',
            r'(\w+)\s*:\s*function\s*\(',
        ]
        func_names = set()
        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                if func_name in JS_KEYWORDS:
                    continue
                if func_name in func_names:
                    continue
                func_names.add(func_name)
                result["functions"].append({
                    "name": func_name,
                    "line": content[:match.start()].count("\n") + 1,
                    "decorators": [],
                    "complexity": 1,
                    "docstring": False,
                    "returns": False,
                })

        class_pattern = re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{')
        for match in class_pattern.finditer(content):
            class_info = {
                "name": match.group(1),
                "line": content[:match.start()].count("\n") + 1,
                "methods": [],
                "bases": [match.group(2)] if match.group(2) else [],
                "docstring": False,
            }
            result["classes"].append(class_info)

        import_patterns = [
            r'import\s+[^from]+\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)',
            r'export\s+\{[^}]+\}\s+from\s+[\'"]([^\'"]+)[\'"]',
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                result["imports"].append(match.group(1))

        if_count = len(re.findall(r'\bif\s*\(', content))
        for_count = len(re.findall(r'\bfor\s*\(', content))
        while_count = len(re.findall(r'\bwhile\s*\(', content))
        catch_count = len(re.findall(r'\bcatch\s*\(', content))
        switch_count = len(re.findall(r'\bswitch\s*\(', content))
        result["complexity"] = 1 + if_count + for_count + while_count + catch_count + switch_count

        secret_patterns = [
            r'(api[_-]?key|secret|password|token|private[_-]?key)\s*[:=]\s*["\'][^"\']+["\']',
        ]
        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result["issues"].append("Potential hardcoded secret detected")

        return result

    def analyze_go_file(self, content: str, filepath: str) -> dict:
        """Analyze a Go file."""
        result = {
            "file": filepath,
            "language": "Go",
            "functions": [],
            "classes": [],
            "imports": [],
            "lines_of_code": len(content.split("\n")),
            "comments": 0,
            "blank_lines": 0,
            "complexity": 1,
            "issues": [],
        }

        lines = content.split("\n")
        result["blank_lines"] = sum(1 for line in lines if not line.strip())
        result["comments"] = sum(1 for line in lines if line.strip().startswith("//"))

        func_pattern = re.compile(r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(')
        for match in func_pattern.finditer(content):
            result["functions"].append({
                "name": match.group(1),
                "line": content[:match.start()].count("\n") + 1,
                "complexity": 1,
            })

        import_pattern = re.compile(r'import\s+(?:\(|")([^"\n(]+)')
        for match in import_pattern.finditer(content):
            result["imports"].append(match.group(1).strip().strip('"'))

        if_count = len(re.findall(r'\bif\b', content))
        for_count = len(re.findall(r'\bfor\b', content))
        switch_count = len(re.findall(r'\bswitch\b', content))
        result["complexity"] = 1 + if_count + for_count + switch_count

        return result

    def analyze_file(self, content: str, filepath: str) -> dict:
        """Dispatch to appropriate analyzer based on file extension."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".py":
            return self.analyze_python_file(content, filepath)
        elif ext in (".js", ".ts", ".tsx", ".jsx"):
            return self.analyze_javascript_file(content, filepath)
        elif ext == ".go":
            return self.analyze_go_file(content, filepath)
        else:
            return self.analyze_generic_file(content, filepath)

    def analyze_generic_file(self, content: str, filepath: str) -> dict:
        """Generic file analysis."""
        lines = content.split("\n")
        return {
            "file": filepath,
            "language": "Unknown",
            "functions": [],
            "classes": [],
            "imports": [],
            "lines_of_code": len(lines),
            "comments": sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*"))),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "complexity": 1,
            "issues": [],
        }

    def analyze_project_structure(self, tree_summary: dict, languages: dict) -> dict:
        """Analyze overall project structure."""
        total_files = tree_summary.get("total_files", 0)
        total_dirs = tree_summary.get("total_dirs", 0)
        file_paths = [f["path"] for f in tree_summary.get("files", [])]

        extensions = Counter()
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            extensions[ext if ext else "(no ext)"] += 1

        top_level_items = []
        dirs_at_root = set()
        files_at_root = []
        for path in file_paths:
            parts = path.split("/")
            if len(parts) == 1:
                files_at_root.append(path)
            else:
                dirs_at_root.add(parts[0])

        structure_type = "monorepo" if total_dirs > 10 else (
            "multi-module" if total_dirs > 3 else "single-module"
        )

        has_tests = any(
            "test" in f.lower() or "spec" in f.lower()
            for f in file_paths
        )
        has_ci = any(
            path in file_paths or any(
                "github/workflows" in f for f in file_paths
            )
            for path in [".github/workflows", ".travis.yml", ".gitlab-ci.yml", "Jenkinsfile"]
        )
        has_license = any(
            "license" in f.lower() for f in file_paths
        )
        has_contributing = any(
            "contributing" in f.lower() for f in file_paths
        )
        has_readme = any(
            "readme" in f.lower() for f in file_paths
        )

        return {
            "structure_type": structure_type,
            "total_files": total_files,
            "total_directories": total_dirs,
            "file_extensions": dict(extensions.most_common(15)),
            "root_directories": sorted(dirs_at_root),
            "root_files": sorted(files_at_root),
            "has_tests": has_tests,
            "has_ci_cd": has_ci,
            "has_license": has_license,
            "has_contributing": has_contributing,
            "has_readme": has_readme,
            "test_coverage_indicator": "detected" if has_tests else "none detected",
        }

    def estimate_complexity(self, analyses: list) -> dict:
        """Estimate overall project complexity."""
        if not analyses:
            return {"average_complexity": 0, "max_complexity": 0, "high_complexity_files": []}

        complexities = [a.get("complexity", 0) for a in analyses]
        avg = sum(complexities) / len(complexities) if complexities else 0
        max_c = max(complexities) if complexities else 0
        high = [a["file"] for a in analyses if a.get("complexity", 0) > 10]

        return {
            "average_complexity": round(avg, 2),
            "max_complexity": max_c,
            "high_complexity_files": high,
            "total_functions": sum(len(a.get("functions", [])) for a in analyses),
            "total_classes": sum(len(a.get("classes", [])) for a in analyses),
            "total_imports": sum(len(a.get("imports", [])) for a in analyses),
        }

    def analyze_dependencies(self, package_files: list) -> dict:
        """Analyze project dependencies from manifest files."""
        deps = {"total": 0, "by_file": {}, "frameworks": []}

        for pf in package_files:
            path = pf["path"]
            content = pf.get("content", "")
            file_deps = []
            frameworks = []

            if path == "package.json":
                try:
                    data = json.loads(content)
                    file_deps = list(data.get("dependencies", {}).keys())
                    file_deps += list(data.get("devDependencies", {}).keys())
                    frameworks = self._detect_npm_frameworks(data)
                except json.JSONDecodeError:
                    pass
            elif path == "requirements.txt":
                for line in content.split("\n"):
                    if line.strip() and not line.startswith("#"):
                        pkg = re.split(r'[>=~<!\[]', line.strip())[0]
                        file_deps.append(pkg)
            elif path == "pyproject.toml":
                for line in content.split("\n"):
                    if "dependencies" in line.lower() or any(d in line for d in ["requests", "flask", "django", "fastapi", "pytest"]):
                        frameworks.append(line.strip())
            elif path == "go.mod":
                for line in content.split("\n"):
                    if line.startswith("require"):
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and "/" in parts[0]:
                        file_deps.append(parts[0])
            elif path == "Cargo.toml":
                for line in content.split("\n"):
                    if "=" in line and not line.startswith("["):
                        dep = line.split("=")[0].strip().strip('"')
                        if dep and not dep.startswith("#"):
                            file_deps.append(dep)
            elif path == "Gemfile":
                for line in content.split("\n"):
                    if line.strip().startswith("gem "):
                        match = re.search(r"gem\s+['\"]([^'\"]+)['\"]", line)
                        if match:
                            file_deps.append(match.group(1))
            elif path == "pom.xml":
                for match in re.finditer(r"<artifactId>([^<]+)</artifactId>", content):
                    file_deps.append(match.group(1))

            deps["by_file"][path] = file_deps
            deps["frameworks"].extend(frameworks)
            deps["total"] += len(file_deps)

        return deps

    def _function_complexity(self, node: ast.FunctionDef) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _decorator_name(self, dec: ast.expr) -> str:
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
            return dec.func.id
        elif isinstance(dec, ast.Attribute):
            return dec.attr
        return "unknown"

    def _expr_name(self, expr: ast.expr) -> str:
        if isinstance(expr, ast.Name):
            return expr.id
        elif isinstance(expr, ast.Attribute):
            return expr.attr
        return "Unknown"

    def _detect_npm_frameworks(self, data: dict) -> list:
        frameworks = []
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        known = {
            "next": "Next.js", "react": "React", "vue": "Vue.js",
            "angular": "Angular", "@angular/core": "Angular",
            "express": "Express", "fastify": "Fastify",
            "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
            "spring-boot-starter-web": "Spring Boot",
            "@nestjs/core": "NestJS",
            "svelte": "Svelte", "nuxt": "Nuxt.js",
            "tailwindcss": "Tailwind CSS",
            "typescript": "TypeScript",
        }
        for dep in deps:
            if dep in known:
                frameworks.append(known[dep])
        return frameworks
