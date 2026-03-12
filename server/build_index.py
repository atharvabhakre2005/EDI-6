"""Build a new vector store from C/C++ security knowledge documents.

Run from the project root:
    cd server
    python build_index.py
"""

import os
import shutil
from pathlib import Path

from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    Settings,
    StorageContext,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# ── Resolve paths ──────────────────────────────────────────────
current_directory = os.getcwd()
print(f"Current working directory: {current_directory}")

if os.path.basename(current_directory) == "server":
    embedding_path = os.path.join(".", "embedding_model")
    knowledge_path = os.path.join(".", "knowledge")
    storage_path = os.path.join(".", "storage")
else:
    embedding_path = os.path.join(".", "server", "embedding_model")
    knowledge_path = os.path.join(".", "server", "knowledge")
    storage_path = os.path.join(".", "server", "storage")

# ── Verify knowledge directory exists ──────────────────────────
if not Path(knowledge_path).is_dir():
    raise FileNotFoundError(f"Knowledge directory not found: {knowledge_path}")

docs = list(Path(knowledge_path).glob("*.txt"))
print(f"Found {len(docs)} knowledge documents:")
for d in docs:
    print(f"  - {d.name}")

# ── Load embedding model ──────────────────────────────────────
print(f"\nLoading embedding model from: {embedding_path}")
embed_model = HuggingFaceEmbedding(model_name=embedding_path)
Settings.embed_model = embed_model

# ── Read documents ─────────────────────────────────────────────
print("\nReading documents...")
reader = SimpleDirectoryReader(input_dir=knowledge_path, required_exts=[".txt"])
documents = reader.load_data()
print(f"Loaded {len(documents)} document chunks")

# ── Backup old storage ─────────────────────────────────────────
backup_path = storage_path + "_backup"
if Path(storage_path).is_dir():
    if Path(backup_path).is_dir():
        shutil.rmtree(backup_path)
    shutil.copytree(storage_path, backup_path)
    print(f"\nBacked up old storage to: {backup_path}")
    shutil.rmtree(storage_path)

# ── Build and persist index ────────────────────────────────────
print("\nBuilding vector index...")
index = VectorStoreIndex.from_documents(documents)
index.storage_context.persist(persist_dir=storage_path)

print(f"\nVector store saved to: {storage_path}")
print("Done! The MCP server will now use C/C++ security knowledge for grounding.")
