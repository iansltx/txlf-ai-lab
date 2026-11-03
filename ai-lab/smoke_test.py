"""Pre-workshop smoke test.

Run inside the VM, with the venv active:  python3 smoke_test.py
Three check marks means you're ready for the workshop.
"""

import sys

REQUIRED_MODELS = ("llama3.2:3b", "nomic-embed-text")


def check(label, fn) -> bool:
    try:
        fn()
        print(f"  [ok] {label}")
        return True
    except Exception as exc:  # noqa: BLE001 — report anything that breaks
        print(f"  [!!] {label} — {exc}")
        return False


def ollama_is_running():
    import requests

    requests.get("http://localhost:11434/api/version", timeout=5).raise_for_status()


def models_are_pulled():
    import requests

    tags = requests.get("http://localhost:11434/api/tags", timeout=5).json()
    names = [m["name"] for m in tags.get("models", [])]
    missing = [
        m for m in REQUIRED_MODELS if not any(n.startswith(m) for n in names)
    ]
    if missing:
        raise RuntimeError(
            f"missing: {', '.join(missing)} — run 'ollama pull <model>'"
        )


def python_deps_installed():
    import chromadb  # noqa: F401
    import requests  # noqa: F401


ok = all(
    [
        check("Ollama is running", ollama_is_running),
        check("required models are pulled", models_are_pulled),
        check("python dependencies installed", python_deps_installed),
    ]
)

print("\nAll good — see you at the workshop!" if ok else
      "\nFix the [!!] items above, then run this again.")
sys.exit(0 if ok else 1)
