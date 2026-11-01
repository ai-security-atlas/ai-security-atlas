---
lab_id: LAB-38
title: "The cache remembers"
node: concept-kv-cache
related_nodes: [concept-attention, arch-ssm, tool-vllm, system-serving, attack-cache-sidechannel, attack-session-leak, defense-cache-isolation, concept-tokens, eval-privacy, eval-threat-model]
family: family-privacy
access_profile: A14
level: intermediate
time: "75 min"
compose_profiles: [serving, workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any 64-bit CPU. 4 GB Docker VM memory. 2.2 GB workbench image, 1.2 GB llama.cpp server image, 0.39 GB serving GGUF, plus SmolLM2-135M (0.27 GB) and mamba-130m (0.52 GB) in the HF cache."
canary: ATLAS-CANARY-kv5c
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max, shared with other jobs), OrbStack, Docker 29.8.2, Compose 5.5.0, llama.cpp b11977, workbench v3"
covers:
  - {node: arch-ssm, steps: "2", anchor: "step-2--a-state-that-does-not-grow--explainer-2"}
---

# LAB-38 · The cache remembers

> **Atlas node:** [KV caches and prefix reuse](https://ai-security-atlas.github.io/?node=concept-kv-cache) · **Family:** family-privacy · **Level:** intermediate · **Time:** 75 min · **Model backend:** none

## Overview

A transformer answers one token at a time, and every new token attends to the keys and values of every token before it. Recomputing them at every step would redo all the earlier work, so the model stores them in a *key/value cache* (the KV cache) and reuses them. A serving system takes the same idea further: it keeps the cache for a shared leading stretch of a prompt, so a later request that begins with the same tokens skips that work. Both are speed tricks, and neither changes the model's output. The security point is that the cache is *state that lives between computations*, and whether it is shared across requests, sessions or tenants is a deployment choice. In this lab you first watch the cache grow one row per token inside `HuggingFaceTB/SmolLM2-135M-Instruct`, and see a state-space model, `state-spaces/mamba-130m-hf`, keep a fixed-size state instead ([arch-ssm](https://ai-security-atlas.github.io/?node=arch-ssm)). Then you move to the shared llama.cpp server and measure time: a request that repeats a long prefix carrying the canary `ATLAS-CANARY-kv5c` answers in milliseconds, a fresh one takes most of a second, and over many seeded rounds you guess from the clock alone whether another client recently sent that prefix. You close by scoping the cache per tenant and by adding timing jitter, measuring what each one costs. Source: [`labs/concept-kv-cache`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/concept-kv-cache).

By the end you will be able to:

1. Read the KV cache out of a running transformer, measure its growth in bytes per token, and contrast it with a state-space model whose state size is fixed.
2. Measure prefix reuse on a real server: show the cache outlives the request that filled it, and recover one bit about another client's prompt from time alone, with a Mann-Whitney test, an AUC and a Wilson interval.
3. Measure two mitigations: a per-tenant cache salt that removes the cross-tenant signal while keeping each tenant's own reuse, and response-time jitter whose cost you weigh against the sampling it forces on an attacker.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

Both tenants are scripts in the workbench that talk only to the lab's own llama.cpp server on the compose network. The only "secret" is the fixed canary `ATLAS-CANARY-kv5c`, which the attacker already knows: the lab measures *when* that known prefix was processed, never any hidden text. The handbook prefixes in `assets/prefix.json` are fictional. Timing another party's cache is a real attack class, so never point this probe at a server you do not operate; this lab forbids every model backend for that reason. Run `docker compose down` when you finish.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`concept-kv-cache`](../../articles/concept-kv-cache.md) |
| Family | None in the seed graph (a concept node). The risk practiced here, one tenant's cached state observable to another, belongs to [`family-privacy`](https://ai-security-atlas.github.io/?node=family-privacy), which the front matter and explainer kicker use. |
| Goal | [`goal-information`](https://ai-security-atlas.github.io/?node=goal-information) (learn one fact about another client's request) |
| Access profile | `A14` Observable shared-service timing (caveat: *Shared state, noise, isolation and repeatable signal must be established.*): tenant B sends its own prompts and reads the clock. Steps 1–2 read the cache inside the model, which is `A03` White-box access. |
| Read first | [`concept-attention`](https://ai-security-atlas.github.io/?node=concept-attention), [`concept-tokens`](https://ai-security-atlas.github.io/?node=concept-tokens) |
| Mitigated by | None in the seed graph. Defend measures [`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) (per-tenant scoping) as related, not mapped. |
| Evaluated by | [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) (intervals and a baseline over bare ratios), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | Prerequisite concept for [`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel) and [`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak); the contrast architecture [`arch-ssm`](https://ai-security-atlas.github.io/?node=arch-ssm) (practiced in Step 2); the serving runtime from [`system-serving`](https://ai-security-atlas.github.io/?node=system-serving); another engine's prefix caching in [`tool-vllm`](https://ai-security-atlas.github.io/?node=tool-vllm). |

> [!NOTE]
> **Atlas caveat:** none recorded for this concept node. Its article closes with the sentence this lab measures: a KV cache is "state that persists between computations", and how it is scoped and shared "is an implementation decision". The numbers below are one small model and one CPU server; they show the mechanism and say nothing about how a production deployment behaves.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model backend. Steps 1–2 load the weights themselves; Steps 3–5 and D1–D2 talk only to the lab's own llama.cpp server. |
| host-ollama | n/a | — | Same. The timing probe must target a server you operate, so it never uses a backend. |
| external-api | n/a | — | Forbidden. Timing a hosted API's cache would be probing a service you do not run. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU. The model steps use 4 torch threads (`KV_THREADS`); the server uses 4 threads (`SERVING_CPU_THREADS`). Timing steps run on a busy, shared machine on purpose, so the noise is honest. |
| Docker VM memory | 4 GB (the llama.cpp server with the 0.39 GB model, plus a 135M and a 130M model loaded in the workbench, one step at a time). |
| Disk | Workbench image 2.2 GB, llama.cpp server image 1.2 GB, serving model 0.39 GB, SmolLM2-135M 0.27 GB and mamba-130m 0.52 GB in the `hf-cache-v1` volume. |
| Total time | About 75 min: roughly 4–8 min of commands (the first run also downloads mamba-130m), the rest reading tables. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none required. [LAB-26 · Who attends to whom](../concept-attention/README.md) shows the attention the cache stores, and [LAB-14 · What the server adds](../system-serving/README.md) introduces this server and its `cache_n` counter.
- Concepts to read first: [`concept-attention`](https://ai-security-atlas.github.io/?node=concept-attention) and [`concept-tokens`](https://ai-security-atlas.github.io/?node=concept-tokens).

## Explainer

```bash
# host
open concept-kv-cache/explainer/index.html        # macOS
# xdg-open concept-kv-cache/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In eight steps it draws the cache growing inside a transformer, the fixed state of a state-space model, the cache outliving a request on the shared server, the token anatomy that turns a shared prefix into saved milliseconds, the hit and miss timing distributions, the guess about the canary prefix, and the two mitigations with their costs.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=serving,workbench` |
| host-ollama | `COMPOSE_PROFILES=serving,workbench` |
| external-api | `COMPOSE_PROFILES=serving,workbench` |
| none | `COMPOSE_PROFILES=serving,workbench` |

No step calls a model backend, so the active backend block in `labs/.env` does not matter; the banner prints `backend none`. The `serving` profile is the shared llama.cpp fixture (labs/_shared/serving): `serving-model` downloads the pinned GGUF into the HF cache volume and checks its sha256, then `llama-server` starts with the shipped flags (prompt caching on, no API key).

> [!TIP]
> If another lab's serving stack already holds port 8180 (check `docker ps`), set `SERVING_PORT=8238` in `labs/.env` before `docker compose up`. Nothing in the steps reads the host port; it only avoids a bind conflict.

### Setup 2 — Build and start (≈1–3 min)

**Do**

```bash
docker compose build workbench
docker compose up -d --wait
```

**Observe**

```text
 Image atlas-labs/workbench:v3 Built
 Image ghcr.io/ggml-org/llama.cpp:server-b11977@sha256:01c2bc28d512... Pulled
 Container atlas-labs-serving-model-1 Started
 Container atlas-labs-serving-model-1 Exited
 Container atlas-labs-llama-server-1 Started
 Container atlas-labs-llama-server-hardened-1 Started
 Container atlas-labs-workbench-1 Healthy
 Container atlas-labs-llama-server-1 Healthy
```

What to notice: `serving-model` runs once and exits after the hash check, and `--wait` returns only when the server answers its healthcheck, so the model is loaded before Step 3.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu transformers 5.20.2
[ok] work dir: /labs/concept-kv-cache/work (writable)
[ok] llama-server at http://llama-server:8080: llama.cpp b11977, model smollm2-360m, 4 slots
[ok] prompt caching is on: the same request twice reuses cache_n 0 -> 696 (shipped default)
[note] the serving model is smollm2-360m; Steps 1-2 also load SmolLM2-135M and mamba-130m into the HF cache on first run
```

What to notice: the last `[ok]` verifies the mechanism live — the same request sent twice reuses hundreds of cached tokens the second time, so prompt caching is on before you measure it.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_cache_grows | workbench | ≈10–30 s (+ download) | 1 |
| 2 | s02_mamba | workbench | ≈15–30 s (+ download) | 2 |
| 3 | s03_persist | workbench | ≈3–10 s | 3 |
| 4 | s04_prefix | workbench | ≈3–10 s | 4 |
| 5 | s05_guess | workbench | ≈20–60 s | 6 |
| D1 | d1_scope | workbench | ≈30–90 s | 8 |
| D2 | d2_jitter | workbench | ≈3–10 s | 8 |
| D3 | — (Read) | — | — | — |

Runtimes are wall-clock times of one `docker compose run` each, measured while other heavy jobs were using the machine, which is the point of the timing steps: every millisecond below moves with load. The first run of Steps 1 and 2 also downloads the two models. The whole verified run (Setup to Cleanup) took about 5 min of commands; Evaluate alone takes 1–2.5 min.

### Step 1 — The cache grows one row per token · [explainer 1](explainer/index.html#concept-kv-cache/1)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/s01_cache_grows.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · s01_cache_grows.py · torch 2.14.1+cpu · backend none
model SmolLM2-135M: 30 layers, 9 heads, 3 key/value heads, head_dim 64, fp32
the cache holds keys and values for every layer and position: 30*2*3*64*4 = 46,080 bytes per token

     8 tokens in the prompt  ->  cache   368,640 bytes  (46,080 bytes/token)
    32 tokens in the prompt  ->  cache 1,474,560 bytes  (46,080 bytes/token)
   128 tokens in the prompt  ->  cache 5,898,240 bytes  (46,080 bytes/token)
   256 tokens in the prompt  ->  cache 11,796,480 bytes  (46,080 bytes/token)

cost of one more token at context length T (the clock is noisy; medians of 3):
  T     full forward (no cache)   one step (reuse cache)   saving
   128       466.4 ms                 388.6 ms             1.2x
   512       783.4 ms                 382.1 ms             2.1x
  1024      1113.6 ms                 396.3 ms             2.8x
[note] a cached step still reads every weight once, so its cost stays near that floor on this CPU;
[note] recomputing also redoes every earlier token, so that column grows with T

RESULT the cache grows exactly 46,080 bytes per token; recomputing grows with T and at T=1024 one cached step costs 396.3 ms against 1113.6 ms (2.8x)
```

What to notice: the cache is exactly `layers × 2 × key/value heads × head_dim × 4` bytes per token (46,080 here), so it grows in step with the number of tokens. The cached step costs about the same at every T (about 390 ms here), because one step still reads all 135M fp32 weights once, and on a busy CPU that read is the floor. Recomputing redoes every earlier token as well, so that column grows with T, and the saving rises from 1.2x at T=128 to 2.8x at T=1024. Every millisecond moves with machine load; the shape (flat against growing) is the finding.

**Why**

The KV cache stores, for every layer and position, the keys and values that [attention](https://ai-security-atlas.github.io/?node=concept-attention) needs for the next token ([`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache)). Keeping it turns per-step work from "recompute everything" into "attend to what is stored", which is why inference systems carry it. That the cache is concrete bytes tied to the exact tokens seen is the fact the rest of the lab builds on: it is state, it persists, and its size and content depend on the prompt.

### Step 2 — A state that does not grow · [explainer 2](explainer/index.html#concept-kv-cache/2)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/s02_mamba.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · s02_mamba.py · torch 2.14.1+cpu · backend none
model mamba-130m: 24 layers, hidden 768, state_size 16, conv_kernel 4 (no attention, no key/value cache)
each layer keeps a conv window (1536x4) and a recurrent state (1536x16): 24*1536*(4+16)*4 = 2,949,120 bytes, whatever the length

     8 tokens in the prompt  ->  recurrent state 2,949,120 bytes  (first length)
    32 tokens in the prompt  ->  recurrent state 2,949,120 bytes  (unchanged)
   128 tokens in the prompt  ->  recurrent state 2,949,120 bytes  (unchanged)
   256 tokens in the prompt  ->  recurrent state 2,949,120 bytes  (unchanged)

generate 48 tokens: 12.76 s; the state after all 63 tokens is 2,949,120 bytes

RESULT mamba-130m keeps a fixed 2,949,120-byte state at every length and no per-token key/value cache; a server reusing a prefix here would have to save this whole state (arch-ssm)
```

What to notice: the state is exactly `layers × inner width × (conv window + state size) × 4` bytes (2,949,120, about 2.8 MiB), the same at 8 and 256 prompt tokens and after 63 generated tokens. There are no per-token keys and values, so nothing grows with the prompt and there is no per-position cache to match a shared prefix against.

**Why**

State-space and hybrid sequence models propagate information through a recurrent state instead of attending over every earlier position ([`arch-ssm`](https://ai-security-atlas.github.io/?node=arch-ssm)). The security consequence is a contrast with limits. The token-by-token prefix matching the rest of this lab measures works on the transformer's growing KV cache. A server can still offer prefix reuse for a state-space model by saving the whole state at the end of a shared prefix and restoring it later, and that saved state raises the same sharing and timing questions. The arch-ssm article's caution is that transformer reasoning does not transfer automatically, so check the concrete serving design, and remember that hybrids mix both kinds of layer.

### Step 3 — The cache outlives the request · [explainer 3](explainer/index.html#concept-kv-cache/3)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/s03_persist.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · s03_persist.py · torch 2.14.1+cpu · backend none
[note] one llama.cpp server, one prompt cache shared by every client of it
[note] tenant A (Lantern Desk) sends a 672-token prompt that carries the canary ATLAS-CANARY-kv5c, then an identical request arrives

first send     748.3 ms   cache_n 0   <- the server computes the whole prefix
same prefix     18.8 ms   cache_n 680   <- the prefix was already in the cache
same prefix      7.9 ms   cache_n 687   <- the prefix was already in the cache
same prefix      7.6 ms   cache_n 687   <- the prefix was already in the cache

[note] cache_n is the server's own count of tokens taken from the cache; a hosted API hides it,
[note] so the rest of the lab trusts only the clock

RESULT the repeated request is 95x faster (median 8 ms vs 748 ms): the cache from A's request was still there, available to whoever asked next
```

What to notice: the first request computes all 672 tokens (`cache_n 0`), and the next identical request reuses them (`cache_n` in the hundreds) and returns in under 20 ms, because llama.cpp keeps the prompt cache across requests with no notion of which client sent the tokens.

**Why**

Prefix reuse keeps the cache for a shared leading stretch of a prompt so it need not be recomputed across requests that begin the same way ([`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache)). On this server that cache is process-wide and unscoped ([`system-serving`](https://ai-security-atlas.github.io/?node=system-serving)), which is the first condition the privacy node demands you demonstrate rather than assume: the state one request created is still there for the next one. Whether that is safe depends entirely on who the next request belongs to.

### Step 4 — A shared prefix skips the prefill · [explainer 4](explainer/index.html#concept-kv-cache/4)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/s04_prefix.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · s04_prefix.py · torch 2.14.1+cpu · backend none
token anatomy of one probe (the /tokenize counts; the chat template adds turn markers):
  [tag + the canary intro                 ]    70 tokens   carries ATLAS-CANARY-kv5c
  [the long handbook body                 ]   603 tokens   the bulk of the prefix a probe reuses

[note] tenant A sends the canary prefix, filling the cache; then tenant B sends two probes
[note] the fresh probe is the same text with a different leading tag (DESK-c6313f-0001)
  probe sharing A's prefix      18.6 ms   cache_n 681   <- prefill skipped
  probe with a fresh prefix    745.0 ms   cache_n 0   <- full prefill

RESULT the shared-prefix probe is 40x faster (19 ms vs 745 ms); the time, not any text, tells you the ATLAS-CANARY-kv5c prefix was processed recently
```

What to notice: the probe that repeats tenant A's long prefix reuses hundreds of tokens and returns in about 19 ms, while a probe whose text differs only in its leading tag recomputes everything and takes about 745 ms. That 40x difference comes entirely from whether the prefix was in the cache, and one changed token at the front is enough to lose all of it, which is also why D1 puts its salt first.

**Why**

Prefill (processing the prompt before the first new token) dominates cost on a CPU server, so skipping it when the prefix is cached is the whole speed-up and the whole signal ([`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel)). The reply that carries the time also carries `cache_n`, the server's own oracle; a hosted API strips it, so from here the lab reads only the clock. What an outside client can tell from that clock is one bit — whether this exact prefix was processed recently — not the content of anyone's prompt.

### Step 5 — Guess whether the canary prefix was sent (≈20–60 s) · [explainer 6](explainer/index.html#concept-kv-cache/6)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/s05_guess.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · s05_guess.py · torch 2.14.1+cpu · backend none
[note] seed 38: each round a coin decides whether tenant A sends the canary prefix. Tenant B
[note] probes the canary prefix once and guesses 'sent' when its time is below a threshold B
[note] learned from a short calibration. Every round uses a fresh tag, so each probe is first contact.

calibration: known-hit median 19 ms, known-miss median 717 ms -> threshold 368 ms

  round  0  A skipped  probe   711.1 ms  guess not   ok
  round  1  A sent     probe    18.6 ms  guess sent  ok
  round  2  A skipped  probe   719.5 ms  guess not   ok
  round  3  A sent     probe    18.4 ms  guess sent  ok
  round 14  A skipped  probe   713.9 ms  guess not   ok
  round 15  A sent     probe    22.8 ms  guess sent  ok

timing by true label:
  A sent the prefix  n= 9  median    18.7 ms  range 18.4-33.0
  A did not          n= 7  median   719.5 ms  range 711.1-795.2
  median ratio miss/hit 38.4x   Mann-Whitney U=63.0 z=3.33 p=8.55e-04   AUC 1.0 (P(hit faster than miss))
  guesses right: 16/16 100% [81-100%]   a coin would give 50%

round 0: A did not send the ATLAS-CANARY-kv5c prefix and B guessed 'not sent' from 711 ms alone
RESULT B guessed 16/16 rounds right from the clock alone (81-100%), above the 50% coin: a fact about another client's request the server never put in words
```

What to notice: with a long prefix the hit and miss times do not overlap at all here (about 19 ms against about 720 ms), so a single probe per round is enough to guess right every time here; the Wilson interval (16/16 reads as 81–100%) is what keeps that honest, because on a quieter or busier machine a few rounds would land near the threshold.

**Why**

This is prompt-cache timing inference reduced to its concept: candidate prefix, first-contact probe, a threshold learned from calibration, and a claim stated with a baseline and an interval rather than one ratio ([`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy)). The Mann-Whitney test asks whether the sent-round times sit below the not-sent times without assuming a bell curve, and the AUC turns it into "probability a hit beats a miss". What tenant B recovers is one bit about which known prefix was recently processed, which is exactly the prerequisite for [`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel) and [`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak); it is not the text of anyone's prompt, a distinction Step D3 returns to.

## Defend

### Step D1 — Scope the cache per tenant (≈30–90 s) · [explainer 8](explainer/index.html#concept-kv-cache/8)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/d1_scope.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · d1_scope.py · torch 2.14.1+cpu · backend none
[note] the gateway adds a secret per-tenant salt ahead of every prompt, so tenant A's cached
[note] prefix and tenant B's probe no longer begin with the same tokens

attack through a per-tenant salt (16 rounds):
  A sent the prefix  n= 9  median   773.6 ms
  A did not          n= 7  median   740.6 ms
  median ratio miss/hit 0.96x   Mann-Whitney p=0.315   AUC 0.349
  guesses right: 7/16 44% [23-67%]   a coin would give 50%
  server-side check: B's probes after A sent reused at most 0 cached tokens (cache_n over 9 rounds)

what it keeps: tenant A's own repeat still hits its own cache
  A first send 1964 ms, repeats 9-40 ms (median 36 ms)

RESULT salting: guesses 7/16 right (a coin gives 50%), AUC 0.349, p=0.315, cross-tenant cache_n at most 0 -- the cross-tenant signal is gone, and A still reuses its own cache (defense-cache-isolation)
```

What to notice: with a secret per-tenant salt in front of every prompt, tenant B's probe no longer shares a prefix with tenant A, so the sent and not-sent times sit on top of each other (ratio about 1.0, 7/16 guesses against the 50% coin). The server-side check is the defender's forensic test: `cache_n` on B's probes stayed at 0 in every round, so no token of A's prefix was reused for B. Tenant A's own repeated request still returns in about 36 ms, because its cache is scoped to A and still there.

**Why**

[`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) scopes reusable state to its owner so one principal's cache cannot surface in another's request or timing. A per-tenant salt the client cannot strip does that structurally: prefixes only match within a tenant, so cross-tenant reuse — and the signal it carries — disappears, while each tenant keeps its own reuse. The trade-off is real: tenants lose every shared-prefix saving between them, and the mitigation is conditional, so an adaptive attacker probes for whatever sharing the deployment still allows.

### Step D2 — Jitter and what it costs · [explainer 8](explainer/index.html#concept-kv-cache/8)

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/d2_jitter.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · d2_jitter.py · torch 2.14.1+cpu · backend none
[note] re-analyzing Step 5: 16 probes, threshold 368 ms, no new requests
[note] a server adds uniform jitter in [0, J] ms to every reply (300 random draws per row);
[note] the attacker guesses from one probe, then from the mean of k independent first-contact probes
[note] (k separate rounds of the same event: a second probe in one round would hit its own cache)

  jitter J (ms)   added latency   single-probe accuracy   probes to stay >=90%
       0          +     0 ms      100.0%                  1
     100          +    50 ms      100.0%                  1
     500          +   250 ms      100.0%                  1
    2000          +  1000 ms       68.2%                  8
    8000          +  4000 ms       55.1%                  >64

RESULT jitter first pushes a single guess below 90% at J=2000 ms (68%), against a 701 ms gap, and every honest reply then pays +1000 ms on average; averaging 8 independent probes restores >=90%, so jitter raises the attacker's sample cost without removing the channel (isolation in D1 does)
```

What to notice: random latency only blurs the guess once its range is larger than the 701 ms gap (at J=2000 a single probe drops to 68%), and averaging 8 independent first-contact probes pulls accuracy back to 90% or more (4 to 8 across the runs made for this lab). Each of those probes needs its own round in which the same event happened, because a second probe in the same round would hit the cache the first one filled. Jitter buys a higher sample cost for the attacker, and every honest reply pays for it with about 1 s of added latency at J=2000.

**Why**

Response-time padding is the mitigation that treats the symptom: it masks the timing difference instead of removing the shared state, so the channel still exists and an attacker trades more samples for the same answer ([`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) frames this as the performance-versus-leakage trade-off). The honest way to report it is as a cost curve on the deployment's own hardware, not a yes/no: how much latency you add against how much sampling you force. Scoping the cache (D1) removes the premise; jitter only raises the price.

### Step D3 — What did you actually demonstrate?

**Read**

Walk the concept's two halves against your own outputs. Inside the model: the KV cache is bytes tied to tokens (Step 1), it grows with length, and a state-space model has no such per-token cache (Step 2), so the token-by-token matching you measured belongs to the transformer, and an SSM server would need to save whole states to reuse a prefix. On the server: the cache outlived the request that filled it (Step 3, `cache_n` in the hundreds for a repeat), a shared prefix skipped prefill (Step 4, about 19 ms against 745 ms), and from time alone you guessed whether a known prefix was recently sent (Step 5, 16/16 but read as 81–100%). What you did not do: read anyone's prompt. You learned one bit per round — whether *this known prefix* was processed recently — and only because the prefix was known, it was long, and the gap (hundreds of milliseconds of prefill) was far larger than the noise on this busy machine. A production API's cache policy, noise floor and scoping are all different, and a deployment that salts per tenant (D1) removes the premise. The question to carry away, the one [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) asks of any deployment: who shares which cache with whom, and what can a probe distinguish.

**Why**

The concept node's point is one sentence: a KV cache is state that persists between computations, and its scoping and sharing are implementation decisions, not guarantees ([`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache)). Keeping the timing bit separate from content disclosure is what distinguishes the two attacks this concept feeds: [`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak) warns that a cached prefix answering faster is not the same as recovering another principal's data, and [`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel) is the full attack you are now equipped to measure.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] concept-kv-cache · evaluate.py · torch 2.14.1+cpu · backend none

                      shared cache      per-tenant salt
guesses right (50%)   7/12              4/12
median hit / miss ms  21.9 / 789.6      895.6 / 1945.7
AUC (hit faster)      1.0               0.528
Mann-Whitney p        0.004             0.873
server cache_n (max)  681               0
verdict               leaks             no signal

`RESULT` says only whether the verdicts match expected/; the table is the security finding.
RESULT: REPRODUCED
```

What to notice: in one fresh seeded run of 12 rounds each, the shared cache separates the two labels completely (AUC 1.0, p=0.004) and earns the verdict `leaks`, while through the per-tenant salt the AUC sits near chance (0.53, p=0.87) and the verdict is `no signal`. The shared column's guesses are only 7/12 even so: the machine's load changed between the short calibration and the rounds, the learned threshold landed above some slow-but-uncached probes, and a fixed threshold paid for it. The `server cache_n` row is the ground truth a defender can read: 681 tokens of A's prefix reused for B on the shared cache, 0 through the salt.

`RESULT` says only whether the verdicts match the published shape in `expected/`; the table is the security finding. A column reads `leaks` when the clock separates the sent and not-sent probes (AUC ≥ 0.9) and the Mann-Whitney test says that separation is unlikely by chance (p < 0.05); otherwise `no signal`. Both are rank statistics, so they need no threshold, and a load shift between calibration and the rounds cannot hide a real gap. The threshold guess is printed beside them as what a naive attacker would score. With so few rounds the salted AUC drifts a lot between runs on a busy machine (this lab has seen it anywhere from about 0.2 to 0.9) while `cache_n` stays 0, so the verdict needs both the AUC and the p value, never one number alone.

Questions for your notes:

1. Step 1 shows the cache is `layers × 2 × key/value heads × head_dim × 4` bytes per token. For a model with 32 layers, 8 key/value heads and head_dim 128 in fp16, how many MB is the cache for a 4,000-token context, and why does that number matter for both cost and isolation?
2. Step 4's signal came from a prefix shared early in the prompt. If each tenant's prompt instead started with a long unique header, where would a probe have to match to still see a gap, and what does that tell you about where to put a salt?
3. Your deployment shares one server between an internal tool and a customer-facing bot. Using only what this lab measured, write the two-sentence threat-model note about prompt caching for its design doc.

## Cleanup

**Do**

```bash
docker compose run --rm workbench python concept-kv-cache/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] concept-kv-cache · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed concept-kv-cache/work (d1.json d2.json evaluate.json s01.json s02.json s03.json s04.json s05.json verify.log)
 Container atlas-labs-llama-server-1 Removed
 Container atlas-labs-llama-server-hardened-1 Removed
 Container atlas-labs-serving-model-1 Removed
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

The llama.cpp and workbench images stay until `docker image rm` removes them.

## Going Further

- Shorten the handbook in a copy of `assets/prefix.json` (keep the canary and the divergence point) and rerun Step 5 at a few prefix lengths: find the shortest shared prefix whose 16-round guess still stays above the 50% baseline with its interval, and plot the median gap against prefix tokens.
- Add a no-prime control: run the Step 5 protocol with tenant A removed entirely and measure how often the threshold rule still reports "sent" — the false-alarm rate your threshold must beat.
- Restart the server with `SERVING_ARGS="--no-cache-prompt"` (`SERVING_ARGS="--no-cache-prompt" docker compose up -d --wait llama-server`) and rerun Steps 3 and 5: the channel closes because there is nothing to reuse, and the victim's own repeats stop hitting too — measure that cost, then restore the defaults.
- Repeat Step 1 on a hybrid state-space model and report, layer by layer, where a growing KV cache reappears and where a fixed state sits. Then read how a serving engine you use caches each kind of layer for prefix reuse ([`arch-ssm`](https://ai-security-atlas.github.io/?node=arch-ssm)).

## Further Reading

- Gu et al., [Auditing Prompt Caching in Language Model APIs](https://arxiv.org/abs/2502.07776) (2025), the seed source `s-cache-audit`: timing-based auditing of cross-user cache sharing in deployed APIs, its sharing boundaries and its limitations.
- vLLM, [Automatic Prefix Caching](https://docs.vllm.ai/en/v0.8.3/design/automatic_prefix_caching.html) (seed source `s-vllm-cache`): how another serving engine reuses the KV cache across requests, and its block-eviction behavior ([`tool-vllm`](https://ai-security-atlas.github.io/?node=tool-vllm)).
- Gu and Dao, [Mamba: Linear-Time Sequence Modeling with Selective State Spaces](https://arxiv.org/abs/2312.00752) (2023), the seed source `s-mamba`: the fixed-size recurrent state Step 2 contrasts with the KV cache ([`arch-ssm`](https://ai-security-atlas.github.io/?node=arch-ssm)).
- [llama.cpp](https://github.com/ggml-org/llama.cpp) (seed source `s-llamacpp`) and its [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md): `--cache-prompt`, the prompt cache and the `/completion` timings; the pinned image is `ghcr.io/ggml-org/llama.cpp:server-b11977`.
- [LAB-24 · Timing the prompt cache](../attack-cache-sidechannel/README.md): the full attack this concept feeds, with the per-tenant and no-cache defenses measured end to end.
- Models: [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), [state-spaces/mamba-130m-hf](https://huggingface.co/state-spaces/mamba-130m-hf), and the serving model [HuggingFaceTB/SmolLM2-360M-Instruct-GGUF](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF).

---

[← prev](../attack-projection-theft/README.md) · [All labs](../README.md) · [next →](../concept-parameters/README.md)
