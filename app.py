"""
GitHub Repository Analyst - Streamlit Web UI

A web interface for the multi-agent GitHub analysis system.
Run with: streamlit run app.py
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from agents.github_agent import GitHubAgent
from agents.gemini_agent import GeminiAgent
from agents.code_agent import CodeIntelligenceAgent
from config import load_config, get_api_key
from utils import get_repo_owner_repo, truncate_text


def main():
    st.set_page_config(
        page_title="GitHub Repository Analyst",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🔍 GitHub Repository Analyst")
    st.markdown("*AI-powered repository analysis using Gemini API, GitHub API, and code intelligence*")
    st.markdown("---")

    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = {}
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    with st.sidebar:
        st.header("⚙️ Settings")

        config = load_config()
        env_gemini = os.environ.get("GEMINI_API_KEY", "")
        env_gh = os.environ.get("GITHUB_TOKEN", "")
        config_gemini = config.get("gemini_api_key", "")

        if env_gemini or config_gemini:
            st.success("✅ Gemini API Key loaded from env/.env/config")
            gemini_key = env_gemini or config_gemini
        else:
            gemini_key = st.text_input(
                "Gemini API Key",
                value="",
                type="password",
                help="Set GEMINI_API_KEY env var or edit .env file. Get it at https://aistudio.google.com/app/apikey",
            )

        if env_gh:
            st.success("✅ GitHub Token loaded from environment")
            github_token = env_gh
        else:
            github_token = st.text_input(
                "GitHub Token (optional)",
                value="",
                type="password",
                help="Set GITHUB_TOKEN env var or edit .env file. Get it at https://github.com/settings/tokens",
            )

        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["shallow", "medium", "deep"],
            index=1,
            help="Shallow = fewer files, faster; Deep = more comprehensive",
        )

        st.markdown("---")
        st.markdown("### Quick Links")
        st.markdown("[GitHub Agent Methods](https://docs.github.com/en/rest)")
        st.markdown("[Gemini API Docs](https://ai.google.dev/docs)")

    st.markdown("---")

    with st.expander("📝 How to use", expanded=False):
        st.markdown("""
        1. Set **GEMINI_API_KEY** as an environment variable or in `.env` file,
           or enter it in the sidebar
           ```bash
           export GEMINI_API_KEY=your_key_here
           streamlit run app.py
           ```
        2. Optionally set **GITHUB_TOKEN** for higher rate limits
        3. Enter a repository in `owner/repo` format (e.g., `fastapi/fastapi`)
        4. Choose analysis depth and click **Analyze**
        5. View the comprehensive report with code intelligence and AI insights
        """)

    col1, col2 = st.columns(2)
    with col1:
        repo_input = st.text_input(
            "Repository (owner/repo)",
            placeholder="e.g., fastapi/fastapi",
        )
    with col2:
        analyze_clicked = st.button("🔍 Analyze Repository", use_container_width=True)

    if analyze_clicked and repo_input:
        try:
            owner, repo = get_repo_owner_repo(repo_input)
        except ValueError as e:
            st.error(str(e))
            return

        if not gemini_key:
            st.warning("⚠️ Gemini API key is required for AI analysis features.")
            return

        progress_bar = st.progress(0, text="Starting analysis...")
        status_text = st.empty()

        try:
            status_text.text("Step 1/6: GitHub Agent - Fetching repository metadata...")
            progress_bar.progress(1 / 6)

            github_agent = GitHubAgent()
            gemini_agent = GeminiAgent()
            code_agent = CodeIntelligenceAgent()

            repo_info = github_agent.get_repo_metadata(owner, repo)
            languages = github_agent.get_languages(owner, repo)

            status_text.text("Step 2/6: GitHub Agent - Fetching repository tree...")
            progress_bar.progress(2 / 6)

            tree = github_agent.get_repo_tree(owner, repo)
            tree_summary = {
                "total_files": sum(1 for item in tree if item.get("type") == "blob"),
                "total_dirs": sum(1 for item in tree if item.get("type") == "tree"),
                "files": [
                    {"path": f["path"], "size": f.get("size", 0)}
                    for f in tree if f.get("type") == "blob"
                ][:50],
            }

            status_text.text("Step 3/6: Code Intelligence - Analyzing project structure...")
            progress_bar.progress(3 / 6)

            structure = code_agent.analyze_project_structure(tree_summary, languages)

            status_text.text("Step 4/6: Code Intelligence - Analyzing code files...")
            progress_bar.progress(4 / 6)

            code_files = github_agent.get_code_files(owner, repo, tree, max_files=30)
            code_analyses = []
            code_files_content = {}
            for cf in code_files[:10]:
                content = github_agent.get_file_content(owner, repo, cf["path"])
                if content and len(content) < 100000:
                    analysis = code_agent.analyze_file(content, cf["path"])
                    code_analyses.append(analysis)
                    code_files_content[cf["path"]] = content

            status_text.text("Step 5/6: Code Intelligence - Analyzing dependencies...")
            progress_bar.progress(5 / 6)

            package_files = github_agent.get_package_files(owner, repo, tree)
            deps = code_agent.analyze_dependencies(package_files)
            complexity = code_agent.estimate_complexity(code_analyses)

            status_text.text("Step 6/6: Gemini Agent - Running AI analysis...")
            progress_bar.progress(5.5 / 6)

            commits = github_agent.get_commits(owner, repo, per_page=20)
            contributors = github_agent.get_contributors(owner, repo, per_page=20)
            readme = github_agent.get_readme(owner, repo)

            analysis_text = gemini_agent.analyze_repository(
                repo_info=repo_info,
                languages=languages,
                tree_summary=tree_summary,
                commits=commits,
                contributors=contributors,
                code_samples={
                    k: truncate_text(v, 2000)
                    for k, v in code_files_content.items()
                },
                readme=readme,
                package_files=[
                    {
                        "path": pf["path"],
                        "content": truncate_text(pf.get("content", ""), 2000),
                    }
                    for pf in package_files
                ],
            )

            chat_context_parts = [
                f"Repository: {repo_info.get('full_name', repo_input)}",
                f"Description: {repo_info.get('description', 'N/A')}",
                f"Languages: {json.dumps(languages)}",
                f"Repository tree summary: {json.dumps(tree_summary)}",
            ]
            if readme:
                chat_context_parts.append(
                    f"FILE: README.md\n{truncate_text(readme, 8000)}"
                )
            for package_file in package_files:
                chat_context_parts.append(
                    f"FILE: {package_file['path']}\n"
                    f"{truncate_text(package_file.get('content', ''), 6000)}"
                )
            for path, content in code_files_content.items():
                chat_context_parts.append(
                    f"FILE: {path}\n{truncate_text(content, 10000)}"
                )

            progress_bar.progress(1.0)
            status_text.text("✅ Analysis complete!")

            st.session_state.analysis_complete = True
            st.session_state.analysis_data = {
                "repo_info": repo_info,
                "languages": languages,
                "tree_summary": tree_summary,
                "structure": structure,
                "code_analyses": code_analyses,
                "code_files_content": code_files_content,
                "complexity": complexity,
                "dependencies": deps,
                "package_files": package_files,
                "analysis_text": analysis_text,
                "chat_context": "\n\n".join(chat_context_parts),
                "repo_input": repo_input,
            }
            st.session_state.chat_messages = []

        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            st.exception(e)
            status_text.text("❌ Analysis failed")
            progress_bar.empty()
            return

    if st.session_state.analysis_complete:
        data = st.session_state.analysis_data
        repo_info = data["repo_info"]

        st.markdown("---")
        st.success("✅ Analysis Complete!")
        st.markdown("### Repository Overview")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Stars", f"{repo_info.get('stargazers_count', 0):,}")
        with col2:
            st.metric("Forks", f"{repo_info.get('forks_count', 0):,}")
        with col3:
            st.metric("Open Issues", f"{repo_info.get('open_issues_count', 0):,}")
        with col4:
            st.metric("Size", f"{repo_info.get('size', 0):,} KB")

        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Languages",
            "🏗️ Structure",
            "🧠 Code Analysis",
            "📦 Dependencies",
            "🤖 AI Report",
            "💬 Repository Chat",
        ])

        with tab1:
            st.subheader("Language Breakdown")
            languages = data["languages"]
            if languages:
                total = sum(languages.values())
                for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:20]:
                    pct = count / total * 100 if total > 0 else 0
                    st.markdown(
                        f"**{lang}**: {count:,} lines ({pct:.1f}%)"
                        f"{'█' * int(pct / 3)}"
                    )
            else:
                st.info("No language data available.")

        with tab2:
            st.subheader("Project Structure")
            structure = data["structure"]
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Files", structure["total_files"])
            c2.metric("Directories", structure["total_directories"])
            c3.metric("Has Tests", "Yes" if structure["has_tests"] else "No")
            c4.metric("Has CI/CD", "Yes" if structure["has_ci_cd"] else "No")
            c5.metric("Has README", "Yes" if structure["has_readme"] else "No")

            st.write("**Root Directories:**", ", ".join(structure.get("root_directories", [])))
            st.write("**Structure Type:**", structure.get("structure_type", "N/A"))
            st.write("**File Extensions:**")
            ext_data = structure.get("file_extensions", {})
            if ext_data:
                st.table(
                    [{"Extension": k, "Count": v} for k, v in list(ext_data.items())[:15]]
                )

        with tab3:
            st.subheader("Code Analysis Results")
            analyses = data.get("code_analyses", [])
            if analyses:
                for analysis in analyses:
                    with st.expander(
                        f"📄 {analysis.get('file', 'unknown')} "
                        f"(LoC: {analysis.get('lines_of_code', 0)}, "
                        f"Complexity: {analysis.get('complexity', 0)})",
                        expanded=True,
                    ):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**Functions:**", len(analysis.get("functions", [])))
                            st.write("**Classes:**", len(analysis.get("classes", [])))
                            st.write("**Imports:**", len(analysis.get("imports", [])))
                            st.write(
                                "**Comments:**", analysis.get("comments", 0)
                            )
                            st.write(
                                "**Blank Lines:**", analysis.get("blank_lines", 0)
                            )
                        with c2:
                            if analysis.get("issues"):
                                for issue in analysis["issues"]:
                                    st.warning(f"⚠️ {issue}")
                            else:
                                st.success("No issues detected")

                        if analysis.get("functions"):
                            st.write("**Functions:**")
                            func_data = [
                                {
                                    "Name": f["name"],
                                    "Line": f["line"],
                                    "Complexity": f.get("complexity", 0),
                                    "Docstring": "Yes" if f.get("docstring") else "No",
                                }
                                for f in analysis["functions"][:20]
                            ]
                            st.table(func_data)

                        if analysis.get("classes"):
                            st.write("**Classes:**")
                            class_data = [
                                {
                                    "Name": c["name"],
                                    "Line": c["line"],
                                    "Methods": ", ".join(c.get("methods", [])),
                                }
                                for c in analysis["classes"]
                            ]
                            st.table(class_data)
            else:
                st.info("No code files were analyzed.")

            complexity = data.get("complexity", {})
            if complexity:
                st.markdown("---")
                st.subheader("Complexity Summary")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Avg Complexity", complexity.get("average_complexity", 0))
                c2.metric("Max Complexity", complexity.get("max_complexity", 0))
                c3.metric("Total Functions", complexity.get("total_functions", 0))
                c4.metric("Total Classes", complexity.get("total_classes", 0))
                if complexity.get("high_complexity_files"):
                    st.warning(
                        "**High complexity files (>10):** "
                        + ", ".join(complexity["high_complexity_files"])
                    )

        with tab4:
            st.subheader("Dependencies")
            deps = data.get("dependencies", {})
            total_deps = deps.get("total", 0)
            frameworks = deps.get("frameworks", [])
            st.metric("Total Dependencies", total_deps)
            if frameworks:
                st.write("**Detected Frameworks:**")
                for fw in frameworks:
                    st.markdown(f"- **{fw}**")
            by_file = deps.get("by_file", {})
            if by_file:
                st.write("**Dependencies by File:**")
                for path, dep_list in by_file.items():
                    with st.expander(f"📄 {path} ({len(dep_list)} deps)"):
                        for dep in dep_list[:30]:
                            st.text(f"• {dep}")
                        if len(dep_list) > 30:
                            st.text(f"... and {len(dep_list) - 30} more")
            if not total_deps and not frameworks:
                st.info("No dependency files found (package.json, requirements.txt, etc.)")

        with tab5:
            st.subheader("🤖 Full AI Analysis Report")
            analysis_text = data.get("analysis_text", "")
            if analysis_text:
                st.markdown(analysis_text)
            else:
                st.info("No AI analysis available.")

        with tab6:
            st.subheader("💬 Ask Questions About This Repository")
            st.caption(
                "Answers are grounded in the files fetched during analysis. "
                "Ask about implementation, dependencies, architecture, or specific files."
            )

            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            question = st.chat_input(
                "Ask something about the repository..."
            )
            if question:
                st.session_state.chat_messages.append(
                    {"role": "user", "content": question}
                )
                with st.chat_message("user"):
                    st.markdown(question)

                with st.chat_message("assistant"):
                    with st.spinner("Searching repository context..."):
                        try:
                            chat_agent = GeminiAgent()
                            answer = chat_agent.answer_question(
                                context=data.get("chat_context", ""),
                                question=question,
                            )
                            st.markdown(answer)
                            st.session_state.chat_messages.append(
                                {"role": "assistant", "content": answer}
                            )
                        except Exception as exc:
                            error_message = f"Unable to answer from repository files: {exc}"
                            st.error(error_message)
                            st.session_state.chat_messages.append(
                                {"role": "assistant", "content": error_message}
                            )

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Re-run Analysis"):
                st.session_state.analysis_complete = False
                st.session_state.analysis_data = {}
                st.rerun()
        with col_b:
            if st.button("📋 Copy Report"):
                st.session_state.copy_text = data.get("analysis_text", "")
                st.rerun()

    else:
        st.markdown("---")
        st.info("Enter a repository name (e.g., `fastapi/fastapi`) and click **Analyze Repository** to begin.")

        with st.expander("Show example repositories", expanded=True):
            examples = [
                ("fastapi/fastapi", "API Framework"),
                ("facebook/react", "UI Library"),
                ("microsoft/vscode", "Code Editor"),
                ("torvalds/linux", "Operating System Kernel"),
                ("google/flax", "ML Framework"),
                ("fastapi/fastapi", "API Framework"),
            ]
            for repo, desc in examples:
                if st.button(f"🔍 {repo}", key=repo):
                    st.rerun()


if __name__ == "__main__":
    main()
