"""Configuration management for Agentic Bug Hunter."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@lru_cache(maxsize=1)
def load_settings() -> dict:
    """Load and cache settings from YAML config."""
    config_path = PROJECT_ROOT / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_prompts() -> dict:
    """Load and cache prompt templates."""
    prompts_path = PROJECT_ROOT / "config" / "prompts.yaml"
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key() -> str:
    """Get the Gemini API key from environment variables."""
    key = os.getenv("GENAI_API_KEY", "")
    if not key:
        raise ValueError(
            "GENAI_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return key


def get_mcp_url() -> str:
    """Get the MCP server URL."""
    settings = load_settings()
    return os.getenv("MCP_SERVER_URL", settings["mcp"]["server_url"])


def get_output_dir() -> Path:
    """Get the reports output directory, creating it if needed."""
    settings = load_settings()
    output_dir = PROJECT_ROOT / settings["reports"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
