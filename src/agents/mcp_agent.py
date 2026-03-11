"""MCP Knowledge Agent - Queries the Infineon MCP server for documentation grounding."""

from __future__ import annotations

import asyncio

from fastmcp import Client

from src.agents.base_agent import BaseAgent
from src.models.schemas import DocumentChunk
from src.utils.config import get_mcp_url, load_settings
from src.utils.logger import logger


class MCPKnowledgeAgent(BaseAgent):
    """Queries the MCP server to retrieve relevant documentation.

    Uses the Infineon-provided MCP server with vector similarity search
    to ground bug hypotheses against official documentation.
    """

    name = "MCPKnowledgeAgent"

    def __init__(self):
        settings = load_settings()
        self.url = get_mcp_url()
        self.min_score = settings["agents"]["mcp_knowledge"].get(
            "min_relevance_score", 0.3
        )

    def execute(self, query: str) -> list[DocumentChunk]:
        """Query MCP server and return relevant documentation chunks."""
        try:
            result = asyncio.run(self._async_query(query))
            return result
        except Exception as e:
            logger.error(f"[{self.name}] MCP query failed: {e}")
            return []

    async def _async_query(self, query: str) -> list[DocumentChunk]:
        """Async MCP client call to search_documents tool."""
        async with Client(self.url) as client:
            result = await client.call_tool(
                "search_documents", {"query": query}
            )

            chunks = []
            if hasattr(result, "content"):
                for item in result.content:
                    text = getattr(item, "text", "")
                    score = getattr(item, "score", 0.0)

                    # Try parsing if text is a JSON-like string
                    if isinstance(text, str) and text.startswith("["):
                        try:
                            import json
                            parsed = json.loads(text)
                            for p in parsed:
                                if isinstance(p, dict):
                                    doc_score = float(p.get("score", 0.0))
                                    if doc_score >= self.min_score:
                                        chunks.append(
                                            DocumentChunk(
                                                text=p.get("text", ""),
                                                score=doc_score,
                                            )
                                        )
                        except (json.JSONDecodeError, TypeError):
                            chunks.append(DocumentChunk(text=text, score=score))
                    else:
                        chunks.append(DocumentChunk(text=text, score=score))

            # Sort by relevance score descending
            chunks.sort(key=lambda c: c.score, reverse=True)
            return chunks

    def get_docs_text(self, chunks: list[DocumentChunk], max_chunks: int = 5) -> str:
        """Combine top documentation chunks into a single text string."""
        top_chunks = chunks[:max_chunks]
        return " ".join(c.text for c in top_chunks if c.text)
