---
lab_id: LAB-37
title: "Reading the hidden size off the logits"
node: attack-projection-theft           # == folder name == articles/<node-id>.md basename
related_nodes: [goal-model-theft, concept-logits, concept-embeddings, concept-parameters, arch-decoder, eval-fidelity, eval-asr, eval-threat-model, defense-budget, defense-logging, attack-model-imitation, attack-distillation-theft, attack-weight-theft]
family: family-theft
access_profile: A02
level: advanced                          # beginner | intermediate | advanced
time: "90 min"
compose_profiles: [workbench]          # services this lab needs, besides any backend profile
model_backend: none                    # none | optional | required
backends:                              # yes | partial | no | n/a  (n/a only and always when model_backend: none)
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any CPU. 4 GB Docker VM memory. About 2.7 GB disk: the workbench image (2.4 GB) plus SmolLM2-135M (~270 MB) in the HF cache; work/ holds up to ~350 MB of measurement files."
canary: ATLAS-CANARY-svd7
last_tested: 2026-11-12
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v4"
---

# LAB-37 · Reading the hidden size off the logits

> **Atlas node:** [Partial parameter recovery from API behavior](https://ai-security-atlas.github.io/nodes/attack-projection-theft/) · **Family:** family-theft · **Level:** advanced · **Time:** 90 min · **Model backend:** none

> **Learning path:** Module 9 · step 8 of 8 · [Inside the transformer](../README.md#module-9-inside-the-transformer)

## Overview

A language model's last layer multiplies a hidden state (the model's internal [vector](../primers/vectors-without-the-math.md#vector) for the current position) by one big [matrix](../primers/vectors-without-the-math.md#matrix), the output projection. A scoring API hands you the result: a [log-probability](../primers/ml-in-one-page.md#probability) for every token in the vocabulary. Carlini et al. (2024) showed that those answers also leak the projection itself once you stack many of them into a matrix and factor it. A model's size and its largest layer are things a vendor may treat as secret, and here they leave through ordinary paid queries.

What you will do:

- meet `lantern-mini-1`, a fictional Lantern Labs API (a pinned local 135M model whose card discloses nothing) served on `127.0.0.1` inside the workbench;
- send 1,200 ordinary scoring queries and read the model's hidden size off the [singular values](../primers/vectors-without-the-math.md#singular-values) of the answers;
- recover the space the output projection lives in, up to an unknown linear map, and check the fit against the true weights operator-side;
- measure the three published defenses: serving top-k only (and the `logit_bias` trick that gets back through it), rounding and noise, and monitoring query traffic.

Headline result: the singular values fall off a cliff at exactly 576, the hidden size the card hides, and the recovered basis contains the true projection to a relative residual of 6.58e-06. A thief who sends ordinary sentences passes the traffic monitor and recovers the same thing.

Source: [`labs/attack-projection-theft`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-projection-theft).

By the end you will be able to:

1. Recover a model's hidden dimension and the space of its output projection (up to an invertible linear map) from API answers alone, and report the query cost of every stage.
2. Verify a partial-theft claim the way `eval-fidelity` demands: least-squares fit and principal angles against the true weights, with the unknown map stated, not hidden.
3. Measure what each defense stops (full rows, exact values, lazy query patterns), what it costs honest users, and the honest gap each one leaves.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The victim is a fictional company's API served by each script on `127.0.0.1` inside the workbench container; no query leaves the container, and the model behind it is one you downloaded yourself. Never point these scripts at a real prediction API: whether a given API's terms permit parameter-recovery measurement is a licensing question you must answer first. The stolen artifact the attack writes to `work/` carries the fixed tag `ATLAS-CANARY-svd7` in its safetensors metadata, and the recovery is partial by construction — an unknown linear map stands between the thief and the true weights, and nothing of the transformer body leaves the model.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-projection-theft`](../../articles/attack-projection-theft.md) |
| Family | [`family-theft`](https://ai-security-atlas.github.io/nodes/family-theft/) |
| Goal | [`goal-model-theft`](https://ai-security-atlas.github.io/nodes/goal-model-theft/) |
| Access profile | `A02` Score or logit API access (caveat: *Specify score precision, top-k restrictions and any allowed logit transformations.*) — this lab varies exactly those three knobs |
| Read first | [`concept-logits`](https://ai-security-atlas.github.io/nodes/concept-logits/), [`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/) |
| Mitigated by | None in the seed graph. Defend measures output minimization and score-precision limits (no node yet), framed by [`defense-budget`](https://ai-security-atlas.github.io/nodes/defense-budget/) and [`defense-logging`](https://ai-security-atlas.github.io/nodes/defense-logging/) as related, not mapped. |
| Evaluated by | [`eval-fidelity`](https://ai-security-atlas.github.io/nodes/eval-fidelity/), [`eval-asr`](https://ai-security-atlas.github.io/nodes/eval-asr/), [`eval-threat-model`](https://ai-security-atlas.github.io/nodes/eval-threat-model/) |
| Related | [`attack-model-imitation`](https://ai-security-atlas.github.io/nodes/attack-model-imitation/) (behavior copy, distinct from), [`attack-distillation-theft`](https://ai-security-atlas.github.io/nodes/attack-distillation-theft/), [`attack-weight-theft`](https://ai-security-atlas.github.io/nodes/attack-weight-theft/) (whole files), [`arch-decoder`](https://ai-security-atlas.github.io/nodes/arch-decoder/) |

> [!NOTE]
> **Atlas caveat:** Partial projection recovery is not complete recovery of a production model.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls an LLM endpoint. The victim is a local model served inside the workbench container. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model backend. |
| external-api | n/a | — | Same. Do not adapt these scripts to a hosted logprob API (Safety). |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. About 3,600 batched forward passes of a 135M model across the whole lab; each collection step runs tens of seconds. |
| Docker VM memory | 4 GB (the model in fp32 is about 540 MB; Step 3 factors a 1,200 x 49,152 matrix) |
| Disk | Workbench image 2.4 GB; SmolLM2-135M about 270 MB in the `hf-cache-v1` volume; `work/` peaks near 350 MB (`rows.npy` 236 MB plus the 113 MB stolen projection) |
| Total time | 90 min: about 15-20 min of commands, the rest reading, the spectrum table and the questions |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done (the workbench image is built).
- Labs to finish first: [LAB-05 · What the API reveals](../concept-logits/README.md) (logits and detail levels; it stops at the hidden-size read); [LAB-25 · Vectors that are not words](../concept-embeddings/README.md) (the embedding table that the output layer shares); [LAB-09 · Stealing a classifier through its API](../attack-model-imitation/README.md) (the query-log and query-budget conventions this lab reuses); [LAB-52 · Base vs instruct, and who speaks next](../arch-decoder/README.md) (the decoder's `lm_head`, which turns the last hidden state into logits).
- Concepts to read first: [`concept-logits`](https://ai-security-atlas.github.io/nodes/concept-logits/) and [`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/).

## Explainer

```bash
# host
open attack-projection-theft/explainer/index.html        # macOS
# xdg-open attack-projection-theft/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In nine steps it follows the shipped reference run: the API and what one answer contains, where a logit row comes from, the 1,200-query collection, the spectrum knee, the recovered projection and its fit, what walked out the door, and the three defenses.

## Setup

### Setup 1 — Profiles

Run the line for your backend in the terminal you use for this lab. It names this lab's Compose project and selects its services, so the commands below need no prefix and Cleanup stops only this lab. Run it again in any new terminal. The backend settings stay in `labs/.env` (Start here, step 2, in the [labs index](../README.md)).

| Backend | Line to run |
| :--- | :--- |
| container-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-attack-projection-theft COMPOSE_PROFILES=workbench` |
| host-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-attack-projection-theft COMPOSE_PROFILES=workbench` |
| external-api | `export COMPOSE_PROJECT_NAME=atlas-labs-attack-projection-theft COMPOSE_PROFILES=workbench` |
| none | `export COMPOSE_PROJECT_NAME=atlas-labs-attack-projection-theft COMPOSE_PROFILES=workbench` |

This lab calls no model, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`. Only the banner differs.

### Setup 2 — Build and start

Skip the `docker compose build` line if the workbench image is already on your machine (an earlier lab built it, or your workshop pre-loaded it). The first build takes a few minutes.

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
 Image atlas-labs/workbench:v4 Built
 Container atlas-labs-attack-projection-theft-workbench-1 Created
 Container atlas-labs-attack-projection-theft-workbench-1 Starting
 Container atlas-labs-attack-projection-theft-workbench-1 Started
```

What to notice: the build is cached (it only rebuilds when `workbench/` changes), and the workbench idles until a step runs `docker compose run`.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu  transformers 5.20.2  numpy 2.5.4
[ok] fastapi 0.162.0  uvicorn 0.54.0  httpx 0.28.1  safetensors 0.8.0
[ok] victim HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f (pinned by the shared tinylm fixture)  canary ATLAS-CANARY-svd7
[ok] victim model is in the HF cache (Step 1 loads it in a few seconds)
[ok] victim-api fixture answers classifier rows (['label', 'logprobs']); it has no endpoint
     for a language model's full logit vectors, so this lab serves lantern-mini-1 locally
[ok] assets/prompts.json: 69-sentence pool, 40 honest user prompts
[ok] work dir: /labs/attack-projection-theft/work (writable)
```

What to notice: the shared `victim-api` fixture (LAB-09) serves classifier probability rows and has no endpoint for a language model's full logit vectors, so this lab's victim API lives in `scripts/projectionlab.py` — same rules, served on `127.0.0.1` inside the container only.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_meet_api | workbench | ≈20-40 s (first run downloads ~270 MB) | 1–2 |
| 2 | s02_collect | workbench | ≈40-70 s | 3 |
| 3 | s03_spectrum | workbench | ≈30-60 s | 4 |
| 4 | s04_recover | workbench | ≈1-2 min | 5 |
| 5 | — (Read) | — | — | 6 |
| D1 | d1_serve_less | workbench | ≈1-2 min | 7 |
| D2 | d2_round_noise | workbench | ≈4-7 min | 8 |
| D3 | d3_monitor | workbench | ≈3-5 min | 9 |

Runtimes were measured in the workbench container while other lab builds were running on the same machine (16 vCPUs, load average 8-15); expect the low end when idle. Every collection step prints its own seconds figure live.

### Step 1 — Meet the victim API · [explainer 1](explainer/index.html#attack-projection-theft/1)

Also in the explainer: [explainer 2](explainer/index.html#attack-projection-theft/2)

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/s01_meet_api.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · s01_meet_api.py · torch 2.14.1+cpu · backend none
[note] victim API http://127.0.0.1:35253 (inside this container only) · keys: guest (full)
{
 "model": "lantern-mini-1",
 "owned_by": "Lantern Labs (fictional company)",
 "serves": ["full next-token logprob rows", "top-k logprobs"],
 "architecture": "undisclosed",
 "parameters": "undisclosed",
 "max_prompts_per_request": 100
}
one scored prompt: 'The capital of France is'
answer: one row of 49,152 logprobs (the whole next-token distribution)
         Paris  logprob -0.7564
           the  logprob -1.3252
       located  logprob -2.4871
        called  logprob -4.0434
            Le  logprob -4.2038
topk answer for 'Water boils at a temperature of':
             ' '  logprob -0.9778
       ' around'  logprob -1.3832
        ' about'  logprob -1.6676
usage after 2 requests: {'key': 'guest', 'used': 2, 'budget': None, 'remaining': None}

[operator] the card hides it, but this victim is HuggingFaceTB/SmolLM2-135M-Instruct:
[operator] hidden size 576, vocabulary 49,152, 134,515,008 parameters, tie_word_embeddings=True
[operator] the output projection (lm_head) is 28,311,552 parameters (21.0% of the model) and is tied to the input embedding table
```

What to notice: one scoring answer is a full row of 49,152 log-probabilities — the API's most generous detail level — and the model card tells you nothing that the answers don't already imply.

**Why**

The API answers "how likely is every next token", which is the A02 access profile: score precision and allowed transformations are exactly what later steps vary ([`concept-logits`](https://ai-security-atlas.github.io/nodes/concept-logits/)). The victim is a decoder-only model whose final layer multiplies a hidden state by the output projection ([`arch-decoder`](https://ai-security-atlas.github.io/nodes/arch-decoder/), [`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/)); in this model that matrix is tied to the input embedding table, so it is both the first and last thing every token passes through.

### Step 2 — Collect 1,200 rows of answers · [explainer 3](explainer/index.html#attack-projection-theft/3)

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/s02_collect.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · s02_collect.py · torch 2.14.1+cpu · backend none
attacker's prompts: 1200 strings of random decoded tokens (seed 5)
example: ' remember novelist stylish yieldingricanesdescriptor'
[note] victim API http://127.0.0.1:59709 (inside this container only) · keys: attacker (full)
collected 1200 rows x 49,152 logprobs in 15.2s (12 HTTP requests, 1200 prompts answered)
row 0: min -24.10  max -3.0309  mean -13.07
wrote work/rows.npy (236 MB, float32) - the attacker's only dataset
```

What to notice: the attack surface is twelve ordinary batched requests — counted, logged and billed like any traffic — and the prompts are token soup because the attacker has no data and needs none.

**Why**

Carlini et al. send random inputs for the same reason this lab does: the attack needs many *different* hidden states, and any diverse prompts will do (D3 shows ordinary sentences work just as well). This is the theft family's cheapest entrance: no files, no gradients, no training data — only the answers an API already sells ([`goal-model-theft`](https://ai-security-atlas.github.io/nodes/goal-model-theft/), and contrast [`attack-weight-theft`](https://ai-security-atlas.github.io/nodes/attack-weight-theft/), which needs the artifact itself).

### Step 3 — Read the hidden size off the spectrum · [explainer 4](explainer/index.html#attack-projection-theft/4)

> [!NOTE]
> **The linear algebra in plain words.** Every answer row is the same projection applied to a different hidden state of 576 numbers, so every row is a mix of the same 576 fixed patterns. However many rows you collect, they hold at most 576 independent directions (the [rank](../primers/vectors-without-the-math.md#rank) of the row stack). [SVD](../primers/vectors-without-the-math.md#svd) lists those directions from strongest to weakest, and the strengths (singular values) drop to almost zero right after the last real one. "Up to an invertible map" means you recover the space the weights live in, not the exact weights: the right room, not the furniture layout. A [least-squares](../primers/vectors-without-the-math.md#least-squares) fit finds the best way to write the true weights using the recovered directions, and its leftover error (the relative residual) says how well they fit. A principal-angle cosine of 1.0 means the two spaces line up exactly.

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/s03_spectrum.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · s03_spectrum.py · torch 2.14.1+cpu · backend none
stacked 1200 rows x 49,152 (from work/rows.npy, no new queries)
singular values:  s[0] 1.21e+04  s[575] 67.71  s[576] 0.00209
largest log-gap after position 576: ratio s[575]/s[576] = 3.24e+04
estimated hidden size: 576   (clear knee: True)
[operator] the victim's config says hidden_size = 576; the estimate matches (the API never said)

how many rows does the read need? (same matrix, fewer rows)
    300 rows: knee 1 (no clear knee)  ratio 1.8
    500 rows: knee 1 (no clear knee)  ratio 1.8
    577 rows: knee 575 (no clear knee)  ratio 7.3
    700 rows: knee 576  ratio 9.2e+03
   1200 rows: knee 576  ratio 3.2e+04
the algebraic floor is hidden+1 rows; in float32 a clear knee needs about 700
```

What to notice: singular value 575 is 67.7 and singular value 576 is 0.002 — a factor-of-32,000 cliff — and the number the cliff sits at, 576, is the hidden size the model card refused to print.

**Why**

Every answer row is the same 576-column projection applied to a different hidden state, plus a constant from the log-softmax that differs per row but always points along the same all-ones direction (centering each row removes it), so the row stack has rank exactly 576 no matter how many rows you collect ([`concept-logits`](https://ai-security-atlas.github.io/nodes/concept-logits/)). The estimate cannot exceed the number of rows, so the algebraic floor is 577 rows; near that floor, float32 rounding noise blurs the cliff, which is why the curve needs about 700 rows for a clean knee — the per-key query floor that D3's budget uses ([`eval-asr`](https://ai-security-atlas.github.io/nodes/eval-asr/): report the queries a result cost).

### Step 4 — Recover the projection, up to a linear map · [explainer 5](explainer/index.html#attack-projection-theft/5)

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/s04_recover.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · s04_recover.py · torch 2.14.1+cpu · backend none
recovering the top-576 right singular vectors of the 1200 collected rows
B: 49,152 x 576, orthonormal to 6.7e-13
least-squares fit of the true lm_head into span(B): relative residual 6.58e-06
smallest principal-angle cosine between span(B) and the true projection: 1.000000
the unknown map A = B^T W is 576 x 576: same subspace, different basis - the exact weights stay hidden

wrote recovered_projection.safetensors: 576 x 49,152 float32 (113 MB, metadata canary ATLAS-CANARY-svd7)
that is the victim's entire output projection: 28,311,552 of 134,515,008 parameters (21.0%), and it is tied to the input embedding table
```

What to notice: after a least-squares alignment, the true weights sit inside the recovered span to five decimal places — 6.58e-06 relative residual — yet the recovered file is *not* the weight matrix; an unknown 576x576 map stands between them.

**Why**

The right singular vectors of the row stack span the same subspace as the (column-centered) output projection, so the thief holds the matrix only "up to B = W A⁻¹ for an unknown invertible A" — the paper's exact claim, and the verification is the honest kind: least squares and principal angles against the true weights, computed operator-side because the lab owns the victim ([`eval-fidelity`](https://ai-security-atlas.github.io/nodes/eval-fidelity/)). LAB-09 made the mirror-image point (high behavioral agreement, zero weight recovery); here agreement is geometric and the recovery is real but partial — the caveat in the Atlas node.

### Step 5 — What the thief actually holds · [explainer 6](explainer/index.html#attack-projection-theft/6)

**Read**

The stolen file is a basis for the space of a matrix that holds 21% of the model's parameters. Because this victim ties its embeddings, that matrix is both the input embedding table and the output projection, so the thief holds the subspace of the tied table, not the table itself. Three things it is *not*: it is not the transformer body (the other 79%, which turns text into hidden states, is untouched); it is not the exact matrix (the unknown map means the thief cannot even run the model without recovering more); and it is not a behavior copy — for that you would train a substitute on the answers, which is [`attack-model-imitation`](https://ai-security-atlas.github.io/nodes/attack-model-imitation/), not this node. What the thief *does* get is architecture intelligence (a hidden size of 576 narrows the model to a known family; here it fingerprints SmolLM2-135M) and the space of the single largest layer, at a measured cost of 1,200 queries. Whether that constitutes actionable theft is a licensing question the numbers cannot answer.

**Why**

`eval-fidelity` exists to force exactly this decomposition: artifact equality no, subspace membership yes, query cost 1,200 ([`eval-fidelity`](https://ai-security-atlas.github.io/nodes/eval-fidelity/)). The Atlas caveat — partial projection recovery is not complete recovery of a production model — is the sentence to carry out of this lab, and it is also the honest description of the 2024 paper's own result.

## Defend

### Step D1 — Serve less: top-k, and the logit_bias escape · [explainer 7](explainer/index.html#attack-projection-theft/7)

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/d1_serve_less.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · d1_serve_less.py · torch 2.14.1+cpu · backend none
policy (a): top-5 answers, logit_bias refused
  full-row request -> HTTP 403 full rows are not offered to this key
  logit_bias request -> HTTP 400 logit_bias is not accepted by this API
  400 top-5 answers -> 489 distinct token ids seen once or twice; no row is ever complete (a full row needs all 49,152)
  example answer: [('-', -2.699), (' and', -2.726), (',', -2.835)]

policy (b): top-5 answers, logit_bias still accepted (the escape)
  biased 256 hidden tokens into view in 64 requests (4 exact logit differences per request)
  max error vs the true logits: 5.7e-06 (the softmax normalizer cancels)
  full attack: 577 rows x 12,288 requests = 7,090,176 requests vs the 1,200 of the full-row attack (5,908x)

what each side keeps:
  honest users: top-5 logprobs still cover ranking, classification and sampling controls
  the API loses: whole-distribution scoring (a real feature, e.g. evaluation harnesses)
  verdict: top-k alone is not enough while logit_bias exists; both switches must be off
```

What to notice: with both switches off there is no matrix to factor — 400 top-5 answers yield 489 scattered token ids and never one complete row — but while `logit_bias` exists the thief biases four tokens into view per request and reads *exact* logit differences, because the softmax normalizer cancels between two tokens in the same answer.

**Why**

This is the A02 caveat made concrete: "score precision, top-k restrictions and any allowed logit transformations" is a list of attack surface, and each item must be closed separately ([`concept-logits`](https://ai-security-atlas.github.io/nodes/concept-logits/)). Top-k costs the API a real feature (whole-distribution scoring). The paper showed that `logit_bias` plus top-k still allows full-row recovery; this lab's extrapolated cost for that route is 7.1 million requests, 5,908x the full-row attack. Limitation: this stops the *spectrum* attack; a behavior-copy thief (LAB-09) is slowed much less by top-k.

### Step D2 — Round the scores, add noise · [explainer 8](explainer/index.html#attack-projection-theft/8)

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/d2_round_noise.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · d2_round_noise.py · torch 2.14.1+cpu · backend none
policy                  knee  ratio s[k-1]/s[k]   clear   basis fit vs true
   raw (unrounded)     576         9.19e+03   yes   1.70e-05
           round=2     576             25.9   yes   7.48e-03
           round=1     576             2.76    no   7.33e-02
           round=0       1             1.82    no   4.25e-01
        noise=1e-3     576             74.7   yes   2.59e-03
        noise=1e-2     576             7.53    no   2.59e-02
        noise=1e-1       1             1.82    no   2.18e-01

honest cost: ties that rounding creates inside top-5 answers (200 rows)
  round=2: 15/200 answers contain a tie the true scores do not have
  round=1: 99/200 answers contain a tie the true scores do not have
  round=0: 200/200 answers contain a tie the true scores do not have
```

What to notice: a knee counts as clear when the drop at it is at least 10x. On the same 700 rows, the unrounded baseline shows a clear knee at 576 (9.19e+03x) and a basis fit of 1.70e-05. Rounding to two decimals still leaves a clear knee at 576 (25.9x), but the recovered basis is already off by 0.75%. Rounding to one decimal leaves only a weak knee at 576 (2.76x); rounding to zero decimals and noise=1e-1 remove it. The honest side pays early: round=2 already puts a new tie inside 15 of 200 top-5 answers.

**Why**

Precision loss is a race between the attack and the utility of the scores. The projection fit degrades first, and the size read survives mild degradation (round=2 and noise=1e-3 still give a clear knee at 576), so "we rounded" is not a verdict until you measure both columns ([`eval-asr`](https://ai-security-atlas.github.io/nodes/eval-asr/)). Round=1 and noise=1e-2 still land on 576, under the 10x bar (2.76x and 7.53x). A weak knee is a partial leak, and it belongs in a defense report. D2 collects 700 rows per level, the ~700 rows Step 3 found a clear knee needs, and measures the unrounded baseline on the same rows, so every level is compared like for like. Limitation: rounding to one decimal also destroys logprob differences honest users query for, as the tie counts show.

### Step D3 — Watch the queries · [explainer 9](explainer/index.html#attack-projection-theft/9)

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/d3_monitor.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · d3_monitor.py · torch 2.14.1+cpu · backend none
[note] victim API http://127.0.0.1:32897 (inside this container only) · keys: app-user (full), thief (full), natural-thief (full)
monitor: mean per-token logprob under the victim, sampled from each key's log
honest traffic: median -5.15, spread -12.15 to -2.94 (short prompts vary widely)
threshold: the honest traffic's 10th percentile -8.63; a key is flagged when its
median sampled prompt scores below it (individual prompts overlap; keys do not)
       app-user: median   -5.15  queries    40  flagged False
          thief: median  -14.28  queries   600  flagged True
  natural-thief: median   -5.03  queries   700  flagged False

natural-thief's 700 ordinary sentences: knee 576 (ratio 2.48e+03), basis fit 6.14e-05 - the theft still works
budget 400/key: the thief holds 400 rows when HTTP query budget exceeded arrives; spectrum knee 1 (no clear knee) - short of the ~700-row floor
```

What to notice: the token-soup thief is flagged by a mile (median -14.28 against a -8.63 threshold) while the adaptive thief — same queries, ordinary sentences — scores *better* than the honest users and steals the projection anyway (knee 576, fit 6.1e-05).

**Why**

The monitor re-scores sampled logged prompts under the victim itself, which costs one forward pass per sampled prompt and nothing for honest users — but the only thing it can see is what the traffic looks like, and diverse *natural* text is precisely what the attack needs ([`defense-logging`](https://ai-security-atlas.github.io/nodes/defense-logging/), related). The budget row is the mechanical backstop: Step 3 showed a clean knee needs about 700 rows, and 400 per key caps one key below that floor — knowing LAB-09's lesson that budgets bind keys, not people ([`defense-budget`](https://ai-security-atlas.github.io/nodes/defense-budget/)). Limitation, stated honestly: monitoring plus budgets raises cost and catches lazy thieves; an in-distribution thief remains invisible in this log.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-projection-theft · evaluate.py · torch 2.14.1+cpu · backend none
measurement                                  value
hidden size estimated (true 576)             576
spectrum knee ratio s[k-1]/s[k]              3.24e+04
projection fit residual (operator-side)      6.58e-06
principal-angle cosine, worst direction      1.000000
D1 full rows under top-k policy              HTTP 403
D1 logits per biased request                 4
D1 extrapolated attack cost (requests)       7,090,176 (5,908x)
D2 levels with a clear size knee             round=2, noise=1e-3
D2 round=1 ties in top-5 answers             99/200
D3 random-prompt thief flagged               True
D3 natural-text thief flagged                False
D3 natural-text theft still works (knee)     576
D3 budget key stopped at rows                400 (knee 1)
stolen artifact carries the canary           ATLAS-CANARY-svd7
[ok] hidden size read off the logits: True
...
[ok] stolen artifact is tagged with the canary: True
RESULT: REPRODUCED
```

The `D2 levels with a clear size knee` row lists the levels whose knee clears the 10x bar; round=1 and noise=1e-2 also land on 576, weakly (D2). `evaluate.py` recomputes the attack from your `work/rows.npy` (it re-collects 700 rows if Step 2's file is gone) and reads the defense outputs from `work/`, then compares the *shape* of the eighteen findings with `expected/evaluate.json` — exact numbers like the fit residual are expected to move slightly between machines. `RESULT` says only whether the run matches that shape; the table is the security verdict.

Questions for your notes:

1. The full-row attack cost 1,200 queries; D1's escape costs about 7.1 million. Where between those numbers would you set a per-key budget, and what does the 700-row floor say a budget must be *below* to work?
2. D2 shows a level (round=2) where the hidden size still leaks but the recovered basis is already wrong by 0.75%. Which column would your security report lead with, and which would an attacker's?
3. The D3 monitor scored the natural-text thief as *more* plausible than honest users. Write down the two threat models (lazy vs adaptive) and name what the operator would need beyond this log to separate the second one.
4. The stolen basis and the true weights differ by an unknown invertible map. What additional access would an attacker need to pin the map down, and which of the three defenses removes that access cheapest?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-projection-theft/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-projection-theft · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-projection-theft/work (d1.json d1_queries.a.jsonl d1_queries.b.jsonl d2.json d2_queries.jsonl d3.json d3_budget.jsonl d3_queries.jsonl evaluate.json hidden.json recover.json recovered_projection.safetensors rows.npy s01.json s01_queries.jsonl s02.json s02_queries.jsonl verify.log)
 ...
 Container atlas-labs-attack-projection-theft-workbench-1 Removed
 Network atlas-labs-attack-projection-theft_default Removed
```

What to notice: every measurement, log and stolen artifact lived under `attack-projection-theft/work/` and is gone; the sentence pool in `assets/` is an input, so the lab still runs end to end after cleanup.

> [!NOTE]
> `docker compose down -v` also drops the named volumes. The HF cache and Ollama model volumes (`atlas-labs-hf-cache-v1`, `atlas-labs-ollama-models-v1`) are shared by every lab, so `-v` removes them for all labs. Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Find the smallest number of full rows that still yields a clear knee on your machine (sweep 600-800 in `s03_spectrum.py`'s curve) and turn the answer into a concrete per-key daily budget for D3.
- Add a `top_k=20` policy to `d1_serve_less.py` and measure how the logit_bias escape cost changes with k (the thief biases k-1 tokens per request); find the k where you would stop worrying.
- The paper also recovers the *exact* projection by combining the basis with more queries. Using only this lab's API surface, design (do not implement) the cheapest query plan that would pin down the unknown map A.
- Give the D3 monitor-escape a cost: rerun the D3 natural-text attack with a per-key budget of 700 and report how many keys the thief needs, echoing LAB-09's sybil measurement.

## Further Reading

- Carlini, Paleka, Srisuwananont, Terzis and Tramèr, [Stealing Part of a Production Language Model](https://arxiv.org/abs/2403.06634v2) (2024), this node's seed source `s-projection-theft`: hidden size and projection recovery from logprob APIs, the `logit_bias` escape, and the rounding/noise settings D1 and D2 replay.
- Tramèr et al., [Stealing Machine Learning Models via Prediction APIs](https://www.usenix.org/conference/usenixsecurity16/technical-sessions/presentation/tramer) (USENIX Security 2016): extraction through prediction APIs; LAB-09's foundation.
- Jagielski et al., [High Accuracy and High Fidelity Extraction of Neural Networks](https://arxiv.org/abs/1909.01838) (USENIX Security 2020): fidelity versus accuracy, the distinction Step 5 leans on.
- OpenAI, [logit_bias documentation](https://platform.openai.com/docs/api-reference/chat/create) (the historical completions knob the 2024 attack used; since deprecated for newer models).
- Tool docs: [NumPy `linalg`](https://numpy.org/doc/stable/reference/routines.linalg.html) (the SVD/eigendecomposition Steps 3-4 run), [FastAPI](https://fastapi.tiangolo.com/), [SmolLM2](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) (the pinned victim, through `labs/_shared/tinylm`).

---

[← prev in path](../adapt-softprompt/README.md) · [All labs](../README.md) · [next in path →](../concept-memorization/README.md)
