"""Explanation Refinement Agent - Batch-produces concise, professional bug explanations."""

from __future__ import annotations

import json
import time

import google.generativeai as genai

from src.agents.base_agent import BaseAgent
from src.utils.config import get_api_key, load_settings, load_prompts
from src.utils.helpers import gemini_rate_limiter, RateLimiter
from src.utils.logger import logger


class ExplanationAgent(BaseAgent):
    """Batch-refines bug descriptions into professional, concise explanations.

    Sends ALL bugs from a sample in a single LLM call to minimize API usage.
    """

    name = "ExplanationAgent"

    def __init__(self):
        settings = load_settings()
        llm_cfg = settings["llm"]

        genai.configure(api_key=get_api_key())
        self.model = genai.GenerativeModel(llm_cfg["model"])
        self.prompts = load_prompts()
        self.max_length = settings["agents"]["explanation"].get("max_length", 200)
        self.retry_attempts = llm_cfg.get("retry_attempts", 3)
        self.retry_delay = llm_cfg.get("retry_delay", 2)

    def execute(self, bugs_data: list[dict]) -> list[str]:
        """Generate refined explanations for ALL bugs in one API call.

        Args:
            bugs_data: List of dicts with keys: index, summary, code_line, docs, severity, category

        Returns:
            List of explanation strings, one per bug.
        """
        if not bugs_data:
            return []

        prompt = self.prompts["explanation_agent_batch"].format(
            bugs_json=json.dumps(bugs_data, indent=2)
        )

        for attempt in range(1, self.retry_attempts + 1):
            try:
                gemini_rate_limiter.wait()
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=2048,
                    ),
                )
                return self._parse_response(response.text, bugs_data)

            except Exception as e:
                logger.warning(
                    f"[{self.name}] Attempt {attempt}/{self.retry_attempts} failed: {e}"
                )
                if attempt < self.retry_attempts:
                    retry_secs = RateLimiter.extract_retry_delay(str(e))
                    wait = max(retry_secs + 2, self.retry_delay * attempt)
                    logger.info(f"[{self.name}] Waiting {wait:.0f}s before retry...")
                    time.sleep(wait)

        # Fallback: return the original summaries
        return [b["summary"] for b in bugs_data]

    def _parse_response(self, text: str, bugs_data: list[dict]) -> list[str]:
        """Parse batch explanation response."""
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
                explanation = item.get("explanation", "")
                if explanation.startswith('"') and explanation.endswith('"'):
                    explanation = explanation[1:-1]
                results.append(explanation)
        except json.JSONDecodeError:
            logger.error(f"[{self.name}] JSON parse error in batch response")

        # Pad with original summaries if fewer results
        while len(results) < len(bugs_data):
            results.append(bugs_data[len(results)]["summary"])
        return results[:len(bugs_data)]
