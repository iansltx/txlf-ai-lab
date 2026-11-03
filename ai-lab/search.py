"""Lab 3c — search without a language model.

Embed a question, ask Chroma for the three closest chunks, and print
them. No generation happens here: this is the R in RAG, by itself.

Run inside the VM:  python3 search.py "what is the return policy?"
"""

import os
import sys

import chromadb
import requests

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = os.environ.get("CHROMA_PATH", "chroma_db")

question = " ".join(sys.argv[1:]) or "What is the return policy?"

# 1. The question becomes a vector, using the SAME model as ingest.py.
r = requests.post(
    f"{OLLAMA}/api/embed",
    json={"model": EMBED_MODEL, "input": question},
)
r.raise_for_status()
query_vector = r.json()["embeddings"][0]

# 2. Chroma returns the nearest chunks.
collection = chromadb.PersistentClient(path=CHROMA_PATH).get_collection("docs")
results = collection.query(query_embeddings=[query_vector], n_results=3)

print(f"Q: {question}\n")
for doc, meta, dist in zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0],
):
    preview = " ".join(doc.split())[:160]
    print(f"--- {meta['source']}  (distance {dist:.3f})")
    print(f"    {preview}...\n")
