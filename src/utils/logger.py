"""Structured logging for Agentic Bug Hunter."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from src.utils.config import load_settings, PROJECT_ROOT


def setup_logger(name: str = "bug_hunter") -> logging.Logger:
    """Create a configured logger with console and optional file output."""
    settings = load_settings()
    log_cfg = settings.get("logging", {})

    logger = logging.getLogger(name)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if log_cfg.get("console", True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    log_file = log_cfg.get("file")
    if log_file:
        log_path = PROJECT_ROOT / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Module-level logger instance
logger = setup_logger()
