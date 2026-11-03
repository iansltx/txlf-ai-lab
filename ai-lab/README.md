# ai-lab — a local LLM + RAG workshop

One folder, one VM, one afternoon. Please complete these steps **before the
workshop** on good wifi — the downloads total roughly 3 GB.

## 0. Requirements

- macOS 13.5+ (Intel or Apple Silicon), or Linux with KVM available
- 16 GB RAM recommended, 8 GB minimum (see the note in step 3)
- About 15 GB of free disk space

## 1. Install Lima

macOS, or Linux with Homebrew:

```
brew install lima
```

Linux without Homebrew: download the tarball from
<https://github.com/lima-vm/lima/releases> and extract it under `/usr/local`.
Linux hosts also need QEMU (`sudo apt install qemu-system-x86` or your
distro's equivalent) and your user in the `kvm` group.

Verify:

```
limactl --version
```

Anything v1.0 or newer works; v2.x is current.

## 2. Put this folder in place

Unzip or clone so that this README lives at `~/ai-lab/README.md`.
The Lima template mounts `~/ai-lab` into the VM by that exact path.

## 3. Create the VM

```
cd ~/ai-lab
limactl start ./ai-lab.yaml
```

First boot downloads an Ubuntu image (~600 MB) and installs Ollama inside
the VM. If your machine has 8 GB of RAM, edit `ai-lab.yaml` and change
`memory: "8GiB"` to `"4GiB"` before starting.

## 4. Pull the models (~2.3 GB)

```
limactl shell ai-lab ollama pull llama3.2:3b
limactl shell ai-lab ollama pull nomic-embed-text
```

## 5. Python setup (inside the VM)

```
cd ~/ai-lab
limactl shell ai-lab
```

You are now inside the VM, in this folder. Then:

```
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install requests chromadb
```

(The venv lives in the VM's home directory, not in the shared folder —
shared-folder filesystems and venvs don't always get along.)

## 6. Smoke test

Still inside the VM, with the venv active:

```
python3 smoke_test.py
```

Three check marks means you're ready. See you at the workshop!

If anything fails, see the Troubleshooting section at the end of the
companion blog post.
