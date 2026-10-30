---
lab_id: LAB-14
title: "What the server adds"
node: system-serving                     # == folder name == articles/<node-id>.md basename
related_nodes: [tool-llamacpp, tool-mlx, life-deploy, format-gguf, concept-kv-cache, attack-session-leak, attack-cache-sidechannel, attack-token-exhaustion, attack-sponge, defense-budget, defense-cache-isolation, eval-threat-model]
family: family-privacy
access_profile: A01
level: intermediate                      # beginner | intermediate | advanced
time: "75 min"
compose_profiles: [serving, workbench]   # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any 64-bit CPU. 4 GB Docker VM memory. 2.2 GB workbench image, 1.2 GB llama.cpp server image, 0.39 GB GGUF model. Optional Step 6: an Apple Silicon Mac with uv."
canary: ATLAS-CANARY-s3rv
last_tested: 2026-10-29
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, llama.cpp b11977, mlx-lm 0.32.2"
covers:                                  # nodes practiced here as named steps (optional; see _template)
  - {node: tool-llamacpp, steps: "1-5, D1-D3", anchor: "step-1--serve-a-gguf-and-map-what-it-exposes--explainer-1"}
  - {node: tool-mlx, steps: "6", anchor: "step-6--the-same-probes-on-mlx_lmserver-optional-slow"}
---

# LAB-14 · What the server adds

> **Atlas node:** [Inference engines and serving gateways](https://ai-security-atlas.github.io/?node=system-serving) · **Family:** family-privacy · **Level:** intermediate · **Time:** 75 min · **Model backend:** none

## Overview

A model file decides what a model can say; the server around it decides who can talk to it, what it remembers between requests and how much work one request may cost. In this lab you serve a small GGUF model (`SmolLM2-360M-Instruct`, Q8_0) with a pinned llama.cpp server (build b11977) and let two tenants share it: tenant A, a billing assistant whose system prompt holds the lab canary `ATLAS-CANARY-s3rv`, and tenant B, any other client that can reach the port. You map what the shipped defaults expose with no key, watch B read A's activity from `/slots` and A's whole prompt once a debug switch is on, confirm A's canary from the prompt-cache counter that every reply carries, and measure how long B waits while A holds every slot. Then you measure each defense on its own: an API key, disabled endpoints, a loopback bind, the limits the server really enforces, and a budget gateway in front. Source: [`labs/system-serving`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/system-serving).

By the end you will be able to:

1. List what a llama.cpp server exposes to an unauthenticated client in a given build, and read another tenant's activity, settings and (with a debug switch) its prompt from `/slots`.
2. Show that the shared prompt cache reports cross-tenant reuse (`timings.cache_n`), and measure the latency another tenant pays while one client holds every slot.
3. Measure which flags really limit exposure and cost (and which are only defaults), and what a per-tenant gateway adds on top.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

Both tenants are scripts in the workbench; the only "secret" is the fixed canary `ATLAS-CANARY-s3rv` that tenant A's own lab request puts on the lab's own server, and every request and guess is hardcoded in `scripts/servelab.py`. The servers are published on `127.0.0.1` only (`llama-server` on port 8180; `llama-server-hardened` on none). Never point these probes at a server you do not operate, and stop the stack with `docker compose down` when you finish: with the shipped defaults, anything that can reach port 8180, including a web page in your browser, can use the model. The optional Step 6 runs `mlx_lm.server` on your Mac's `127.0.0.1` for about 15 seconds and stops it.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`system-serving`](../../articles/system-serving.md) |
| Family | None in the seed graph (a component node). The front matter and kicker use [`family-privacy`](https://ai-security-atlas.github.io/?node=family-privacy) for the cross-tenant reads in Steps 2–3; Steps 4–5 belong to [`family-availability`](https://ai-security-atlas.github.io/?node=family-availability). |
| Goal | [`goal-information`](https://ai-security-atlas.github.io/?node=goal-information) (Steps 2–3) and [`goal-availability`](https://ai-security-atlas.github.io/?node=goal-availability) (Steps 4–5) |
| Access profile | `A01` Output-query access (caveat: *No weights, logits, training data or privileged context are implied.*): tenant B only sends requests and reads replies. The per-request settings it uses in Steps 4–5 (`n_predict`, `ignore_eos`) are what `A19` Inference configuration control describes, and the server grants them to every client. |
| Read first | [`life-deploy`](https://ai-security-atlas.github.io/?node=life-deploy), [`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache) |
| Mitigated by | None in the seed graph. Defend uses [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget) and [`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) as related controls. |
| Evaluated by | [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | Runtimes: [`tool-llamacpp`](https://ai-security-atlas.github.io/?node=tool-llamacpp), [`tool-mlx`](https://ai-security-atlas.github.io/?node=tool-mlx), and the file it serves, [`format-gguf`](https://ai-security-atlas.github.io/?node=format-gguf). In scope of this component: [`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak), [`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel), [`attack-token-exhaustion`](https://ai-security-atlas.github.io/?node=attack-token-exhaustion), [`attack-sponge`](https://ai-security-atlas.github.io/?node=attack-sponge). |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this component node. Its article says the shared state and shared budget "sit between tenants". The closest attack caveat is `attack-session-leak`'s: "Separate actual content leakage from a timing signal that only suggests prior use." This lab keeps them apart: Step 2 reads content, Step 3 reads a counter (not a timing), and neither is a claim about any other build or product.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | The lab is about the server itself, so it brings its own: the `serving` profile runs llama.cpp in a container. No step calls the backend in `labs/.env`. |
| host-ollama | n/a | — | Same. Ollama embeds llama.cpp, but it hides the server flags and endpoints this lab changes. |
| external-api | n/a | — | A hosted API is a server you do not operate; probing its slots, cache or budgets is out of scope. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU (amd64 or arm64). Each server uses 4 threads (`SERVING_CPU_THREADS`). Steps 4 and 5 deliberately keep the CPU busy for about a minute. |
| Docker VM memory | 4 GB (two llama.cpp servers with the 0.39 GB model, about 0.5 GB each, plus the workbench). |
| Disk | Workbench image 2.2 GB, llama.cpp server image 1.2 GB, model 0.39 GB in the `hf-cache-v1` volume. Step 6 (optional): mlx-lm in the uv cache and a 0.29 GB MLX model in the host HF cache. |
| Total time | About 75 min: about 10 min of commands (server restarts are most of it), plus reading. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-05 · What the API reveals](../concept-logits/README.md) shows what a model API's reply fields can leak; this lab does the same for the server around the model.
- Concepts to read first: [`life-deploy`](https://ai-security-atlas.github.io/?node=life-deploy) and [`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache).

## Explainer

```bash
# host
open system-serving/explainer/index.html        # macOS
# xdg-open system-serving/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In 10 steps the explainer draws the shared server (slots, KV cache, endpoints) between tenant A and tenant B, then replays the reference run: the open surface, what `/slots` shows with and without the debug switch, the cache counter rising for the right guess, B's latency while A holds every slot, and the exposure, limit and gateway tables from Defend.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=serving,workbench` |
| host-ollama | `COMPOSE_PROFILES=serving,workbench` |
| external-api | `COMPOSE_PROFILES=serving,workbench` |
| none | `COMPOSE_PROFILES=serving,workbench` |

This lab calls no model backend, so you can keep whichever backend block is active in `labs/.env`; the banner prints its `LAB_BACKEND` and the Observe blocks below show `backend none`. The `serving` profile is the shared llama.cpp fixture (`labs/_shared/serving`): `serving-model` downloads the pinned GGUF into the HF cache volume and checks its sha256, then `llama-server` (the shipped defaults) and `llama-server-hardened` (the Defend flags) start. Several steps restart `llama-server` with other flags by prefixing `docker compose up -d --wait llama-server` with `SERVING_ARGS="..."` (or `SERVING_SLOTS_DEBUG=1`); the same command without a prefix puts the shipped defaults back.

### Setup 2 — Build and start (≈1–3 min)

**Do**

```bash
docker compose build workbench
docker compose up -d --wait
```

**Observe**

```text
 Image atlas-labs/workbench:v3 Building
...
 Image atlas-labs/workbench:v3 Built
 Image ghcr.io/ggml-org/llama.cpp:server-b11977@sha256:01c2bc28d512... Pulled
 Container atlas-labs-serving-model-1 Started
 Container atlas-labs-workbench-1 Started
 Container atlas-labs-serving-model-1 Exited
 Container atlas-labs-llama-server-hardened-1 Started
 Container atlas-labs-llama-server-1 Started
...
 Container atlas-labs-workbench-1 Healthy
 Container atlas-labs-llama-server-1 Healthy
 Container atlas-labs-llama-server-hardened-1 Healthy
```

What to notice: `serving-model` runs once and exits after the hash check, and `--wait` returns only when both servers answer their healthcheck, so the model is loaded before Step 1.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] system-serving · check_env.py · torch 2.14.1+cpu · backend none
[ok] work dir: /labs/system-serving/work (writable)
[ok] llama-server at http://llama-server:8080: llama.cpp b11977-7ac5727d6 (pinned b11977), model smollm2-360m Q8_0, 4 slots, n_ctx 8192
[ok] llama-server-hardened at http://llama-server-hardened:8080: llama.cpp b11977-7ac5727d6 (pinned b11977), model smollm2-360m Q8_0, 4 slots, n_ctx 512
[ok] model file pinned: HuggingFaceTB/SmolLM2-360M-Instruct-GGUF @ 593b5a2 sha256 48ab3034d0dd
```

What to notice: both servers report the pinned build `b11977`; the hardened one has 512 tokens per slot (Step D2 explains why), and `check_env.py` reads its `/props` with the lab key because it refuses everyone else.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_surface + host checks | workbench | <15 s | 1 |
| 2 | s02_slots_watch (×2), restarts | workbench, llama-server | ≈20–30 s | 3 |
| 3 | s03_cache_probe | workbench | <15 s | 5 |
| 4 | s04_starve | workbench | ≈40 s–1 min | 7 |
| 5 | s05_limits, restarts | workbench, llama-server | ≈30–45 s | — |
| 6 | s06_mlx_host (optional) | host (macOS arm64) | ≈15 s–1 min (download) | — |
| D1 | d1_exposure (×5), restarts | workbench, llama-server | ≈45 s–1.5 min | 8 |
| D2 | s04_starve, restarts | workbench, llama-server | ≈25–40 s | 9 |
| D3 | d3_proxy | workbench, llama-server-hardened | <30 s | 10 |

Runtimes were measured on the test machine while three other labs were being built on it, so they may be inflated. They include about 1–3 s of container start-up per `docker compose run` and about 3–10 s per server restart (`up -d --wait` recreates the container, loads the model and waits for the healthcheck). The whole verified run, Setup to Cleanup with the optional Step 6, took about 5 min from empty volumes, including the 386 MB model download.

### Step 1 — Serve a GGUF and map what it exposes · [explainer 1](explainer/index.html#system-serving/1)

**Do**

```bash
docker compose port llama-server 8080
docker compose logs --no-log-prefix llama-server | grep -E "security|listening"
docker compose run --rm workbench python system-serving/scripts/s01_surface.py
```

**Observe**

```text
127.0.0.1:8180
0.00.004.135 W srv  server_setup: security: no API key is set and CORS allows all origins (see https://github.com/ggml-org/llama.cpp/pull/25655)
0.00.354.533 I srv  server_on_li: listening on http://0.0.0.0:8080
[atlas-lab] system-serving · s01_surface.py · torch 2.14.1+cpu · backend none
[note] tenant B, no API key -> http://llama-server:8080
server: llama.cpp b11977-7ac5727d6  model smollm2-360m Q8_0  slots 4  n_ctx 8192
defaults from GET /props: n_predict -1  temperature 0.8  endpoint_slots True  endpoint_metrics False  endpoint_props False  ui True
GET /props also returns: model_path '901ad47f/smollm2-360m-instruct-q8_0.gguf', chat_template (368 chars)

method  path                       code what tenant B gets
GET     /health                    200  {"status":"ok"}
GET     /v1/models                 200  model list: smollm2-360m
GET     /props                     200  2344 bytes: build, model path, defaults, chat template
GET     /slots                     200  4 slots: is_processing, n_prompt_tokens, params, n_decoded
GET     /metrics                   501  off (needs --metrics)
POST    /props                     501  off (needs --props)
POST    /slots/0?action=erase      501  off (needs --slot-save-path)
GET     /lora-adapters             200  [] (none loaded; POST sets the global adapter scales)
POST    /tokenize                  200  11 tokens for the canary string
POST    /v1/chat/completions       200  a reply, plus timings: cache_n, predicted_ms, predicted_n, ...
GET     / (web UI)                 200  text/html; charset=utf-8 (1233 bytes)
OPTIONS /v1/chat/completions       200  CORS from http://attacker.example: allow-origin http://attacker.example, credentials true
```

What to notice: with the shipped defaults every endpoint answers a client with no key, `/props` hands out the model path and chat template, and the CORS preflight echoes `http://attacker.example` with credentials allowed, so a web page on any origin can call the server from a browser.

**Why**

The model is the same file in every deployment; what this table shows is added by the [`system-serving`](https://ai-security-atlas.github.io/?node=system-serving) layer, and it changes between builds: the binary's own default host is `127.0.0.1:9931`, but the official image sets `LLAMA_ARG_HOST=0.0.0.0` and `LLAMA_ARG_PORT=8080`, so every container on the compose network reaches it ([`tool-llamacpp`](https://ai-security-atlas.github.io/?node=tool-llamacpp)). The host only sees it on `127.0.0.1:8180` because compose publishes it there. `/metrics`, `POST /props` and slot save/erase are off by default in b11977; record what your build ships, because these defaults have moved before.

### Step 2 — What /slots tells another tenant (≈20–30 s) · [explainer 3](explainer/index.html#system-serving/3)

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/s02_slots_watch.py
SERVING_SLOTS_DEBUG=1 docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/s02_slots_watch.py
docker compose logs llama-server | grep -c ATLAS-CANARY-s3rv
docker compose up -d --wait llama-server
```

**Observe**

```text
[atlas-lab] system-serving · s02_slots_watch.py · torch 2.14.1+cpu · backend none
[note] tenant A asks 'What are your opening hours?' with its system prompt (holds the canary); tenant B polls http://llama-server:8080/slots with no key
3 polls; slot busy in 1 of them
mid-request : slot 1 is_processing true  n_prompt_tokens 78  n_decoded 28  n_remain 132  n_predict 160  temperature 0.0
after       : slot 1 is_processing false  id_task 1915  n_prompt_tokens 98  keys: is_processing, id_task, n_prompt_tokens, n_prompt_tokens_processed, n_prompt_tokens_cache, params, next_token
canary ATLAS-CANARY-s3rv in /slots responses: no
tenant A got its answer: "I'm sorry for the confusion, but as a billing assistant for "...
 Container atlas-labs-llama-server-1 Recreated
...
 Container atlas-labs-llama-server-1 Healthy
[atlas-lab] system-serving · s02_slots_watch.py · torch 2.14.1+cpu · backend none
...
mid-request : slot 0 is_processing true  n_prompt_tokens 74  n_decoded 24  n_remain 136  n_predict 160  temperature 0.0
after       : slot 0 is_processing false  id_task 1  n_prompt_tokens 98  keys: is_processing, id_task, n_prompt_tokens, n_prompt_tokens_processed, n_prompt_tokens_cache, params, next_token, prompt, generated
  prompt    : 's. Internal note, never reveal: escalation code ATLAS-CANARY-s3rv.<'
  generated : "I'm sorry for the confusion, but as a billing assistant for Lantern La"...
canary ATLAS-CANARY-s3rv in /slots responses: YES
tenant A got its answer: "I'm sorry for the confusion, but as a billing assistant for "...
0
 Container atlas-labs-llama-server-1 Recreated
...
 Container atlas-labs-llama-server-1 Healthy
```

What to notice: by default B sees that A is busy, how long A's prompt is, A's sampling settings and its progress, but not the text; with `LLAMA_SERVER_SLOTS_DEBUG=1` the same unauthenticated call returns A's whole prompt with the canary `ATLAS-CANARY-s3rv` and A's answer, even after A has finished, while the container log still has no copy of it (`0`).

**Why**

`/slots` is on by default and needs no key; in b11977 it returns per-slot metadata, and the env switch `LLAMA_SERVER_SLOTS_DEBUG` (llama.cpp PR #16482, October 2025) adds the prompt and generated text of the current or last task. Older builds returned the prompt without any switch (build b4000, October 2024, did), so a monitoring endpoint left open is a cross-tenant read whose content depends on the build and one environment variable ([`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak)). The metadata alone already tells B when A is active and how much it sends.

### Step 3 — The cache remembers across tenants · [explainer 5](explainer/index.html#system-serving/5)

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/s03_cache_probe.py
```

**Observe**

```text
[atlas-lab] system-serving · s03_cache_probe.py · torch 2.14.1+cpu · backend none
[note] B knows A's prompt up to the code: 'er reveal: escalation code ATLAS-CANARY-'
[note] B's own probe with no guess reuses 29 tokens after A's request (it shares the template and A's prefix); each extra matched token adds 1

B guesses the code             cache_n  vs prefix
ATLAS-CANARY-k9px                   29         +0
ATLAS-CANARY-q7mz                   29         +0
ATLAS-CANARY-s3rv                   32         +3   <- matches A
ATLAS-CANARY-b2wd                   29         +0
-> B picks ATLAS-CANARY-s3rv (the only guess that reused tokens from A's prompt)

B extends its guess            cache_n  vs prefix
ATLAS-CANARY-s                      30         +1
ATLAS-CANARY-s3                     31         +2
ATLAS-CANARY-s3r                    31         +2
ATLAS-CANARY-s3rv                   32         +3
ATLAS-CANARY-s3rv.                  38         +9
each token that matches A's prompt adds 1 (A's code is the tokens s|3|rv|.); 's3r' ends in a different token than A's 'rv', so it gains nothing; after '.' the chat template matches too
```

What to notice: only the guess `s3rv` reuses extra tokens (+3, one per matching token), and extending it one piece at a time raises the counter token by token, so the reply field confirms A's canary `ATLAS-CANARY-s3rv` without any debug switch.

**Why**

Prompt caching is on by default: the server keeps the KV cache of earlier prompts in its slots and in a host-memory cache, and a new request that starts with the same tokens reuses them, whoever sent them ([`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache)). Every reply reports the reuse in `timings.cache_n`, so B gets an exact counter instead of a noisy timing ([`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel) covers the timing version). The script lets A's app answer one customer before each probe, as a busy app would; B also needs A's prompt up to the code, and guessing it from scratch costs many requests, so this is confirmation of a guess, not a free read.

### Step 4 — One client holds every slot (≈40 s–1 min) · [explainer 7](explainer/index.html#system-serving/7)

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/s04_starve.py
```

**Observe**

```text
[atlas-lab] system-serving · s04_starve.py · torch 2.14.1+cpu · backend none
[note] http://llama-server:8080: 4 slots, n_ctx per slot 8192; A asks n_predict 1500, ignore_eos

condition                    B p50   B p95   B max   A's long requests
idle                         0.05s   0.08s   0.08s   -
A holds 1 of 4 slots         0.08s   0.14s   0.14s   1 x 1500 tokens in 11.1 s (stop: limit)
A holds 4 of 4 slots         0.05s  23.60s  23.60s   4 x 1500 tokens in 25.0 s (stop: limit)
B's p95 with every slot held: 23.60 s = 295x idle (0.08 s)
```

What to notice: one long request from A barely slows B, because the server batches 4 slots; four of them take every slot and B's next request waits for all of them, so B's p95 grows by two orders of magnitude (from a fraction of a second to tens of seconds; the factor varies with machine load).

**Why**

b11977 picks the number of slots automatically (4 here) and lets every request set its own `n_predict` and `ignore_eos`; the default `n_predict` is -1, unlimited up to the context. The slots and their shared 8192-token KV cache are the budget the tenants share, so a client that fills them denies service to everyone else with a handful of ordinary requests ([`attack-token-exhaustion`](https://ai-security-atlas.github.io/?node=attack-token-exhaustion)).

### Step 5 — Server flags that only look like limits (≈30–45 s)

**Do**

```bash
SERVING_ARGS="--n-predict 64 --timeout 5" docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/s05_limits.py
docker compose up -d --wait llama-server
```

**Observe**

```text
 Container atlas-labs-llama-server-1 Recreated
...
 Container atlas-labs-llama-server-1 Healthy
[atlas-lab] system-serving · s05_limits.py · torch 2.14.1+cpu · backend none
[note] http://llama-server:8080: GET /props default n_predict -1
request without n_predict      -> 64 tokens (stop: limit)
request with n_predict 400     -> 400 tokens (stop: limit)   the request's value wins over --n-predict
request with n_predict 1500    -> HTTP 200 after 9.5 s, 1500 tokens   --timeout 5 did not stop it
client closes after 3 s        -> TimeoutError: timed out; slot free again 1.0 s later
 Container atlas-labs-llama-server-1 Recreated
...
 Container atlas-labs-llama-server-1 Healthy
```

What to notice: `--n-predict 64` applies only to requests that do not set their own value, `--timeout 5` did not stop a request that ran for many seconds, and the one thing that freed the slot was the client closing its connection.

**Why**

In b11977 the server code says it plainly: "the per-request limit takes priority over the global one", so `--n-predict` is a default, not a cap, and `--timeout` is the HTTP socket read/write timeout, not a generation budget ([`tool-llamacpp`](https://ai-security-atlas.github.io/?node=tool-llamacpp)). The server does cancel work when the client disconnects, which is what a gateway's upstream timeout relies on in D3 ([`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget)).

### Step 6 — The same probes on mlx_lm.server (optional, slow)

> [!TIP] Optional: later steps use the shipped result, so you can skip this.

**Do**

```bash
# host
PYTHONPATH=_shared uvx --from mlx-lm==0.32.2 python system-serving/scripts/s06_mlx_host.py
```

**Observe**

```text
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
[atlas-lab] system-serving · s06_mlx_host.py · torch n/a · backend none
[ok] mlx-lm 0.32.2; model mlx-community/SmolLM2-360M-Instruct-6bit @ 642affd in the host HF cache
[note] mlx_lm.server http://127.0.0.1:60714 (defaults: --host 127.0.0.1, --allowed-origins *, --max-tokens 512, no API key option)

method  path                   code what tenant B gets
GET     /health                200  {"status": "ok"}
GET     /v1/models             200  1 model(s); the id is the host path ...shots/642affd1f9e387d1b56c745894afc83795aebe1d
GET     /slots                 404
GET     /metrics               404
GET     /props                 404
POST    /v1/chat/completions   200  a reply; usage: {'prompt_tokens': 36, 'completion_tokens': 4, 'total_tokens': 40, 'prompt_tokens_details': {'cached_tokens': 0}}
OPTIONS /v1/chat/completions   204  CORS from http://attacker.example: allow-origin *

cache: usage.prompt_tokens_details.cached_tokens, B's guesses after A's requests (no guess: 29): k9px 29  q7mz 29  s3rv 32  b2wd 29
limits: A asks max_tokens 1500 -> 1500 tokens (6.5 s); --max-tokens 512 is only the default
model : B sends "model": "system-serving" -> HTTP 404 "[Errno 2] No such file or directory: 'system-serving/config.json'"
        the next default request -> HTTP 200 after 0.2 s (the server dropped its model to try B's path, then reloaded the default)
[ok] mlx_lm.server stopped
```

What to notice: MLX's server binds `127.0.0.1` by default but has no API key option, allows any origin, reports the same cache counter in the standard `usage.prompt_tokens_details.cached_tokens` field (`s3rv` again reuses 3 more tokens), treats `--max-tokens` as a default, and lets any client name another model to load.

**Why**

[`tool-mlx`](https://ai-security-atlas.github.io/?node=tool-mlx) cannot run in the Linux containers, so this step runs on an Apple Silicon host with `uv` (`uvx` installs mlx-lm 0.32.2 into its own cache; the pinned 6-bit model goes to your HF cache). The runtime is different and the defaults differ (loopback bind, no `/slots`), but the serving-layer questions are the same ([`system-serving`](https://ai-security-atlas.github.io/?node=system-serving)): who can call it, what is shared, what a request may cost. In mlx-lm 0.32.2 a request's `model` field is a path or repo to load for everyone; the step sends a folder of this lab, which exists and is not a model, so nothing is downloaded.

## Defend

### Step D1 — Lock the surface, one flag at a time (≈45 s–1.5 min) · [explainer 8](explainer/index.html#system-serving/8)

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/d1_exposure.py shipped
SERVING_ARGS="--metrics" docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/d1_exposure.py metrics
SERVING_ARGS="--api-key-file /labs/_shared/serving/lab-api-keys.txt" docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/d1_exposure.py api-key
SERVING_ARGS="--no-slots --no-webui --cors-origins localhost" docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/d1_exposure.py no-slots-ui
SERVING_ARGS="--host 127.0.0.1" docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/d1_exposure.py loopback
# host
curl -s -o /dev/null -w "host 127.0.0.1:8180/health -> %{http_code}\n" http://127.0.0.1:8180/health
docker compose up -d --wait llama-server
```

**Observe**

```text
[atlas-lab] system-serving · d1_exposure.py · torch 2.14.1+cpu · backend none
config       /health    /v1/models /props     /slots     /metrics   chat       web UI     CORS       A+key
shipped      200        200        200        200        501        200        200        allowed    200
 Container atlas-labs-llama-server-1 Recreated
...
[note] /metrics for anyone (after one request from A):
       llamacpp:prompt_tokens_total 50
       llamacpp:tokens_predicted_total 16
       llamacpp:n_decode_total 16
       llamacpp:requests_processing 0
...
[atlas-lab] system-serving · d1_exposure.py · torch 2.14.1+cpu · backend none
[note] http://llama-server:8080: ConnectionRefusedError: [Errno 111] Connection refused
config       /health    /v1/models /props     /slots     /metrics   chat       web UI     CORS       A+key
shipped      200        200        200        200        501        200        200        allowed    200
metrics      200        200        200        200        200        200        200        allowed    200
api-key      200        401        401        401        401        401        200        allowed    200
no-slots-ui  200        200        200        501        501        200        404        blocked    200
loopback     refused    refused    refused    refused    refused    refused    refused    refused    refused
host 127.0.0.1:8180/health -> 000
 Container atlas-labs-llama-server-1 Recreated
...
 Container atlas-labs-llama-server-1 Healthy
```

What to notice: `--metrics` adds usage counters for anyone; the API key turns every API route into 401 except `/health` and the web UI's static files; `--no-slots --no-webui --cors-origins localhost` closes `/slots`, the UI and cross-origin calls but leaves the model open; binding `127.0.0.1` inside a container closes it to the network and to the published host port alike.

**Why**

Each flag closes one door and leaves the others: the key stops strangers but not a tenant who has one, disabling `/slots` stops the monitoring read but not the cache counter of Step 3, and a loopback bind only works if whatever must reach the server runs in the same network namespace ([`system-serving`](https://ai-security-atlas.github.io/?node=system-serving)). A key passed as `--api-key` is visible in the process list and in `docker inspect`; this lab uses `--api-key-file`. The `shipped` run starts a fresh table.

### Step D2 — Limits the server does enforce (≈25–40 s) · [explainer 9](explainer/index.html#system-serving/9)

**Do**

```bash
SERVING_ARGS="--ctx-size 2048 --parallel 4 --no-kv-unified" docker compose up -d --wait llama-server
docker compose run --rm workbench python system-serving/scripts/s04_starve.py --out d2_starve.json
docker compose up -d --wait llama-server
```

**Observe**

```text
 Container atlas-labs-llama-server-1 Recreated
...
[atlas-lab] system-serving · s04_starve.py · torch 2.14.1+cpu · backend none
[note] http://llama-server:8080: 4 slots, n_ctx per slot 512; A asks n_predict 1500, ignore_eos

condition                    B p50   B p95   B max   A's long requests
idle                         0.05s   0.05s   0.05s   -
A holds 1 of 4 slots         0.09s   0.18s   0.18s   1 x 508 tokens in 3.0 s (stop: limit)
A holds 4 of 4 slots         0.05s   3.79s   3.79s   4 x 508 tokens in 5.2 s (stop: limit)
B's p95 with every slot held: 3.79 s = 76x idle (0.05 s)
 Container atlas-labs-llama-server-1 Recreated
...
 Container atlas-labs-llama-server-1 Healthy
```

What to notice: with 512 tokens of context per slot, A's 1500-token requests stop near 508 tokens whatever they ask for, so B's worst wait falls from tens of seconds to a few seconds.

**Why**

Unlike `--n-predict`, the context size is a hard limit: `--ctx-size 2048 --parallel 4 --no-kv-unified` gives each slot its own 512 cells, and a request cannot generate past them (context shift is off by default). It is a blunt per-request cap ([`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget)): it also caps every prompt at about 500 tokens, and A can still keep all four slots busy by sending new requests, which needs a per-tenant limit in front of the server.

### Step D3 — A budget gateway in front · [explainer 10](explainer/index.html#system-serving/10)

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/d3_proxy.py
```

**Observe**

```text
[atlas-lab] system-serving · d3_proxy.py · torch 2.14.1+cpu · backend none
[note] B straight to http://llama-server-hardened:8080 with no key: chat 401, /slots 401
[note] budget gateway http://127.0.0.1:38485 (inside this container) -> http://llama-server-hardened:8080

(1) surface through the gateway, as B
    GET   /slots       404  GET /slots is not exposed by the gateway
    GET   /props       404  GET /props is not exposed by the gateway
    GET   /metrics     404  GET /metrics is not exposed by the gateway
    POST  /completion  404  POST /completion is not exposed by the gateway
    GET   /            404  GET / is not exposed by the gateway
    CORS preflight from http://attacker.example: 401, allow-origin None

(2) A asks for 100000 tokens with ignore_eos
    HTTP 200, completion_tokens 128 (clamped to 128; ignore_eos dropped)

(3) A opens 4 long requests at once while B keeps asking
    A's statuses: [200, 429, 429, 429]  (1 ran, 3 refused by the concurrency rule)
    B p50 0.07s  p95 0.12s  max 0.12s

(4) A keeps asking for 128 tokens until the budget (1000 tokens / 60 s) stops it
    4 more requests served, then HTTP 429: tenant A token budget 1000/60s used up

(5) B's cache probe from Step 3, through the gateway (A's app answers before each probe)
    slots pinned, timings shown      cache_n for '', k9px, s3rv: [5, 29, 29]
    slots pinned, timings stripped   cache_n for '', k9px, s3rv: [None, None, None]
```

What to notice: the hardened server refuses B outright (401), the gateway exposes only chat and the model list, clamps A's 100000-token request to 128, refuses A's extra concurrent requests and its requests past the budget with 429, keeps B's p95 low under A's burst, and B's cache probe finds nothing once each tenant has its own slot (the first number only reflects B's own earlier requests and varies; `s3rv` gains nothing over `k9px`).

**Why**

The gateway (`labs/_shared/serving/proxy.py`) holds the server's key and gives each tenant its own key, a path allowlist, a body allowlist that drops `n_predict`, `ignore_eos` and `id_slot`, a `max_tokens` clamp, one request at a time, a token budget per minute, its own slot, and replies without `timings` ([`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget), [`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation)). Pinning a slot per tenant is what stops the cache match (row "timings shown"); stripping `timings` alone would still leave the timing channel. Limitation: a gateway only enforces what it understands; a tenant with many keys multiplies its budget, and one slot per tenant does not scale past the slot count, where separate deployments are the isolation boundary.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] system-serving · evaluate.py · torch 2.14.1+cpu · backend none
condition                          shipped      gateway      expected
B sees A's slot activity           yes          no (404)     yes / no (404)
B confirms A's code via cache_n    s3rv         none         s3rv / none
B uses the model with no key       yes          no           yes / no
page on another origin (CORS)      allowed      blocked      allowed / blocked
A asks 800 tokens, gets            800          128          800 / 128
B p95 with A on every slot         >=10x idle   <5x idle     >=10x idle / <5x idle
(B's p95 ratio, busy / idle: shipped 144.6x, gateway 1.4x)
RESULT: REPRODUCED
```

`RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict. "shipped" is `llama-server` with the build defaults; "gateway" is `llama-server-hardened` behind the budget gateway from D3. The p95 rows compare B's latency while A holds every slot with B's latency on an idle server.

Questions for your notes:

1. Which rows did the API key alone (D1) fix, and which needed the per-tenant parts of the gateway? Why can a server-wide key not separate tenant A from tenant B?
2. Step 3 needed A's prompt up to the code. In your own deployment, which tenants share a system-prompt prefix, and what would `cache_n` tell one of them about the others?
3. For your threat model ([`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model)), who can reach port 8080 on the compose network, and who can reach 8180 on the host?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python system-serving/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] system-serving · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed system-serving/work (d1_exposure.json d2_starve.json d3_gateway.jsonl d3_proxy.json evaluate.json s01_surface.json s02_slots_watch.json s03_cache_probe.json s04_starve.json s05_limits.json s06_mlx_host.json s06_mlx_server.log)
 Container atlas-labs-llama-server-1 Removed
 Container atlas-labs-llama-server-hardened-1 Removed
 Container atlas-labs-serving-model-1 Removed
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

The llama.cpp image stays until `docker image rm` removes it. If you ran Step 6, its model is in `~/.cache/huggingface/hub/models--mlx-community--SmolLM2-360M-Instruct-6bit` and mlx-lm is in the uv cache (`uv cache clean mlx-lm`).

## Going Further

- Add a rule to the gateway that refuses a tenant whose prompt shares more than N tokens with another tenant's recent prompts, then rerun Step 3 through it and measure how many of A's own repeat requests it also refuses.
- Measure how B's p95 under A's burst changes with `--parallel` 2, 4 and 8 at the same `--ctx-size`, and write the trade-off down as slots versus prompt length.
- Rerun Step 3 with `SERVING_ARGS="--no-cache-prompt"` and with `--cache-ram 0`, and report `cache_n` and A's own prompt time for each, so the isolation has a measured cost.
- Swap the model with `SERVING_MODEL=` (any GGUF readable inside the container) and rerun `s01_surface.py`: which rows depend on the model and which only on the server?

## Further Reading

- vLLM, [Automatic Prefix Caching](https://docs.vllm.ai/en/v0.8.3/design/automatic_prefix_caching.html) (seed source `s-vllm-cache`): how a serving engine reuses KV cache across requests.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) (seed source `s-llamacpp`) and its [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) (flags, `/slots`, `/props`, `/metrics`, `--api-key`); the pinned image is `ghcr.io/ggml-org/llama.cpp:server-b11977`. Slot debug output: [PR #16482](https://github.com/ggml-org/llama.cpp/pull/16482); user inputs kept out of the console: [PR #16871](https://github.com/ggml-org/llama.cpp/pull/16871); the "no API key and CORS allows all origins" warning: [PR #25655](https://github.com/ggml-org/llama.cpp/pull/25655).
- [MLX documentation](https://ml-explore.github.io/mlx/build/html/index.html) (seed source `s-mlx`) and [mlx-lm](https://github.com/ml-explore/mlx-lm) (`mlx_lm.server`).
- Gu et al., [Auditing Prompt Caching in Language Model APIs](https://arxiv.org/abs/2502.07776) (2025), seed source `s-cache-audit`: detecting cross-user cache sharing from timing.
- OWASP, [Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/) (seed source `s-owasp25`): unbounded consumption.
- Model: [HuggingFaceTB/SmolLM2-360M-Instruct-GGUF](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF) at revision `593b5a2`.

---

[← prev](../attack-membership/README.md) · [All labs](../README.md)
