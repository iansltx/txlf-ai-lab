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

That exact host path matters: `ai-lab.yaml` shares `~/ai-lab` with the VM, and
inside the VM it appears as `~/ai-lab` too. If you clone somewhere else, the VM
still boots fine but `~/ai-lab` there is empty — Lima quietly creates a blank
`~/ai-lab` on the host and shares that instead.

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

From the host:

```
limactl shell ai-lab
```

Then, inside the VM, go to the shared folder and set up Python:

```
cd ~/ai-lab
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install requests chromadb
```

(The venv lives in the VM's home directory, not in the shared folder —
shared-folder filesystems and venvs don't always get along.)

If `limactl shell` printed `cd: /Users/you/ai-lab: No such file or directory`
before your prompt, that is harmless: the folder is mounted at `~/ai-lab` in
the VM rather than at its host path, so the shell just falls back. `cd ~/ai-lab`
is always the way in.

## 6. Smoke test

Still inside the VM, with the venv active:

```
cd ~/ai-lab
python3 smoke_test.py
```

Three check marks means you're ready. See you at the workshop!

If anything fails, see the Troubleshooting section at the end of the
companion blog post.

---

## Option B: the GPU lab (Apple Silicon only)

Everything above runs the model on the VM's CPU. On an Apple Silicon Mac with
macOS 14 or newer there is a second template, `ai-lab-gpu.yaml`, for the same
lab on Lima's `krunkit` driver. It puts the Mac's GPU *inside* the VM as a
Vulkan device (Mesa's Venus driver), and `llama-bench` on an M1 Max reports
567 tokens/s of prompt processing and 42 tokens/s of generation for our 3B
model, entirely on the GPU.

Two caveats worth having up front:

- **Ollama stays on the CPU.** Its Linux builds ship CPU and CUDA runners, no
  Vulkan, so it cannot see this GPU. The RAG labs are unaffected — they keep
  working, on the CPU. The GPU path is llama.cpp, in a container.
- **Ubuntu's own Mesa cannot drive the GPU.** Venus support is a patched Mesa,
  which is why the GPU path runs a Fedora-based container image and installs
  nothing into the guest.

If you already built the CPU lab, keep it. `vmType` cannot be changed on an
existing instance, so this is a *second* VM next to `ai-lab` — and there is
nothing to re-download: the Ubuntu image is already cached, and step B4 reuses
the model you already pulled.

### B1. Host setup (one time)

```
brew tap slp/krun
brew trust slp/krun            # Homebrew >= 4.6 asks before running a third-party tap
brew install krunkit
krunkit --version              # 1.3.2 or newer
limactl --version              # 2.0 or newer; the krunkit driver ships with Lima
```

### B2. Keep the shared folder a real folder

`krunkit` shares the workshop folder over virtiofs, and it does not accept a
*symlink* as that path: the VM dies mid-boot with

```
virtio_fs: failed to create worker: Message too long (os error 40)
Failed to activate device: BadActivate
```

and `limactl start` reports `did not receive an event with the 'running' status`.
The `vz` driver used by the CPU lab follows symlinks fine, so this only affects
Option B.

```
ls -ld ~/ai-lab      # 'd' at the start means a real folder; 'l' means a symlink
```

If it is a symlink, point the template at the real path rather than moving
anything around:

```
cd ~/ai-lab && pwd -P                       # e.g. /Users/you/code/ai-lab
limactl start --set '.mounts[0].location="/Users/you/code/ai-lab"' ./ai-lab-gpu.yaml
```

### B3. Start the GPU VM

```
cd ~/ai-lab
limactl start ./ai-lab-gpu.yaml
```

Both instances forward guest port 11434, so they cannot run side by side on the
host. Stop the CPU VM while this one runs (`limactl stop ai-lab`), or give this
one a different port with `--set '.portForwards[0].hostPort=11435'`.

### B4. Bring a model over, without downloading it again

If you already pulled `llama3.2:3b` in the CPU VM, the weights are one blob on
that VM's disk. Copy it out through the shared folder, from inside the CPU VM:

```
limactl shell ai-lab
mkdir -p ~/ai-lab/models
sudo find /usr/share/ollama/.ollama/models/blobs -type f -size +1G \
  -exec cp {} ~/ai-lab/models/llama3.2-3b.gguf \;
exit
```

`-size +1G` picks the 1.9 GB model rather than the embedding blob, which is an
order of magnitude smaller. No CPU VM? Fetch the same weights directly instead:

```
mkdir -p ~/ai-lab/models
curl -L -o ~/ai-lab/models/llama3.2-3b.gguf \
  https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

(`models/` is git-ignored; the weights never enter the repo.)

### B5. Run the model on the GPU

```
limactl shell ai-lab-gpu
cd ~/ai-lab
nerdctl run --rm -ti --device /dev/dri -v ~/ai-lab/models:/models \
  ghcr.io/unsuman/fedora-vgpu-llama \
  llama-cli -m /models/llama3.2-3b.gguf -ngl 99 -st -p "Say hello in exactly five words."
```

`-ngl 99` puts every layer on the GPU. The image is about 900 MB and carries the
patched Mesa plus a Vulkan build of llama.cpp; `nerdctl` itself comes with Lima.
The first run prints the device it found —
`Vulkan0: Virtio-GPU Venus (Apple M1 Max)` — and the answer ends with
`[ Prompt: 202.4 t/s | Generation: 46.7 t/s ]`.

Keep `-ti` on that command. Without a terminal, `llama-cli` falls into its chat
loop, reads end-of-file forever and fills the VM's disk with prompt markers.

To check the GPU without loading a model, or to benchmark it:

```
nerdctl run --rm --device /dev/dri ghcr.io/unsuman/fedora-vgpu-llama llama-cli --list-devices
nerdctl run --rm --device /dev/dri -v ~/ai-lab/models:/models \
  ghcr.io/unsuman/fedora-vgpu-llama llama-bench -m /models/llama3.2-3b.gguf -ngl 99 -p 128 -n 32
```

### B6. What still runs on the CPU

The RAG labs are unchanged: step 4's `ollama pull`, `ingest.py`, `search.py` and
`ask.py` all work in this VM, on the CPU. If you want generation on the GPU as
well, the same image ships `llama-server`, which speaks the OpenAI-compatible
API on port 8080 (already forwarded by the template), and `ask.py`'s single
`requests.post` to `/api/chat` becomes a call to `/v1/chat/completions`.

On a 16 GB Mac run one instance at a time: each template asks for 8 GiB.
