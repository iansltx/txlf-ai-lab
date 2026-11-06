"""Bonus lab: a browser front end for ask.py.

The same RAG loop as ask.py, served as one web page. No framework, just
Python's built-in HTTP server. Lima forwards the port, so the page opens
in the browser on your host.

Run inside the VM:  python3 web.py
Then open:          http://localhost:8000
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chromadb
import requests

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2:3b"
CHROMA_PATH = os.environ.get("CHROMA_PATH", "chroma_db")
TOP_K = 3
PORT = 8000

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ask Your Documents</title>
<style>
  :root { --bg: #002b36; --panel: #073642; --line: #0e4250; --text: #eee8d5;
          --muted: #93a1a1; --accent: #2aa198; --error: #dc322f; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 17px/1.55 system-ui, sans-serif; }
  main { max-width: 760px; margin: 0 auto; padding: 40px 16px; }
  h1 { margin: 0 0 4px; font-size: 1.8em; }
  h2 { margin: 28px 0 8px; font-size: 0.8em; color: var(--muted);
       letter-spacing: 0.1em; text-transform: uppercase; }
  p { margin: 0; }
  form { display: flex; gap: 8px; margin-top: 24px; }
  input { flex: 1; min-width: 0; padding: 12px; font: inherit; color: var(--text);
          background: var(--panel); border: 1px solid var(--line); border-radius: 6px; }
  button { padding: 12px 20px; font: inherit; font-weight: 600; color: var(--bg);
           background: var(--accent); border: 0; border-radius: 6px; cursor: pointer; }
  button:disabled { opacity: 0.6; cursor: wait; }
  .muted { color: var(--muted); }
  .error { color: var(--text); background: var(--error); padding: 12px; border-radius: 6px; }
  .answer { white-space: pre-wrap; }
  details { background: var(--panel); border: 1px solid var(--line);
            border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }
  summary { cursor: pointer; }
  details p { margin-top: 8px; white-space: pre-wrap; font-size: 0.9em; color: var(--muted);
              overflow-wrap: anywhere; }
</style>
</head>
<body>
<main>
  <h1>Ask Your Documents</h1>
  <p class="muted">Everything runs in your VM. Nothing leaves your laptop.</p>
  <form id="form">
    <input id="question" aria-label="Your question" autocomplete="off" required
           placeholder="What is the return policy on a used candle?">
    <button id="ask">Ask</button>
  </form>
  <div id="status" class="muted" role="status" style="margin-top:16px"></div>
  <div id="result" hidden>
    <h2>Answer</h2>
    <p id="answer" class="answer"></p>
    <h2>Retrieved chunks</h2>
    <div id="chunks"></div>
  </div>
</main>
<script>
  const $ = (id) => document.getElementById(id);

  $("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("ask").disabled = true;
    $("result").hidden = true;
    $("status").className = "muted";
    $("status").textContent = "Thinking. On a CPU this can take a minute...";
    try {
      const response = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: $("question").value }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      $("answer").textContent = data.answer;
      $("chunks").replaceChildren(...data.chunks.map((chunk) => {
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        const text = document.createElement("p");
        summary.textContent = `${chunk.source} (distance ${chunk.distance.toFixed(3)})`;
        text.textContent = chunk.text;
        details.append(summary, text);
        return details;
      }));
      $("status").textContent = "";
      $("result").hidden = false;
    } catch (error) {
      $("status").className = "error";
      $("status").textContent = error.message;
    } finally {
      $("ask").disabled = false;
    }
  });
</script>
</body>
</html>
"""


def ask(question: str) -> dict:
    """The same four steps as ask.py, returning data instead of printing it."""
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

    # 3. Build the prompt.
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

    return {
        "answer": r.json()["message"]["content"],
        "chunks": [
            {"text": text, "source": meta["source"], "distance": distance}
            for text, meta, distance in zip(
                chunks, results["metadatas"][0], results["distances"][0]
            )
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def send_body(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, data: dict) -> None:
        self.send_body(status, "application/json", json.dumps(data).encode())

    def do_GET(self) -> None:
        if self.path == "/":
            self.send_body(200, "text/html; charset=utf-8", PAGE.encode())
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/ask":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            question = json.loads(self.rfile.read(length))["question"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            self.send_json(400, {"error": "Send JSON with a question."})
            return
        if not question:
            self.send_json(400, {"error": "Type a question first."})
            return
        try:
            self.send_json(200, ask(question))
        except chromadb.errors.NotFoundError:
            self.send_json(500, {"error": "No documents yet. Run python3 ingest.py first."})
        except requests.RequestException as error:
            self.send_json(502, {"error": f"Couldn't get a reply from Ollama: {error}"})


if __name__ == "__main__":
    print(f"Open http://localhost:{PORT} in your browser. Press Ctrl-C to stop.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
