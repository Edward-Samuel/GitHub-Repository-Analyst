import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
CONFIG_PATH = PROJECT_ROOT / "config.json"
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "github_token": "",
    "primary_model": "gemma-4-26b-a4b-it",
    "fallback_model": "gemma-4-31b-it",
    "default_depth": "medium",
    "default_report_format": "markdown",
    "max_file_size_kb": 100,
    "max_files_to_analyze": 200,
    "cache_responses": True,
    "cache_dir": ".cache",
}

ENV_CONFIG_KEYS = {
    "GEMINI_API_KEY": "gemini_api_key",
    "GITHUB_TOKEN": "github_token",
    "PRIMARY_MODEL": "primary_model",
    "FALLBACK_MODEL": "fallback_model",
    "DEFAULT_DEPTH": "default_depth",
    "DEFAULT_REPORT_FORMAT": "default_report_format",
    "MAX_FILE_SIZE_KB": "max_file_size_kb",
    "MAX_FILES_TO_ANALYZE": "max_files_to_analyze",
    "CACHE_RESPONSES": "cache_responses",
    "CACHE_DIR": "cache_dir",
}


def _load_env_file():
    """Load variables from .env file if it exists."""
    env_vars = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes from value
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                        value = value[1:-1]
                    env_vars[key] = value
    return env_vars


def load_config():
    # Load .env file first (lowest priority)
    env_vars = _load_env_file()

    # Load config.json next
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            config.update(json.load(f))

    # Apply .env values using the documented uppercase names.
    for key, value in env_vars.items():
        config_key = ENV_CONFIG_KEYS.get(key, key if key in DEFAULT_CONFIG else None)
        if config_key:
            config[config_key] = value

    # Convert common typed settings loaded from text.
    for key in ("max_file_size_kb", "max_files_to_analyze"):
        if isinstance(config.get(key), str):
            config[key] = int(config[key])
    if isinstance(config.get("cache_responses"), str):
        config["cache_responses"] = config["cache_responses"].lower() in {"1", "true", "yes", "on"}

    # Environment variables always take highest priority
    for env_key, config_key in ENV_CONFIG_KEYS.items():
        if os.environ.get(env_key):
            config[config_key] = os.environ[env_key]

    # Normalize the short model aliases used by earlier versions to the
    # model IDs exposed by the Gemini API.
    model_aliases = {
        "gemma-4-26b": "gemma-4-26b-a4b-it",
        "gemma-4-31b": "gemma-4-31b-it",
    }
    for key in ("primary_model", "fallback_model"):
        if config.get(key) in model_aliases:
            config[key] = model_aliases[config[key]]

    return config


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_api_key():
    config = load_config()
    key = config.get("gemini_api_key")
    if not key:
        raise ValueError(
            "Gemini API key not found. Set it via:\n"
            "  1. python main.py config\n"
            "  2. .env file (GEMINI_API_KEY=your_key)\n"
            "  3. Environment variable (export GEMINI_API_KEY=your_key)"
        )
    return key


def get_github_token():
    config = load_config()
    return config.get("github_token")


def configure():
    print("=== GitHub Repository Analyst - Configuration ===\n")

    gemini_key = input("Enter your Gemini API key: ").strip()
    if not gemini_key:
        print("Warning: Gemini API key is required for AI features.")

    github_token = input("Enter GitHub Token (optional, for higher rate limits): ").strip()

    config = load_config()
    if gemini_key:
        config["gemini_api_key"] = gemini_key
    if github_token:
        config["github_token"] = github_token

    print("\nPreferred model order (primary then fallback):")
    config["primary_model"] = input(
        f"Primary model [{config.get('primary_model', 'gemma-4-26b-a4b-it')}]: "
    ).strip() or config.get("primary_model", "gemma-4-26b-a4b-it")
    config["fallback_model"] = input(
        f"Fallback model [{config.get('fallback_model', 'gemma-4-31b-it')}]: "
    ).strip() or config.get("fallback_model", "gemma-4-31b-it")

    save_config(config)
    print("\nConfiguration saved to {}".format(CONFIG_PATH))
    print("Done! You can now run analyses.")
