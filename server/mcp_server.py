"""MCP Server for Agentic Bug Hunter.

This is the Infineon-provided MCP server adapted for the project.
It provides document search via vector similarity using LlamaIndex
with BAAI/bge-base-en-v1.5 embeddings.

Run with:
    cd server
    python mcp_server.py
"""

import math
import os
from pathlib import Path

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.retrievers import VectorIndexRetriever
from fastmcp import FastMCP

# ── Resolve paths ──────────────────────────────────────────────
current_directory = os.getcwd()
print(f"Current working directory: {current_directory}")

if os.path.basename(current_directory) == "server":
    directory_path = os.path.join(".", "embedding_model")
    storage_path = os.path.join(".", "storage")
else:
    directory_path = os.path.join(".", "server", "embedding_model")
    storage_path = os.path.join(".", "server", "storage")

# ── Download embedding model if needed ─────────────────────────
if Path(directory_path).is_dir():
    print(f"Embedding model found at: {directory_path}")
else:
    print(f"Downloading embedding model to: {directory_path}")
    from huggingface_hub import snapshot_download
    model_id = "BAAI/bge-base-en-v1.5"
    snapshot_download(repo_id=model_id, local_dir=directory_path, local_dir_use_symlinks=False)

# ── Initialize embedding model and index ───────────────────────
embed_model = HuggingFaceEmbedding(model_name=directory_path)
Settings.embed_model = embed_model

storage_context = StorageContext.from_defaults(persist_dir=storage_path)
index = load_index_from_storage(storage_context=storage_context)
retriever = VectorIndexRetriever(index=index, similarity_top_k=20)

# ── MCP Server ─────────────────────────────────────────────────
mcp = FastMCP("ABH_Server")


@mcp.tool()
def search_documents(query: str) -> list:
    """Searches documents using vector similarity retrieval.

    Args:
        query: The search query string to find relevant documents.

    Returns:
        list of dicts with 'text' and 'score' keys.
    """
    print(f"[MCP] search_documents: {query[:80]}...")
    nodes = retriever.retrieve(query)
    return [{"text": ele.get_text(), "score": ele.get_score()} for ele in nodes]


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def sine(a: int) -> float:
    """Compute the sine of an angle in degrees."""
    radians = math.radians(a)
    return math.sin(radians)


@mcp.tool()
def list_files_and_folders() -> list:
    """Lists all files and directories in the current working directory."""
    try:
        items = os.listdir(".")
        return items
    except Exception as e:
        return [f"Error: {str(e)}"]


if __name__ == "__main__":
    print("Starting MCP Server on port 8003...")
    mcp.run(transport="sse", port=8003)
