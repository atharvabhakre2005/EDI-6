"""Reasoning Agent - Uses Gemini LLM to discover semantic bugs in code."""

from __future__ import annotations

import json
import time

import google.generativeai as genai

from src.agents.base_agent import BaseAgent
from src.models.schemas import RawBug, BugCategory
from src.utils.config import get_api_key, load_settings, load_prompts
from src.utils.helpers import gemini_rate_limiter, RateLimiter
from src.utils.logger import logger


class ReasoningAgent(BaseAgent):
    """Analyzes C++ RDI test code using Gemini to discover semantic bugs.

    This is the primary bug discovery agent that uses LLM reasoning
    to identify API misuse, logic errors, and other semantic issues.
    """

    name = "ReasoningAgent"

    def __init__(self):
        settings = load_settings()
        llm_cfg = settings["llm"]

        genai.configure(api_key=get_api_key())
        self.model = genai.GenerativeModel(llm_cfg["model"])
        self.temperature = llm_cfg.get("temperature", 0.1)
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.retry_attempts = llm_cfg.get("retry_attempts", 3)
        self.retry_delay = llm_cfg.get("retry_delay", 2)
        self.prompts = load_prompts()

    @staticmethod
    def _add_line_numbers(code: str) -> str:
        """Prepend line numbers to each line of code so the LLM can reference exact lines."""
        lines = code.split("\n")
        numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(lines)]
        return "\n".join(numbered)

    def execute(self, code: str) -> list[RawBug]:
        """Analyze code and return a list of raw bug hypotheses."""
        numbered_code = self._add_line_numbers(code)
        prompt = self.prompts["reasoning_agent"].format(code=numbered_code)

        for attempt in range(1, self.retry_attempts + 1):
            try:
                gemini_rate_limiter.wait()
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens,
                    ),
                )
                return self._parse_response(response.text)

            except Exception as e:
                logger.warning(
                    f"[{self.name}] Attempt {attempt}/{self.retry_attempts} failed: {e}"
                )
                if attempt < self.retry_attempts:
                    retry_secs = RateLimiter.extract_retry_delay(str(e))
                    wait = max(retry_secs + 2, self.retry_delay * attempt)
                    logger.info(f"[{self.name}] Waiting {wait:.0f}s before retry...")
                    time.sleep(wait)

        logger.error(f"[{self.name}] All retry attempts exhausted")
        return []

    def _parse_response(self, text: str) -> list[RawBug]:
        """Parse Gemini's JSON response into structured RawBug objects."""
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, list):
                logger.warning(f"[{self.name}] Expected list, got {type(data)}")
                return []

            bugs = []
            for item in data:
                category = item.get("category", "UNKNOWN")
                try:
                    cat = BugCategory(category)
                except ValueError:
                    cat = BugCategory.UNKNOWN

                bugs.append(
                    RawBug(
                        line=int(item.get("line", 1)),
                        summary=str(item.get("summary", "")),
                        category=cat,
                        confidence=float(item.get("confidence", 0.5)),
                    )
                )
            return bugs

        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] JSON parse error: {e}")
            logger.debug(f"[{self.name}] Raw response: {cleaned[:500]}")
            return []
