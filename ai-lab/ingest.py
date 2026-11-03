"""Lab 3b — ingest the documents.

Read every markdown file in ./docs, split it into chunks, ask Ollama for
an embedding of each chunk, and store everything in a local Chroma
database. Run it again any time the docs change — it upserts.

Run inside the VM:  python3 ingest.py
"""

import os
import pathlib

import chromadb
import requests

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = os.environ.get("CHROMA_PATH", "chroma_db")
MAX_CHARS = 400  # small on purpose: one chunk ≈ one topic in our docs


def embed(texts: list[str]) -> list[list[float]]:
    r = requests.post(
        f"{OLLAMA}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
    )
    r.raise_for_status()
    return r.json()["embeddings"]


def chunk(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Naive-but-honest chunking: split on blank lines, then merge
    paragraphs until a chunk would exceed max_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if current and len(current) + len(p) > max_chars:
            chunks.append(current)
            current = p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return chunks


client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"},  # smaller distance = more similar
)

ids, texts, metadatas = [], [], []
for path in sorted(pathlib.Path("docs").glob("*.md")):
    for i, piece in enumerate(chunk(path.read_text())):
        ids.append(f"{path.stem}-{i}")
        texts.append(piece)
        metadatas.append({"source": path.name})

print(f"Embedding {len(texts)} chunks from "
      f"{len(set(m['source'] for m in metadatas))} files...")

collection.upsert(
    ids=ids,
    documents=texts,
    embeddings=embed(texts),
    metadatas=metadatas,
)

print(f"Done. Collection 'docs' in ./{CHROMA_PATH} now holds "
      f"{collection.count()} chunks.")
