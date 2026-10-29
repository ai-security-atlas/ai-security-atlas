# Lab requirements and model backends

Everything runs in Docker. Python, PyTorch and the scanners live in the workbench image, so you need no Python on your host to do the labs.

## Host requirements

| Need | Minimum |
| :--- | :--- |
| Docker | Docker 24 or newer with Compose 2.20.0 or newer (`docker compose version`). Tested with Docker 29.8.2, Compose v5.5.0, OrbStack, macOS 15 arm64. |
| Docker VM memory | 4 GB for the workbench alone (LAB-02 peaks at about 2.2 GiB during PGD), plus about 4 GB if container Ollama runs `qwen2.5vl:3b` alongside. |
| Host RAM | 8 GB minimum, 16 GB recommended. |
| CPU | Any 64-bit CPU (linux/amd64 or linux/arm64 images). Everything is CPU-only in Docker. |

Disk:

| Item | Size | Needed for |
| :--- | :--- | :--- |
| Workbench image `atlas-labs/workbench:v2` | 2.2 GB (measured on arm64, with torchvision; v1 was 1.8 GB) | every lab |
| Ollama image | 7.08 GB on arm64; the amd64 image ships CUDA/ROCm libraries and is larger | backend a only |
| Open WebUI slim image | 904 MB | the `chat` profile |
| Models | `qwen2.5vl:3b` 3.2 GB, `moondream:1.8b` 1.7 GB, SmolVLM-256M 518 MB (HF cache) | labs that use them |

All images are published for linux/amd64 and linux/arm64.

## Pick a model backend

Some labs need no model backend at all (their README says `Model backend: none`). For the others, pick one backend and keep only its block uncommented in `.env`:

| Your machine | Backend |
| :--- | :--- |
| Apple Silicon | b (host Ollama uses Metal; Docker on macOS has no GPU) |
| Linux with an NVIDIA/AMD GPU | b (container Ollama is CPU-only in v1) |
| Linux/Windows CPU only, or CI | a |
| Weak laptop | c, for the steps tagged external-api; or no backend (labs still run their main path) |

- **a = container-ollama:** Ollama runs in Docker (profile `ollama`); `docker compose up -d` also pulls the models listed in `LAB_MODELS`.
- **b = host-ollama:** Ollama runs on your host; containers reach it at `host.docker.internal:11434`.
- **c = external-api:** an OpenAI-compatible endpoint.

Scripts always run in the `workbench` or `sandbox` service. The backend only answers model calls.

## Host Ollama (backend b)

- **macOS:** run the Ollama app or `ollama serve`, then pull the models: `ollama pull qwen2.5vl:3b` and `ollama pull moondream:1.8b`.
- **Linux:** the installer's systemd unit already binds 11434 on loopback, so `OLLAMA_HOST=0.0.0.0 ollama serve` fails with "address already in use". Run `sudo systemctl edit ollama`, add

  ```ini
  [Service]
  Environment="OLLAMA_HOST=172.17.0.1:11434"
  ```

  using the Docker bridge IP from `ip -4 addr show docker0`, then run `sudo systemctl restart ollama`.
- **Warning:** never bind Ollama to `0.0.0.0` on a shared or untrusted network. It has no authentication, so anyone on the LAN can use it. If you cannot bind to the bridge IP, use backend a.
- **Version:** labs were tested with host Ollama 0.32.5, while the container image is 0.40.11, so behavior may differ between backends a and b.

## Container Ollama tuning (backend a)

Set `OLLAMA_CPU_THREADS` in `.env` to about half of `docker info --format '{{.NCPU}}'`. The default of 8 oversubscribes a 4-core laptop. Without a thread limit, Ollama in Docker can stall under load.

## External API (backend c)

Prefer an OpenAI-compatible server you run yourself (vLLM or llama.cpp on another machine you own). If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Lab scripts print the endpoint before they send anything. v1 was tested only against Ollama's OpenAI-compatible `/v1` endpoint as a stand-in for a hosted provider; hosted vision models may refuse or filter requests.

## Open WebUI (profile `chat`)

- Open WebUI runs at http://127.0.0.1:3000 with authentication off and `ENABLE_PERSISTENT_CONFIG=False`, so `.env` stays the source of truth.
- After switching backends, run `docker compose up -d --force-recreate open-webui`. For a full reset, run `docker compose down -v`.
- With auth off, anyone who can reach 127.0.0.1:3000 is admin. The ports are bound to loopback, but on a shared multi-user machine every local user can reach them, so run `docker compose down` as soon as you finish.

## Build once

```bash
docker compose build workbench
```

Building v2 on top of a cached v1 took about 45 s on an M4 Max; a first build also downloads the PyTorch wheels and takes longer. v2 adds peft, accelerate, scikit-learn, fastapi, uvicorn, httpx, pydantic and matplotlib to v1 and keeps every v1 pin. If your `labs/.env` was copied before v2 and still says `WORKBENCH_TAG=v1`, change it to `v2` and build again. Check the result:

```bash
docker compose run --rm workbench python -c "import torch,torchvision,transformers,safetensors,fickling;print(torch.__version__,torchvision.__version__,transformers.__version__)"
```

It must print `2.14.1+cpu 0.29.1+cpu 5.20.2`.

## Linux notes

- Set `LAB_UID` and `LAB_GID` in `.env` to the output of `id -u` and `id -g`, so the `work/` folders the containers write in your checkout stay yours.
- SELinux hosts need `:z` on bind mounts (`./:/labs:z`). This is untested.
- Rootless Docker and Podman handle `host-gateway` and UID mapping differently and are unsupported in v1.
