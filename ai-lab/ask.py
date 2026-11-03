"""Lab 4 — ask your documents.

The whole RAG loop: embed the question, retrieve the closest chunks,
put them in the prompt, generate an answer, cite the sources.

Run inside the VM:  python3 ask.py "what is the return policy on a used candle?"
"""

import os
import sys

import chromadb
import requests

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2:3b"
CHROMA_PATH = os.environ.get("CHROMA_PATH", "chroma_db")
TOP_K = 3

question = " ".join(sys.argv[1:]) or "What is the return policy on a used candle?"

# 1. Embed the question.
r = requests.post(
    f"{OLLAMA}/api/embed",
    json={"model": EMBED_MODEL, "input": question},
)
r.raise_for_status()
query_vector = r.json()["embeddings"][0]

# 2. Retrieve the most relevant chunks.
collection = chromadb.PersistentClient(path=CHROMA_PATH).get_collection("docs")
results = collection.query(query_embeddings=[query_vector], n_results=TOP_K)
chunks = results["documents"][0]
sources = sorted({m["source"] for m in results["metadatas"][0]})

# 3. Build the prompt. This is the entire "framework".
context = "\n\n---\n\n".join(chunks)
messages = [
    {
        "role": "system",
        "content": (
            "Answer the question using ONLY the provided context. "
            "If the context does not contain the answer, say you don't know."
        ),
    },
    {
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {question}",
    },
]

# 4. Generate.
r = requests.post(
    f"{OLLAMA}/api/chat",
    json={"model": CHAT_MODEL, "messages": messages, "stream": False},
)
r.raise_for_status()
answer = r.json()["message"]["content"]

print(f"Q: {question}\n")
print(f"A: {answer}\n")
print(f"Sources: {', '.join(sources)}")
