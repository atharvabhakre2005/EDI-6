"""Abstract base agent for the multi-agent pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.models.schemas import AgentEvent
from src.utils.logger import logger
from src.utils.helpers import Timer


class BaseAgent(ABC):
    """Base class for all agents in the pipeline.

    Provides unified logging, timing, and trace event generation.
    """

    name: str = "BaseAgent"

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the agent's core logic. Must be implemented by subclasses."""
        ...

    def run(self, *args, **kwargs) -> tuple:
        """Run the agent with timing and trace event generation.

        Returns:
            tuple: (result, AgentEvent)
        """
        logger.info(f"[{self.name}] Starting execution...")
        timer = Timer()

        try:
            with timer:
                result = self.execute(*args, **kwargs)

            event = AgentEvent(
                agent_name=self.name,
                action="execute",
                timestamp=datetime.now(),
                duration_ms=timer.elapsed_ms,
                input_summary=self._summarize_input(*args, **kwargs),
                output_summary=self._summarize_output(result),
                status="success",
            )
            logger.info(
                f"[{self.name}] Completed in {timer.elapsed_ms:.1f}ms"
            )
            return result, event

        except Exception as e:
            event = AgentEvent(
                agent_name=self.name,
                action="execute",
                timestamp=datetime.now(),
                duration_ms=timer.elapsed_ms,
                input_summary=self._summarize_input(*args, **kwargs),
                output_summary=f"ERROR: {e}",
                status="error",
            )
            logger.error(f"[{self.name}] Failed: {e}")
            return None, event

    def _summarize_input(self, *args, **kwargs) -> str:
        """Generate a brief summary of the input for tracing."""
        parts = []
        for a in args:
            if isinstance(a, str):
                parts.append(a[:80] + "..." if len(a) > 80 else a)
            else:
                parts.append(str(type(a).__name__))
        return ", ".join(parts) if parts else "no input"

    def _summarize_output(self, result) -> str:
        """Generate a brief summary of the output for tracing."""
        if result is None:
            return "no output"
        if isinstance(result, list):
            return f"{len(result)} items"
        if isinstance(result, str):
            return result[:100] + "..." if len(result) > 100 else result
        return str(type(result).__name__)
