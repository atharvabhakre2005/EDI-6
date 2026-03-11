"""Utility helpers for Agentic Bug Hunter."""

from __future__ import annotations

import csv
import re
import threading
import time
from pathlib import Path
from typing import Generator


def read_samples_csv(filepath: str | Path) -> list[dict[str, str]]:
    """Read code samples from CSV. Expects columns: ID, Code."""
    samples = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append({"ID": row["ID"], "Code": row["Code"]})
    return samples


def get_code_line(code: str, line_number: int) -> str:
    """Extract a specific line from code (1-indexed)."""
    lines = code.split("\n")
    idx = max(line_number - 1, 0)
    return lines[idx].strip() if idx < len(lines) else ""


def get_code_context(code: str, line_number: int, context_lines: int = 3) -> str:
    """Extract code context around a specific line."""
    lines = code.split("\n")
    idx = max(line_number - 1, 0)
    start = max(0, idx - context_lines)
    end = min(len(lines), idx + context_lines + 1)

    context_parts = []
    for i in range(start, end):
        marker = " >> " if i == idx else "    "
        context_parts.append(f"{marker}{i + 1:4d} | {lines[i]}")
    return "\n".join(context_parts)


class Timer:
    """Simple context manager for timing operations."""

    def __init__(self):
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


def chunk_list(items: list, chunk_size: int) -> Generator[list, None, None]:
    """Split a list into chunks of specified size."""
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, requests_per_minute: int = 5):
        self._min_interval = 60.0 / requests_per_minute
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self):
        """Block until it is safe to make the next API call."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()

    @staticmethod
    def extract_retry_delay(error_msg: str) -> float:
        """Extract the API-suggested retry delay from a 429 error message."""
        match = re.search(r"retry in ([\d.]+)s", error_msg, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_msg)
        if match:
            return float(match.group(1))
        return 0.0


gemini_rate_limiter = RateLimiter(requests_per_minute=5)
