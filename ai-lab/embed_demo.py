"""Lab 3a — see an embedding.

Three sentences in, three vectors out. Two of them mean roughly the same
thing; one doesn't. The numbers agree.

Run inside the VM:  python3 embed_demo.py
"""

import requests

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"


def embed(texts: list[str]) -> list[list[float]]:
    """Turn a list of strings into a list of vectors via Ollama."""
    r = requests.post(
        f"{OLLAMA}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
    )
    r.raise_for_status()
    return r.json()["embeddings"]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity: 1.0 = same direction, 0.0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b)


sentences = [
    "The candle smells like lavender and cedar.",
    "This wax melt has notes of lavender and wood.",
    "Restart the server after updating the config file.",
]

vectors = embed(sentences)

print(f"Each sentence became a vector of {len(vectors[0])} numbers.")
print(f"The first five numbers of sentence 0: "
      f"{[round(x, 3) for x in vectors[0][:5]]}\n")

for i in range(len(sentences)):
    for j in range(i + 1, len(sentences)):
        sim = cosine(vectors[i], vectors[j])
        print(f"similarity({i}, {j}) = {sim:.3f}")
        print(f"   {sentences[i]}")
        print(f"   {sentences[j]}\n")
