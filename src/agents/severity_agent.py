"""Severity Classification Agent - Batch-classifies bug severities using Gemini."""

from __future__ import annotations

import json
import time

import google.generativeai as genai

from src.agents.base_agent import BaseAgent
from src.models.schemas import Severity
from src.utils.config import get_api_key, load_settings, load_prompts
from src.utils.helpers import gemini_rate_limiter, RateLimiter
from src.utils.logger import logger


class SeverityAgent(BaseAgent):
    """Batch-classifies detected bugs by severity level.

    Sends ALL bugs from a sample in a single LLM call to minimize API usage.
    """

    name = "SeverityAgent"

    def __init__(self):
        settings = load_settings()
        llm_cfg = settings["llm"]

        genai.configure(api_key=get_api_key())
        self.model = genai.GenerativeModel(llm_cfg["model"])
        self.prompts = load_prompts()
        self.retry_attempts = llm_cfg.get("retry_attempts", 3)
        self.retry_delay = llm_cfg.get("retry_delay", 2)

    def execute(self, bugs_data: list[dict]) -> list[tuple[Severity, str]]:
        """Classify severity for ALL bugs in one API call.

        Args:
            bugs_data: List of dicts with keys: index, summary, code_line, category, docs

        Returns:
            List of (Severity, justification) tuples, one per bug.
        """
        if not bugs_data:
            return []

        prompt = self.prompts["severity_agent_batch"].format(
            bugs_json=json.dumps(bugs_data, indent=2)
        )

        for attempt in range(1, self.retry_attempts + 1):
            try:
                gemini_rate_limiter.wait()
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.0,
                        max_output_tokens=1024,
                    ),
                )
                return self._parse_response(response.text, len(bugs_data))

            except Exception as e:
                logger.warning(
                    f"[{self.name}] Attempt {attempt}/{self.retry_attempts} failed: {e}"
                )
                if attempt < self.retry_attempts:
                    retry_secs = RateLimiter.extract_retry_delay(str(e))
                    wait = max(retry_secs + 2, self.retry_delay * attempt)
                    logger.info(f"[{self.name}] Waiting {wait:.0f}s before retry...")
                    time.sleep(wait)

        return [(Severity.MEDIUM, "Classification failed — defaulting to MEDIUM")] * len(bugs_data)

    def _parse_response(self, text: str, expected_count: int) -> list[tuple[Severity, str]]:
        """Parse batch severity response."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        results = []
        try:
            data = json.loads(cleaned)
            if not isinstance(data, list):
                data = [data]

            for item in data:
                severity_str = item.get("severity", "MEDIUM").upper()
                justification = item.get("justification", "")
                try:
                    severity = Severity(severity_str)
                except ValueError:
                    severity = Severity.MEDIUM
                results.append((severity, justification))

        except json.JSONDecodeError:
            logger.error(f"[{self.name}] JSON parse error in batch response")

        # Pad with defaults if we got fewer results than expected
        while len(results) < expected_count:
            results.append((Severity.MEDIUM, "Parse fallback"))
        return results[:expected_count]
