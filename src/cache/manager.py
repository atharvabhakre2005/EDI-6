"""Cache Manager - Stores and replays analysis results for demo mode.

Caches complete AnalysisResult objects keyed by a hash of the input code.
This allows the system to replay previous analyses without making any API calls.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from src.utils.logger import logger

# Cache directory at project root
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"


class CacheManager:
    """Manages reading and writing cached analysis results.

    Cache keys are SHA-256 hashes of the input source code, ensuring
    that identical code always maps to the same cache entry.
    """

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.cache_dir / "index.json"
        self._index = self._load_index()

    # ── Public API ─────────────────────────────────────────────

    def has(self, code: str) -> bool:
        """Check if a cached result exists for the given code."""
        key = self._hash_code(code)
        cache_file = self.cache_dir / f"{key}.json"
        return cache_file.exists()

    def get(self, code: str) -> dict | None:
        """Retrieve a cached analysis result for the given code.

        Returns:
            dict with the cached AnalysisResult data, or None if not found.
        """
        key = self._hash_code(code)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            logger.debug(f"[Cache] MISS for key {key[:12]}...")
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"[Cache] HIT for key {key[:12]}... (sample: {data.get('sample_id', '?')})")
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[Cache] Failed to read {cache_file}: {e}")
            return None

    def put(self, code: str, sample_id: str, result_data: dict) -> None:
        """Store an analysis result in the cache.

        Args:
            code: The source code that was analyzed.
            sample_id: The sample identifier.
            result_data: Serialized AnalysisResult data.
        """
        key = self._hash_code(code)
        cache_file = self.cache_dir / f"{key}.json"

        payload = {
            "sample_id": sample_id,
            "code_hash": key,
            "cached_at": datetime.now().isoformat(),
            "result": result_data,
        }

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)

            # Update index
            self._index[key] = {
                "sample_id": sample_id,
                "cached_at": payload["cached_at"],
                "code_preview": code[:80].replace("\n", " "),
            }
            self._save_index()
            logger.info(f"[Cache] STORED result for {sample_id} (key: {key[:12]}...)")
        except OSError as e:
            logger.error(f"[Cache] Failed to write cache: {e}")

    def list_cached(self) -> list[dict]:
        """List all cached entries with metadata."""
        return [
            {"key": k, **v}
            for k, v in self._index.items()
        ]

    def clear(self) -> int:
        """Clear all cached results. Returns number of entries removed."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            if f.name != "index.json":
                f.unlink()
                count += 1
        self._index = {}
        self._save_index()
        logger.info(f"[Cache] Cleared {count} cached entries")
        return count

    # ── Internal ───────────────────────────────────────────────

    @staticmethod
    def _hash_code(code: str) -> str:
        """Generate a deterministic SHA-256 hash of the source code."""
        # Normalize whitespace to avoid cache misses from trivial formatting changes
        normalized = code.strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _load_index(self) -> dict:
        """Load the cache index file."""
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_index(self) -> None:
        """Persist the cache index to disk."""
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2)
        except OSError as e:
            logger.warning(f"[Cache] Failed to save index: {e}")
