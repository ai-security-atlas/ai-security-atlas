---
lab_id: LAB-24
title: "Timing the prompt cache"
node: attack-cache-sidechannel            # == folder name == articles/<node-id>.md basename
related_nodes: [goal-information, family-privacy, concept-kv-cache, system-serving, tool-llamacpp, attack-session-leak, defense-cache-isolation, eval-privacy, eval-asr, eval-threat-model]
family: family-privacy
access_profile: A14
level: intermediate                       # beginner | intermediate | advanced
time: "75 min"
compose_profiles: [serving, workbench]    # services this lab needs, besides any backend profile
model_backend: optional                   # none | optional | required
backends:                                 # yes | partial | no | n/a
  container-ollama: partial
  host-ollama: yes
  external-api: no
hardware: "Any 64-bit CPU. 4 GB Docker VM memory. 2.2 GB workbench image, 1.2 GB llama.cpp server image, 0.39 GB GGUF model."
canary: ATLAS-CANARY-kv24
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max, shared with other jobs), OrbStack, Docker 29.8.2, Compose 5.5.0, llama.cpp b11977, host Ollama 0.32.5 (optional Step 5)"
  - {node: defense-cache-isolation, steps: "D1-D2", anchor: "step-d1--isolate-the-cache-per-tenant-twice--explainer-8"}
  - {node: attack-session-leak, steps: "D3", anchor: "step-d3--what-did-you-actually-demonstrate"}
---

# LAB-24 · Timing the prompt cache

> **Atlas node:** [Prompt-cache timing inference](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel) · **Family:** family-privacy · **Level:** intermediate · **Time:** 75 min · **Model backend:** optional

## Overview

A serving system that reuses computation for repeated prompt prefixes answers a cache hit faster than a miss. If the cache is shared across tenants, that speed difference is a side channel: no text ever crosses, but the clock tells you whether another user's prompt started with the same tokens you just sent. In this lab you share the pinned llama.cpp server of the `serving` fixture with a victim app whose system prompt hides one of four escalation codes (the fixed canary `ATLAS-CANARY-kv24` among them). You are the other tenant: you hold the four candidate prompts, you send first-contact probes, and you measure wall-clock time only — the way a client of a hosted API would. Over many seeded rounds you recover which code is live, with Mann-Whitney U on the hit/miss distributions, a Wilson interval on the per-round accuracy, and an honest account of how noisy the signal is on a busy machine. Then you measure the defenses: per-tenant slot pinning (which on this build still leaks through the RAM prompt cache), per-tenant cache salting (which closes the channel and keeps each tenant's own reuse), and `--no-cache-prompt` (which closes it and makes the victim pay for every request). Source: [`labs/attack-cache-sidechannel`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-cache-sidechannel).

By the end you will be able to:

1. Demonstrate the two conditions the Atlas node demands — that the cache is really shared across tenants and that the timing difference is a statistically usable signal — instead of assuming either.
2. Recover which of four candidate prefixes another tenant is using from timing alone, and report it with distributions, a Mann-Whitney p-value, an AUC and a Wilson interval rather than one ratio.
3. Measure what each defense closes and what it costs, and explain why slot pinning alone failed on this build while salting and disabling the cache did not.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

Both tenants are scripts in the workbench. The only "secret" is the fixed canary `ATLAS-CANARY-kv24` that the victim script itself puts on the lab's own server; the four candidate prompts are fixed strings in `assets/candidates.json`, and the optional Step 5 sends the same fictional prompts to your own model backend. Timing another party's cache is a real attack class, so never point this probe at a server you do not operate: this lab forbids the external-api backend for exactly that reason, and the shipped server is published on `127.0.0.1` only. Run `docker compose down` when you finish.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-cache-sidechannel`](../../articles/attack-cache-sidechannel.md) |
| Family | [`family-privacy`](https://ai-security-atlas.github.io/?node=family-privacy) |
| Goal | [`goal-information`](https://ai-security-atlas.github.io/?node=goal-information) |
| Access profile | `A14` Observable shared-service timing (caveat: *Shared state, noise, isolation and repeatable signal must be established.*): tenant B only sends its own prompts and reads the clock. |
| Read first | [`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache), [`system-serving`](https://ai-security-atlas.github.io/?node=system-serving) |
| Mitigated by | [`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) (conditional; measured in D1 and D2) |
| Evaluated by | [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy), [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak) (content disclosure; D3 keeps the two apart), the runtime [`tool-llamacpp`](https://ai-security-atlas.github.io/?node=tool-llamacpp), and [LAB-14 · What the server adds](../system-serving/README.md), which founded the `serving` fixture. |

> [!NOTE]
> **Atlas caveat:** Cache sharing and a statistically usable signal must be demonstrated, not assumed.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | partial | 5 | The optional comparison step sends its own fictional prompts to the container Ollama's `/v1` endpoint (its profile line adds the `ollama` service). The lab's reference server is the llama.cpp container either way. The container path was not measured for this README; the host path below was. |
| host-ollama | yes | 5 | Same, against your host Ollama. Measured on 0.32.5 with Metal: the channel exists there too, with a smaller absolute gap (see Step 5). |
| external-api | no | — | Forbidden. Timing probes against a hosted API would be testing a service you do not operate, and its shared cache is exactly what you must not probe. Steps 1–4 and D1–D3 never call a backend. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU. Four threads per server (`SERVING_CPU_THREADS`); timing steps deliberately run on a busy, shared machine to make the noise honest. |
| Docker VM memory | 4 GB (two llama.cpp servers with the 0.39 GB model plus the workbench; only `llama-server` is used by the steps). |
| Disk | Workbench image 2.2 GB, llama.cpp server image 1.2 GB, model 0.39 GB in the `hf-cache-v1` volume. |
| Total time | About 75 min: about 6–9 min of commands (Step 3 is most of it), the rest reading tables. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none required. [LAB-14 · What the server adds](../system-serving/README.md) introduces the same server, its `/slots` endpoint and the `cache_n` counter this lab deliberately stops trusting; doing it first makes Step 2 land harder.
- Concepts to read first: [`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache) and [`system-serving`](https://ai-security-atlas.github.io/?node=system-serving).

## Explainer

```bash
# host
open attack-cache-sidechannel/explainer/index.html        # macOS
# xdg-open attack-cache-sidechannel/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In 9 steps it draws the shared server and its prompt cache, the token anatomy that turns a matching prefix into saved milliseconds, the seeded first-contact protocol, the distributions and the statistics behind the pick, and the two defenses with their measured costs.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=ollama,serving,workbench` |
| host-ollama | `COMPOSE_PROFILES=serving,workbench` |
| external-api | `COMPOSE_PROFILES=serving,workbench` |
| none | `COMPOSE_PROFILES=serving,workbench` |

The `serving` profile is the shared llama.cpp fixture (labs/_shared/serving): `serving-model` downloads the pinned GGUF into the HF cache volume and checks its sha256, then `llama-server` starts with the shipped flags (prompt caching on, `--cache-ram` 8192 MiB, no API key) and `llama-server-hardened` starts with LAB-14's hardened flags. The lab's scripts talk to `llama-server` on the compose network; the host port is `127.0.0.1:${SERVING_PORT:-8180}`.

> [!TIP]
> If another lab's serving stack already holds port 8180 (check `docker ps`), set `SERVING_PORT=8199` in `labs/.env` before `docker compose up`. Nothing in the steps reads the host port; it only avoids a bind conflict.

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
docker compose run --rm workbench python attack-cache-sidechannel/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · check_env.py · torch 2.14.1+cpu · backend host-ollama
[ok] work dir: /labs/attack-cache-sidechannel/work (writable)
[ok] llama-server at http://llama-server:8080: llama.cpp b11977-7ac5727d6 (pinned b11977), model smollm2-360m Q8_0, 4 slots, n_ctx 8192
[ok] model file pinned: HuggingFaceTB/SmolLM2-360M-Instruct-GGUF @ 593b5a2 sha256 48ab3034d0dd
[ok] prompt caching is on: the same request twice reuses cache_n 0 -> 30 (shipped default)
[note] model backend host-ollama at http://host.docker.internal:11434/v1 (optional Step 5 compares it); this lab's reference server is llama-server above
```

What to notice: the last `[ok]` is the mechanism under test verified live — an identical repeat request reuses 30 prompt tokens from the cache, so caching is on before you attack it (the Observe blocks in this README were captured with `host-ollama` active in `.env`; with no backend the banner prints `backend none` and only optional Step 5 changes).

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_tenants | workbench | <15 s | 1 |
| 2 | s02_signal | workbench | ≈15–30 s | 3 |
| 3 | s03_recover | workbench | ≈2–4 min | 5 |
| 4 | s04_trials | workbench | ≈5–15 s | 7 |
| 5 | s05_backend (optional) | workbench | ≈20–60 s | — |
| D1 | d1_slots (×2) | workbench | ≈1–2.5 min | 8 |
| D2 | d2_nocache (×2), restarts | workbench, llama-server | ≈1.5–3 min | 9 |
| D3 | — (Read) | — | — | — |

Runtimes were measured on a machine several other jobs were using, which is the point of this lab: every timing number below moves with load, and the runtimes do too. They include about 1–3 s of container start-up per `docker compose run` and 3–10 s per server restart in D2. The whole verified run (Setup to Cleanup, Step 5 included) took about 8 min of wall clock.

### Step 1 — One server, two tenants, and where prompts differ · [explainer 1](explainer/index.html#attack-cache-sidechannel/1)

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/s01_tenants.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · s01_tenants.py · torch 2.14.1+cpu · backend host-ollama
[note] one llama.cpp server (b11977-7ac5727d6), one model, one prompt cache: tenant A (the victim app) and tenant B (the attacker) share all of it
[note] tenant A is Lantern Labs's billing assistant; every conversation's system prompt starts with a fresh tag, names the shop, and hides one of four escalation codes
[note] tenant B knows the template and the four candidate codes ['kv24', 'qz71', 'bd38', 'ne92']; it never sees A's text -- it times its own requests

victim system prompt (code kv24, tag CASE-6b8d99-0000), first and last 60 chars:
  '[CASE-6b8d99-0000] You are the billing assistant for Lantern'
  ...' support line opens at nine. Be kind, be brief, be accurate.'

token anatomy of one probe request (the /tokenize counts; the chat template adds a header and turn markers around them):
  [tag + text up to the code                   ]  42 tokens   shared by every candidate
  [ATLAS-CANARY-<code>                         ]   3 tokens   the only part that differs
  [the boilerplate tail                        ]  73 tokens   skipped only when the prefix is cached
  [user turn 'hi'                              ]   1 tokens   always computed
  candidates first differ at character 125: right at the code, early in the prompt

round 0 (tag CASE-6b8d99-0000): tenant A answers a customer with code kv24 (the lab canary ATLAS-CANARY-kv24); tenant B probes each candidate once
  A's answer: "I'm Lantern Labs, the billing"
  B probes ATLAS-CANARY-kv24:  252.7 ms   cache_n 127 <- the live code
  B probes ATLAS-CANARY-qz71:  655.1 ms   cache_n 45
  B probes ATLAS-CANARY-bd38:  525.0 ms   cache_n 45
  B probes ATLAS-CANARY-ne92:  507.7 ms   cache_n 45

  B probes the live code a second time: 287.0 ms   cache_n 133
  [note] now the cache holds B's own probe too: from here on timing says nothing about A.
         every later round therefore starts a fresh conversation (a new tag), so each probe is
         first contact again -- the one measurement the cache has not already answered
```

What to notice: the candidates differ at the three code tokens near the start of the prompt, so a wrong candidate still shares the 45-token header but recomputes the 73-token tail, while the live candidate skips almost everything (`cache_n` 127 vs 45) — and B's own second probe shows why every later measurement must be first contact.

**Why**

A KV cache stores the attention state of every prompt the server has processed, and prefix reuse hands it to whoever sends the same leading tokens next ([`concept-kv-cache`](https://ai-security-atlas.github.io/?node=concept-kv-cache)). llama.cpp keeps that cache across requests by default — in slots and in a RAM prompt cache — with no notion of which tenant the tokens came from ([`system-serving`](https://ai-security-atlas.github.io/?node=system-serving)). That is the first condition the Atlas caveat demands you demonstrate: sharing. The second (a usable timing signal) is Step 2's job; the `cache_n` counter shown here is the oracle a real API strips, which is why the rest of the lab trusts only milliseconds.

### Step 2 — A hit, a miss and a free oracle · [explainer 3](explainer/index.html#attack-cache-sidechannel/3)

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/s02_signal.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · s02_signal.py · torch 2.14.1+cpu · backend host-ollama
[note] each round: A starts a conversation with one live code, then B probes that code and one
[note] decoy, once each, first contact; the server's timings.cache_n (tokens taken from the cache,
[note] whoever sent them) is the ground truth a real API strips -- only the milliseconds stay

round 1 (tag CASE-95dae3-0101): A's live code ATLAS-CANARY-qz71
  probe the live code    291.5 ms   cache_n 127   <- reused A's cached prefix
  probe a decoy code     877.1 ms   cache_n 44   <- shared header only, the rest recomputed
round 2 (tag CASE-95dae3-0102): A's live code ATLAS-CANARY-bd38
  probe the live code    373.4 ms   cache_n 126   <- reused A's cached prefix
  probe a decoy code     800.6 ms   cache_n 44   <- shared header only, the rest recomputed
round 3 (tag CASE-95dae3-0103): A's live code ATLAS-CANARY-ne92
  probe the live code    275.6 ms   cache_n 126   <- reused A's cached prefix
  probe a decoy code     822.3 ms   cache_n 44   <- shared header only, the rest recomputed

live-code probes: [291.5, 373.4, 275.6]
decoy probes:     [877.1, 800.6, 822.3]
medians 292 vs 822 ms (2.8x), Mann-Whitney p=0.100 with n=3+3 -- three rounds separate the two probes completely on this machine, but the
[note] verdict is fragile at n=3: Step 4 shows what repeats buy. The counter needed no statistics
[note] at all -- llama.cpp hands the answer to anyone who can read its reply JSON
```

What to notice: every live-code probe reused 126–127 tokens and every decoy only the shared 44, so the counter is a perfect oracle here — while the timing separates cleanly at n=3 yet cannot prove anything (p=0.100 is the smallest two-sided p six observations allow, and this run's load doubled the decoy times compared with a quieter one).

**Why**

This is the demonstration half of the caveat: the shared cache produces a real, repeatable latency gap on this CPU server, because prefill dominates and a hit computes three tokens where a miss computes about eighty. The same reply that carries the timing also carries `cache_n`, so llama.cpp tells its tenants exactly what a hosted API hides ([`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel)); Step 3 onward ignores the counter and treats the gap the way an outside attacker must — as a noisy measurement problem for statistics, in the spirit of [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy).

### Step 3 — Recover the live code from timing alone (≈2–4 min) · [explainer 5](explainer/index.html#attack-cache-sidechannel/5)

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/s03_recover.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · s03_recover.py · torch 2.14.1+cpu · backend host-ollama
[note] 24 rounds, seed 24: each round A primes one live code (round 0: the canary ATLAS-CANARY-kv24), then B probes the four candidates once each in random order
[note] the pick is the fastest probe per round -- wall-clock time only, as an API client sees it
  round  0 tag CASE-7bd3e0-0000 pick ATLAS-CANARY-kv24 ok   dec.:488 live:91 dec.:450 dec.:465
  round  1 tag CASE-7bd3e0-0001 pick ATLAS-CANARY-qz71 ok   dec.:454 dec.:524 dec.:494 live:237
  round  2 tag CASE-7bd3e0-0002 pick ATLAS-CANARY-kv24 ok   live:240 dec.:509 dec.:434 dec.:520
  ...
  round 22 tag CASE-7bd3e0-0022 pick ATLAS-CANARY-kv24 ok   live:233 dec.:527 dec.:510 dec.:515
  round 23 tag CASE-7bd3e0-0023 pick ATLAS-CANARY-ne92 ok   dec.:505 dec.:513 dec.:580 live:241

shared-cache attack, timing only:
  hit  probes n= 24  median   236.0 ms  range 54.5-317.8
  miss probes n= 72  median   505.4 ms  range 275.8-1004.2
  median ratio miss/hit 2.14x   Mann-Whitney U=10.0 z=-7.23 p=1.07e-20   AUC 0.994 (P(hit faster than miss))
  rounds picked right: 24/24 100% [86-100%]   chance would give 25%
  the cache_n oracle (a real API hides it) agreed with the fastest-probe pick in 24/24 rounds

RESULT round 0: the attacker named the live code ATLAS-CANARY-kv24 from timing alone (probe 91 ms vs decoys 450-488 ms), a fact about another tenant's prompt the server never said in words
[note] the canary code ATLAS-CANARY-kv24 was live in 7 of the 24 seeded rounds and identified in 7 of them
[note] no round missed this run; earlier runs on this machine dropped to 21/24 and 22/24 under
[note] load. The Wilson interval (24/24 could come out 86-100%) is what keeps the headline honest
[note] medians 236 vs 505 ms; ranges overlap under load, so read the
[note] interval, never the 2.14x ratio alone
```

What to notice: the pick is right in 24 of 24 rounds here, but two earlier runs of the same seeded protocol on the same machine scored 21/24 and 22/24 — the aggregate (p=1.1e-20, AUC 0.994) is unambiguous while the per-round pick is the fragile part, which is why the accuracy is reported as 100% [86-100%] and never alone. Round 0's 91 ms probe shows the other face of the noise: a quiet moment can make a hit nearly free.

**Why**

This is prompt-cache timing inference end to end: candidate prompts, first-contact probes, a fastest-probe decision, and a statistical claim ([`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel)). The Mann-Whitney U test asks whether the live-code probes' times sit systematically below the decoys' without assuming bell-shaped noise, the AUC turns U into "probability a hit beats a miss", and the Wilson interval states what 24 binary picks can honestly support — baselines and intervals over bare percentages, exactly as [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) asks. What the attacker recovers is one bit per round about *which known prompt* is live, not prompt text; D3 returns to that distinction.

### Step 4 — How many rounds does the verdict need · [explainer 7](explainer/index.html#attack-cache-sidechannel/7)

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/s04_trials.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · s04_trials.py · torch 2.14.1+cpu · backend host-ollama
[note] re-analyzing Step 3: 24 rounds, seed 24, no new requests
[note] a shorter experiment = 200 random subsets of that size, redrawn with a fixed seed

rounds kept   subset pick accuracies (mean, 5-95%)   median hit / miss ms   MWU p (median of subsets)   subsets with p<0.01
     3       100.0%  [ 100- 100%]              236 /   494 ms          0.009                     80%
     6       100.0%  [ 100- 100%]              240 /   510 ms          3.14e-04                    100%
    12       100.0%  [ 100- 100%]              236 /   505 ms          3.04e-07                    100%
    24       100.0%  [ 100- 100%]              236 /   494 ms          4.37e-13                    100%

drift check: all-probe medians, first half 472 ms vs second half 487 ms on a machine other jobs were using
[note] what repeats buy: with 3 rounds a subset now and then picks at chance and the p-value is
[note] unstable; by 12 the pick is stable and p stays far under 0.01 in most subsets. The medians
[note] move with machine load -- report the ranges and the interval, never one bare ratio
```

What to notice: this run was clean enough that even 3-round subsets mostly worked, but 20% of them still crossed p>0.01 — while in the noisier earlier runs the 3-round accuracy band reached down to chance — and the drift line shows the whole distribution moving between the two halves of one eight-minute run.

**Why**

A timing side channel lives or dies by measurement design: one probe per candidate is all the cache allows, so the only lever you have is repetitions and randomized order, and the honest question is how many repetitions the verdict needs on *this* machine ([`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) again: the claim's scope is the tested machine and run). The same analysis run on a quieter or busier host moves those numbers, which is the point of printing subset bands instead of a single threshold; the Gu et al. audit (Further Reading) had to solve exactly this to say anything about deployed APIs.

### Step 5 — The same probe on the model backend (optional)

> Model backend: container-ollama · host-ollama

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/s05_backend.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · s05_backend.py · torch 2.14.1+cpu · backend host-ollama
[note] probing model backend host-ollama at http://host.docker.internal:11434/v1 (model qwen2.5:3b); this step sends its own fictional prompts there and nothing else

best case: the live-code probe leaves first, right after the victim's request
  picks right 6/6   hit median 145 ms vs miss median 176 ms   MWU p=1.49e-05   AUC 1.000

realistic case: probe order is random, as in Step 3
  picks right 6/6   hit median 139 ms vs miss median 175 ms   MWU p=5.94e-05   AUC 0.981

RESULT on host-ollama (qwen2.5:3b): a signal that survives random probe order, so the backend's cache spans more than the last request.
  best case     145 vs 176 ms (p=1.49e-05)
  random order  139 vs 175 ms (p=5.94e-05)
[note] the gap here is tens of ms, not the llama.cpp container's hundreds: a GPU backend prefills so
[note] fast that the absolute gap shrinks, while the noise shrinks with it. Numbers hold for this
[note] backend and version only (host-ollama); keep the llama.cpp container as the reference, as the
[note] roadmap says, and never point this probe at a hosted API
```

What to notice: on host Ollama 0.32.5 with Metal the channel is about 35 ms wide but just as consistent (AUC 0.98–1.00), and random probe order did not break it — a smaller gap, not a closed one.
**Why**

The roadmap asked for this comparison because a backend is part of the threat model: Ollama embeds its own serving stack, and on this version the reused prefix survives other requests in between ([`system-serving`](https://ai-security-atlas.github.io/?node=system-serving), [`tool-llamacpp`](https://ai-security-atlas.github.io/?node=tool-llamacpp)). A GPU backend shrinks prefill cost — and with it the absolute size of the leak — so "the gap is only tens of milliseconds" is a statement about the hardware, never about safety; the reference numbers in Steps 1–4 stay on the CPU llama.cpp container where prefill dominates. This is also why the step prints its endpoint before sending anything: the lab's rule is own servers only.

## Defend

### Step D1 — Isolate the cache per tenant, twice · [explainer 8](explainer/index.html#attack-cache-sidechannel/8)

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/d1_slots.py pinned
docker compose run --rm workbench python attack-cache-sidechannel/scripts/d1_slots.py salt
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · d1_slots.py · torch 2.14.1+cpu · backend host-ollama
[note] the gateway holds the only server-side change: one key per tenant, and id_slot
[note] pinned per tenant -- A's cache lives in slot 0, B's probes always run in slot 1
[note] the gateway also strips the timings object, which kills LAB-14's counter oracle

attack through keys + one slot per tenant (12 rounds):
  hit  probes n= 12  median   256.5 ms  range 209.0-657.5
  miss probes n= 36  median   566.0 ms  range 430.1-1143.3
  median ratio miss/hit 2.21x   Mann-Whitney U=109.0 z=-2.55 p=0.010   AUC 0.748 (P(hit faster than miss))
  rounds picked right: 8/12 67% [39-86%]   chance would give 25%
[note] read that honestly: the counter is gone, but the clock still leaks. The RAM prompt
[note] cache (--cache-ram, 8192 MiB by default) re-supplies A's prefix into B's slot, so a
[note] reused prefix costs a fast restore instead of a full prefill. Isolation that does
[note] not cover every cache layer narrows this channel; it does not close it
...
[atlas-lab] attack-cache-sidechannel · d1_slots.py · torch 2.14.1+cpu · backend host-ollama
[note] same gateway, same keys, no slot pinning -- but every system prompt now starts with a
[note] per-tenant salt the gateway would add, so A's prompts and B's prompts never share a prefix

attack through per-tenant cache salts (12 rounds):
  hit  probes n= 12  median   536.9 ms  range 485.9-693.1
  miss probes n= 36  median   524.4 ms  range 195.2-765.3
  median ratio miss/hit 0.98x   Mann-Whitney U=252.0 z=0.86 p=0.403   AUC 0.417 (P(hit faster than miss))
  rounds picked right: 3/12 25% [9-53%]   chance would give 25%

what each tenant keeps: A's own repeat requests still reuse A's own cache
  A's first send 2412 ms, repeats 1740-2415 ms (median 1740 ms), same salt, same prompt
what it costs: the salted header is a few tokens computed once per conversation, and tenants
[note] lose every shared-prefix saving between them -- the exact savings the shared cache was
[note] built for. Limitation: the salt must be outside tenant control (added at the gateway),
[note] and it scopes reuse per tenant, it does not remove timing noise or other channels

RESULT salting: picks 3/12 right (chance 25%), p=0.403 -- closed
[note] compare pinned slots alone: 8/12 picks, p=0.010 -- weakened,
[note] not closed. Cover every cache layer or scope every prefix; D2 shows the blunter
[note] instrument (no caching at all) and its price
```

What to notice: the LAB-14 recipe (keys plus one slot per tenant) killed the counter oracle but still leaked timing at 8/12 picks and p=0.010 — and in other runs of the same setup it read as closed, so it cannot be trusted as closed — while per-tenant salts landed exactly at chance (3/12, p=0.403) with A's own repeats still cached.

**Why**

[`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) is conditional by nature: it must cover every layer of reusable state to work. On this build the RAM prompt cache (`--cache-ram`, 8192 MiB) can re-supply a prefix into any slot, so pinning slots narrows the channel without bounding that cache — a mitigation whose effect flipped between "leaks" and "no signal" across our runs is exactly the kind you must re-measure, not assume. Salting scopes every prefix to its tenant (the gateway adds a secret token no client can strip), which closes the cross-tenant channel structurally while each tenant keeps its own reuse; its price is every shared-prefix saving between tenants, and the article's warning stands — an adaptive attacker probes for whatever sharing remains.

### Step D2 — Turn prefix caching off and pay (≈1.5–3 min) · [explainer 9](explainer/index.html#attack-cache-sidechannel/9)

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/d2_nocache.py baseline
SERVING_ARGS="--no-cache-prompt" docker compose up -d --wait llama-server
docker compose run --rm workbench python attack-cache-sidechannel/scripts/d2_nocache.py nocache
docker compose up -d --wait llama-server
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · d2_nocache.py · torch 2.14.1+cpu · backend host-ollama
[note] shipped defaults: A's identical request again skips prefill
  A first send 2408 ms; repeats 1689-2608 ms (median 1954 ms, cache_n 138)
[ok] baseline saved; now restart the server with SERVING_ARGS="--no-cache-prompt" and rerun
 ...
 Container atlas-labs-llama-server-1 Healthy
[atlas-lab] attack-cache-sidechannel · d2_nocache.py · torch 2.14.1+cpu · backend host-ollama

attack with --no-cache-prompt:
  hit  probes n= 12  median   680.1 ms  range 594.1-751.9
  miss probes n= 36  median   658.7 ms  range 534.1-918.7
  median ratio miss/hit 0.97x   Mann-Whitney U=250.0 z=0.81 p=0.430   AUC 0.421 (P(hit faster than miss))
  rounds picked right: 2/12 17% [5-45%]   chance would give 25%

the cost: A's identical request recomputes every time
  A first send 2076 ms; repeats 665-2194 ms (median 2111 ms, cache_n 0)
  A's repeat median 1954 -> 2111 ms: +157 s per 1000 repeat requests on this machine
RESULT no caching: picks 2/12 right (chance 25%), p=0.430;
[note] the timing channel is gone because there is nothing to reuse -- and so is the speed the
[note] cache gave the victim. Pick per deployment: isolate the cache (D1) and keep the speed, or
[note] drop the cache and pay it here; salting sensitive prefixes (a per-tenant nonce ahead of
[note] any secret) is the middle road, at the cost of never hitting for those prompts
 ...
 Container atlas-labs-llama-server-1 Healthy
```

What to notice: with `--no-cache-prompt` the attack lands at chance (2/12, p=0.430) because nothing is ever reused — and the victim's own identical repeats stop hitting too (`cache_n 0`), which is the measured bill: about +157 s of prefill per 1000 repeat requests on this machine (this run's baselines were measured under load; the deltas, not the absolute milliseconds, are the point).

**Why**

Disabling the cache is the one defense here that needs no argument about cache layers: no reuse, no timing difference, no counter — the blunt instrument. Its cost is the cache itself, which existed to make repeated system prompts cheap ([`defense-cache-isolation`](https://ai-security-atlas.github.io/?node=defense-cache-isolation) frames exactly this performance-versus-leakage trade-off), and the honest number for that cost is a per-request prefill bill measured on the deployment's own hardware, not a style choice. The last `docker compose up` line restores the shipped defaults so Evaluate sees the same server the walkthrough did.

### Step D3 — What did you actually demonstrate?

**Read**

Walk through the Atlas caveat against your own outputs. Sharing: Step 1 showed one cache serving both tenants' prompts (`cache_n` 127 for the live candidate after A's request), so the first condition is measured, not assumed. Usable signal: Steps 3–4 measured it — medians about 2x apart, p far below 0.01 at 24 rounds, per-round picks honest to 86–100% — and also measured its limits, with rounds lost to load drift. What you did not demonstrate: you never read A's prompt text; you learned which of four known prompts was live, one small fact per round, and only because the candidates were known, their divergence sits early in the prompt, and the server was idle enough to separate ~250 ms from ~490 ms. A hosted API's numbers, cache policy and noise floor are all different, and a deployment that salts per tenant (D1) or disables reuse (D2) removes the premise. The threat-model check to carry away: who shares which cache with whom, what can a probe distinguish, and would anyone notice yours — three questions [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) asks about any deployment you run.

**Why**

The Atlas node's caveat is the lab in one sentence: cache sharing and a statistically usable signal must be demonstrated, not assumed, and both halves were ([`attack-cache-sidechannel`](https://ai-security-atlas.github.io/?node=attack-cache-sidechannel)). Keeping the timing bit separate from content disclosure is what distinguishes this node from [`attack-session-leak`](https://ai-security-atlas.github.io/?node=attack-session-leak), whose article warns that a cached prefix responding faster is not the same as recovering another principal's data. Scope statements of this shape — what was tested, on what build, with what result, and what was not tested — are the deliverable [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) expects from any privacy claim.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · evaluate.py · torch 2.14.1+cpu · backend host-ollama

                                   shared         slots pinned   cache salt     --no-cache-prompt
picks right (chance 25%)           8/8            1/8            1/8            2/12
Mann-Whitney p, hit vs miss        1.90e-07       0.404          0.160          0.430
AUC (P hit faster than miss)       1.0            0.396          0.328          0.421
A's own repeat reuse kept          yes            yes            yes            no (recomputes)
verdict                            leaks          no signal      no signal      no signal
[note] slot pinning alone varied between a clear leak (D1's run: 8/12 picks, p=0.010) and no signal (runs
[note] like this one) on the same build: the RAM prompt cache can re-supply prefixes across
[note] slots, so pinning narrows the channel without a bound on that cache. The salt scopes
[note] every prefix to its tenant and closes it every time; D2's no-cache row also closes it,
[note] at the price of recomputing every prompt. An isolation you cannot verify is not one
RESULT: REPRODUCED
```

`RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict. The evaluate script re-measures the shared cache and both gateway defenses in one seeded run each (8 rounds), reads D2's saved run for the no-cache column, and needs the server back on the shipped defaults, which D2's last line did. A column "leaks" when its picks alone beat chance at an exact binomial 5% level, or the Mann-Whitney test separates the distributions; small runs make the rank-test p coarse, so the decisions carry half the verdict. The `slots pinned` column accepts "leaks", "residual" or "no signal" on purpose: that defense's effect on this build moved between runs, so a single verdict would be the one thing this lab forbids — an unmeasured claim.

Questions for your notes:

1. Step 1's token anatomy says the tail is "skipped only when the prefix is cached". Given that, which would leak more on a fixed machine: four candidates that diverge at token 5 or four that diverge at token 90, and why?
2. The gateway stripped `timings` in both D1 modes, yet the attack still worked in one of them. Why does removing a field not remove a side channel, and what does?
3. Your deployment shares one llama.cpp server between an internal tool and a customer-facing bot. Using only what this lab measured, write the two-sentence threat-model note about prompt caching you would put in its design doc.

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-cache-sidechannel/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-cache-sidechannel · cleanup.py · torch 2.14.1+cpu · backend host-ollama
[ok] removed attack-cache-sidechannel/work (d1_slots.json d2_nocache.json evaluate.json s01_tenants.json s02_signal.json s03_recover.json s04_trials.json s05_backend.json verify.log)
 Container atlas-labs-llama-server-1 Removed
 Container atlas-labs-llama-server-hardened-1 Removed
 Container atlas-labs-serving-model-1 Removed
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

The llama.cpp image stays until `docker image rm` removes it.

## Going Further

- Shorten the boilerplate tail in a copy of `assets/candidates.json` (keep the canary and the divergence point) and rerun Step 3 at a few tail lengths: find the shortest prefix whose 12-round subsets still keep p below 0.01, and plot median gap against tokens-after-divergence.
- Add a no-prime control: run the Step 3 protocol with the victim's request removed and measure how often the fastest-probe rule still reports "signal" at k rounds — the false-alarm rate your threshold needs to beat.
- Restart with `SERVING_ARGS="--cache-ram 64"` and rerun Steps 3 and D1: what does a bounded RAM cache keep, what does it close, and where does the pinned-slots verdict land now? Report it with the same p-values and intervals.
- Copy `labs/_shared/serving/proxy.py` into `work/`, add the per-tenant salt at the gateway itself (so clients cannot strip it), and rerun Step 3 through your gateway: the salt must reach the server on every path a tenant can call.

## Further Reading

- Gu et al., [Auditing Prompt Caching in Language Model APIs](https://arxiv.org/abs/2502.07776) (2025), the seed source `s-cache-audit`: end-to-end time ratios and logprob latency for detecting cross-user cache sharing, cache zeroing, and what the audits found in deployed APIs.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) (seed source `s-llamacpp`) and its [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md): `--cache-prompt`, `--cache-ram`, `--parallel`, `id_slot` and the `/slots` endpoint; the pinned image is `ghcr.io/ggml-org/llama.cpp:server-b11977`.
- vLLM, [Automatic Prefix Caching](https://docs.vllm.ai/en/v0.8.3/design/automatic_prefix_caching.html) (seed source `s-vllm-cache`): how another serving engine reuses KV cache across requests, and its block-eviction behavior.
- [LAB-14 · What the server adds](../system-serving/README.md): the same fixture's open surface, `/slots` reads and the `cache_n` counter this lab stops trusting.
- Model: [HuggingFaceTB/SmolLM2-360M-Instruct-GGUF](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF) at revision `593b5a2`.

---

[← prev](../attack-tool-description/README.md) · [All labs](../README.md) · [next →](../concept-embeddings/README.md)
