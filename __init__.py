"""
GitHub Repository Analyst - Multi-Agent System

An AI-powered tool that analyzes GitHub repositories using:
- GitHub Agent: Fetches repository data via GitHub API
- Code Intelligence Agent: Analyzes code structure, complexity, and patterns  
- Gemini Agent: Provides AI-powered insights using Google Gemini API

Architecture:
    main.py              -> CLI entry point and orchestration
    config.py            -> Configuration management
    utils.py             -> Shared utilities and helpers
    agents/
        github_agent.py  -> GitHub API operations
        gemini_agent.py  -> Gemini LLM integration
        code_agent.py    -> Code intelligence analysis
    ui.py                -> Rich terminal UI components

Setup:
    pip install -r requirements.txt
    python main.py config
    python main.py analyze owner/repo

Usage Examples:
    python main.py analyze microsoft/vscode
    python main.py analyze facebook/react --depth deep --insights --security
    python main.py compare vercel/next.js nearform/next.js
    python main.py batch repos.txt
"""
