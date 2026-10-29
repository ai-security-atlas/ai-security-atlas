---
lab_id: LAB-09
title: "Stealing a classifier through its API"
node: attack-model-imitation             # == folder name == articles/<node-id>.md basename
related_nodes: [goal-model-theft, adapt-distillation, concept-logits, eval-fidelity, eval-asr, eval-threat-model, defense-budget, defense-logging, attack-weight-theft, attack-distillation-theft, attack-projection-theft, arch-neural]
family: family-theft
access_profile: A02
level: beginner                          # beginner | intermediate | advanced
time: "60 min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory, 2.2 GB disk for the workbench image."
canary: ATLAS-CANARY-5e09
last_tested: 2026-10-26
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v2"
covers:                                  # nodes practiced here as named steps (optional; see _template)
  - {node: eval-fidelity, steps: "4", anchor: "step-4--agreement-is-not-the-same-weights--explainer-7"}
---

# LAB-09 · Stealing a classifier through its API

> **Atlas node:** [Black-box functional model extraction](https://ai-security-atlas.github.io/?node=attack-model-imitation) · **Family:** family-theft · **Level:** beginner · **Time:** 60 min · **Model backend:** none

## Overview

A model behind a prediction API still leaks itself one answer at a time. If you can send inputs and read the outputs, every answer is a free training label, and enough of them let you train a substitute that behaves like the original without ever seeing its weights or its training data. In this lab you train a small "proprietary" digit classifier, put it behind `victim-api` (a local FastAPI service with selectable answer detail, per-key query budgets and a query log), and copy it through that API with 25 to 1,200 queries. You measure how much the answer format matters (labels, top-3, full probabilities), show that a 99% copy shares almost nothing with the original's weights, and then measure four defenses: smaller answers, rounding, per-key budgets and a watermark plus fingerprint check. Source: [`labs/attack-model-imitation`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-model-imitation).

By the end you will be able to:

1. Copy a classifier through its API and plot fidelity (agreement with the victim) against the number of queries for each answer format.
2. Report a stolen model with three separate numbers (agreement, task accuracy, weight similarity) and explain why high agreement is not weight recovery.
3. Measure what label-only answers, rounding, query budgets and watermarks actually cost a thief, and name the gap each one leaves.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The victim is a classifier you train in Step 1, served by each script on `127.0.0.1` inside the workbench container; no query leaves the container. Never point these scripts at a real prediction API: copying a model you do not own is a question of query rights and licensing (the Atlas caveat), whatever the technical result. Every stolen copy in `work/` carries the fixed tag `ATLAS-CANARY-5e09` in its safetensors metadata, and the D3 watermark is keyed with the same string. The lab exists so you can measure extraction defenses, not to copy deployed models.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-model-imitation`](../../articles/attack-model-imitation.md) |
| Family | [`family-theft`](https://ai-security-atlas.github.io/?node=family-theft) |
| Goal | [`goal-model-theft`](https://ai-security-atlas.github.io/?node=goal-model-theft) |
| Access profile | `A01` Output-query access (caveat: *No weights, logits, training data or privileged context are implied.*) for the label-only rows, and `A02` Score or logit API access (caveat: *Specify score precision, top-k restrictions and any allowed logit transformations.*) for the top-k, probability and rounded rows |
| Read first | [`adapt-distillation`](https://ai-security-atlas.github.io/?node=adapt-distillation), [`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits) |
| Mitigated by | None in the seed graph. Defend uses [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget) and [`defense-logging`](https://ai-security-atlas.github.io/?node=defense-logging) as related, not mapped, plus output minimization and watermarking, which have no node yet. |
| Evaluated by | [`eval-fidelity`](https://ai-security-atlas.github.io/?node=eval-fidelity), [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`attack-weight-theft`](https://ai-security-atlas.github.io/?node=attack-weight-theft) (distinct from), [`attack-distillation-theft`](https://ai-security-atlas.github.io/?node=attack-distillation-theft), [`attack-projection-theft`](https://ai-security-atlas.github.io/?node=attack-projection-theft), [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) |

> [!NOTE]
> **Atlas caveat:** Functional fidelity is not equality of weights; query rights and licensing are separate policy questions.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls an LLM. The victim is a local classifier that the lab trains and serves with `victim-api` inside the workbench. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model backend. |
| external-api | n/a | — | Same. Do not adapt the scripts to a hosted prediction API (Safety). |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Each substitute trains in about 1–2 s on one thread. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB). The lab writes about 15 MB to `work/` (mostly query logs). |
| Total time | 60 min: about 6 min of commands, the rest reading and answering the questions |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done (the workbench image is built).
- Labs to finish first: none. [LAB-05 · What the API reveals](../concept-logits/README.md) covers logits and log-probabilities in more depth.
- Concepts to read first: [`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits) and [`adapt-distillation`](https://ai-security-atlas.github.io/?node=adapt-distillation).

## Explainer

```bash
# host
open attack-model-imitation/explainer/index.html        # macOS
# xdg-open attack-model-imitation/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In 10 steps the explainer follows one digit through the API at every detail level, the attacker's 600 queries, the targets the substitute is fitted to, the measured fidelity curves, the weights of victim and copy side by side, and the three defenses, all from a reference run of this lab.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=workbench` |
| host-ollama | `COMPOSE_PROFILES=workbench` |
| external-api | `COMPOSE_PROFILES=workbench` |
| none | `COMPOSE_PROFILES=workbench` |

This lab calls no model, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`. Only the banner differs.

### Setup 2 — Build and start

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
 Image atlas-labs/workbench:v2 Building
...
 Image atlas-labs/workbench:v2 Built
 Container atlas-labs-workbench-1 Started
```

What to notice: the image already has scikit-learn, FastAPI, uvicorn and httpx (workbench v2), so nothing is installed at run time.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu  scikit-learn 1.9.1  safetensors 0.8.0
[ok] fastapi 0.162.0  uvicorn 0.54.0  httpx 0.28.1
[ok] digits dataset bundled with scikit-learn: 1797 images of 64 pixels (no download)
[ok] victim-api fixture: served {'label': 'a', 'probs': [0.5, 0.5]} on 127.0.0.1 inside the container
[ok] work dir: /labs/attack-model-imitation/work (writable)
```

What to notice: the dataset ships inside scikit-learn, and the `victim-api` fixture starts and answers on `127.0.0.1` inside the container.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_train_victim | workbench | ≈5 s | 1 |
| 2 | s02_query_api | workbench | ≈3 s | 2 |
| 3 | s03_steal | workbench | ≈20 s | 3 |
| 4 | s04_compare | workbench | ≈5 s | 7 |
| 5 | s05_random_queries | workbench | ≈10 s | — |
| D1 | d1_output_minimization | workbench | ≈25 s | 8 |
| D2 | d2_budget_monitor | workbench | ≈5 s | 9 |
| D3 | d3_watermark_check | workbench | ≈6 s | 10 |
| D4 | — (Read) | — | — | — |

Runtimes were measured in the workbench container on the test machine, with other lab builds running at the same time, and include about 2 s of container start-up per `docker compose run`. `verify.py` runs the whole lab, Setup to Cleanup, in about 2 min.

### Step 1 — Train the "proprietary" victim · [explainer 1](explainer/index.html#attack-model-imitation/1)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/s01_train_victim.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · s01_train_victim.py · torch 2.14.1+cpu · backend none
dataset: sklearn digits 8x8, 1797 images, 10 classes (bundled, no download)
split: owner's private training set 900 · attacker's unlabelled pool 600 · held-out test 297
victim: MLP 64-64-10, 4,810 parameters, trained in 1.8s
victim test accuracy: 0.976 (290/297)
wrote /labs/attack-model-imitation/work/victim.safetensors (safetensors, tensors only)
```

What to notice: the attacker's pool and the test digits are disjoint from the owner's 900 training images, so the attacker never has the private data, only unlabelled digits of the same kind.

**Why**

The victim is a small neural network ([`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural)) saved as tensors only in `work/victim.safetensors`. The attacker in this lab never reads that file: everything it learns comes through the API, which is the A01/A02 threat model ([`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model)). Taking the file itself would be a different attack, [`attack-weight-theft`](https://ai-security-atlas.github.io/?node=attack-weight-theft).

### Step 2 — What one answer reveals · [explainer 2](explainer/index.html#attack-model-imitation/2)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/s02_query_api.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · s02_query_api.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:34385 (inside this container only)
GET /v1/model -> model atlas-digits-victim, 10 classes, 64 features, details ['label', 'topk', 'probs', 'logprobs']
true label of the query digit: 0
detail=label     {"label": "0"}
detail=topk      {"label": "0", "top_k": [{"label": "0", "p": 1.0}, {"label": "8", "p": 6.7e-05}, {"label": "6", "p": 4.6e-05}]}
detail=probs     {"label": "0", "probs": [1.0, 6.8e-10, 8.9e-11, 4.3e-11, 1.2e-07, 2.4e-05, 4.6e-05, 3.2e-09, 6.7e-05, 4.7e-06]}
detail=logprobs  {"label": "0", "logprobs": [-0.00014, -21.0, -23.0, -24.0, -16.0, -11.0, -10.0, -20.0, -9.6, -12.0]}
usage after 4 queries: {'key': 'demo', 'used': 4, 'budget': 20, 'remaining': 16}
20 more queries -> HTTP 429 query budget exceeded {'used': 4, 'budget': 20, 'remaining': 16}
query log work/s02_queries.jsonl: 5 lines; last: {"key": "demo", "n": 20, "requested": "label", "served": null, "status": 429}
label reveals 1 class of 10; probs and logprobs reveal all 10 numbers (smallest p 4.3e-11, logprob -23.9)
```

What to notice: the label is one class out of ten, while `probs` and `logprobs` return all ten numbers, down to probabilities of about 1e-11 that a rounded display shows as 0.

**Why**

`victim-api` serves the same model at four detail levels; `logprobs` are just the logarithms of `probs`, so at full precision they carry the same information but make the tiny values readable ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits)). Every request is counted against the key's budget and written to the query log, which D2 uses. The refused batch of 20 is answered with nothing at all, not with the 16 queries left.

### Step 3 — Steal it at three detail levels · [explainer 3](explainer/index.html#attack-model-imitation/3)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/s03_steal.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · s03_steal.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:48405 (inside this container only)
queried 600 pool digits x 3 detail levels in 0.4s (log: work/s03_queries.jsonl)
fidelity = agreement with the victim on 297 held-out digits
 queries    label     topk    probs
      25    0.727    0.613    0.862
      50    0.808    0.808    0.946
     100    0.848    0.865    0.953
     200    0.909    0.953    0.976
     400    0.960    0.983    0.983
     600    0.963    0.990    0.993
queries to reach 95% agreement: label 400, topk 200, probs 100
wrote work/copy_label.safetensors work/copy_topk.safetensors work/copy_probs.safetensors (tag ATLAS-CANARY-5e09) in 18s
```

What to notice: with full probabilities the copy agrees with the victim on 95% of unseen digits after 100 queries; labels alone need 400 queries for the same mark.

**Why**

The attacker treats the API as a labelling oracle and fits a fresh MLP to its answers, which is knowledge distillation run through someone else's API ([`adapt-distillation`](https://ai-security-atlas.github.io/?node=adapt-distillation)). A label carries at most one class per query, while a probability vector also says how the model ranks the other nine classes, so each richer answer constrains the copy more ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits)). One learning rule is used for every level: cross-entropy on the label plus a squared-error match on whatever log-probabilities the API revealed.

### Step 4 — Agreement is not the same weights · [explainer 7](explainer/index.html#attack-model-imitation/7)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/s04_compare.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · s04_compare.py · torch 2.14.1+cpu · backend none
victim: test accuracy 0.976, wrong on 7 of 297 held-out digits
model          agreement  accuracy  errors  cosine aligned r
copy (probs)       0.993     0.976     6/7   0.031      0.47
copy (label)       0.963     0.963     3/7  -0.024      0.58
independent        0.973     0.983     2/7   0.009      0.56
agreement and accuracy are about behaviour; cosine and aligned r are about weights
```

What to notice: the probability copy agrees with the victim on 99.3% of held-out digits and repeats 6 of its 7 mistakes, yet its weights are less similar to the victim's (aligned r 0.47) than those of an independent model that never queried the API (0.56).

**Why**

[`eval-fidelity`](https://ai-security-atlas.github.io/?node=eval-fidelity) asks for separate numbers: functional agreement with the target, task accuracy, and parameter recovery. Agreement on the victim's mistakes is what separates a copy from a model that is merely good at the task. Many different weight settings compute the same function (hidden units can be reordered, for a start), so a high-fidelity copy is not the original's weights, which is exactly the Atlas caveat, and all of these numbers hold only for the input distribution they were measured on.

### Step 5 — No data: random queries

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/s05_random_queries.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · s05_random_queries.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:44641 (inside this container only)
victim's answers to noise, per class: 0:38 1:28 2:250 3:9 4:470 5:19 6:6 7:196 8:144 9:40
top-p of the answers: median 0.88 (held-out digits: 1.00)
 queries    label    probs
     100    0.330    0.717
     300    0.566    0.872
     600    0.721    0.862
    1200    0.768    0.879
with 600 real digits (Step 3): label 0.963  probs 0.993
```

What to notice: random noise lands mostly in classes 4, 2 and 7, so even 1,200 noise queries copy the victim worse than 50 real digits did in Step 3, and probabilities help far more than labels here.

**Why**

What the attacker asks matters as much as how many questions: queries near the real data probe the decision boundaries that matter, which is the point of Knockoff Nets and of the [`attack-model-imitation`](https://ai-security-atlas.github.io/?node=attack-model-imitation) threat model. Noise queries are also unusual: the victim answers them with low confidence, which the D2 monitor uses. Do not read this as "no data, no theft": real attackers use public data from a similar domain.

## Defend

### Step D1 — Answer with less: labels and rounding · [explainer 8](explainer/index.html#attack-model-imitation/8)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/d1_output_minimization.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · d1_output_minimization.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:40049 (inside this container only)
attacker asks for probs; every policy serves the same labels: True
policy         served      50    100    200    600   (queries -> fidelity)
probs (full)   probs    0.946  0.953  0.976  0.993
probs round 2  probs    0.842  0.865  0.933  0.990
probs round 1  probs    0.828  0.869  0.916  0.983
top-1 + p      topk     0.832  0.855  0.902  0.970
label only     label    0.808  0.848  0.909  0.963
```

What to notice: rounding to two decimals already removes most of the advantage of probabilities (0.842 instead of 0.946 at 50 queries), but at 600 queries every policy still yields a copy that agrees at 96% or more.

**Why**

The richest part of a probability vector is its tail of tiny values, and rounding sets them to zero, so the thief is left with roughly the information of a label ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits)). Honest users keep the same labels in every policy, so minimization is cheap when they do not need scores. Limitation: it raises the number of queries a copy needs, it does not prevent the copy ([`attack-model-imitation`](https://ai-security-atlas.github.io/?node=attack-model-imitation)).

### Step D2 — Budgets per key, and what the log shows · [explainer 9](explainer/index.html#attack-model-imitation/9)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/d2_budget_monitor.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · d2_budget_monitor.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:41211 (inside this container only)
thief, 1 key: 100 answers, then HTTP 429 ({'used': 100, 'budget': 100, 'remaining': 0})
thief, 6 keys x 100: 600 answers, no 429
fidelity: 1 key 0.848 · 6 keys 0.963
monitor over work/d2_queries.jsonl:
key          served refused low-conf  flags
thief           100      50     0.06  at budget, refused
sybil-1         100       0     0.06  at budget
sybil-2         100       0     0.08  at budget
sybil-3         100       0     0.11  at budget
sybil-4         100       0     0.06  at budget
sybil-5         100       0     0.06  at budget
sybil-6         100       0     0.04  at budget
app-user         60       0     0.12  -
noise-probe     100       0     0.54  at budget, low-confidence
```

What to notice: one key is cut off at 100 queries and gets a 0.848 copy, but six keys with the same budget get 600 answers and a 0.963 copy; in the log each sybil key looks just like the first one, and only the noise prober stands out as low-confidence.

**Why**

A per-key budget ([`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget), related here) caps what one account can learn, and the query log ([`defense-logging`](https://ai-security-atlas.github.io/?node=defense-logging)) is where you see who hits the cap. Limitation: budgets bind keys, not people, so they only work together with account verification and limits across accounts, and an attacker using in-distribution data looks like an honest user in this monitor.

### Step D3 — Prove a copy: watermark and fingerprint · [explainer 10](explainer/index.html#attack-model-imitation/10)

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/d3_watermark_check.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · d3_watermark_check.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:59119 (inside this container only)
watermark: secret ATLAS-CANARY-5e09, rate 2% -> 18 of 1200 answers were deliberately wrong
suspect        wm set         hits        p  fingerprint
copy (label)   thief-label    9/9     1e-09         0.37
copy (probs)   thief-probs    0/9     1e+00         0.64
independent    thief-label    0/9     1e+00         0.37
independent    thief-probs    0/9     1e+00         0.37
cost: every caller, honest or not, got a deliberately wrong label on 1.5% of answers; the label copy scores 0.926 on the test digits
```

What to notice: the watermark catches the label-only copy (9 of 9 deliberately wrong answers repeated, p ≈ 1e-9) and misses the probability copy (0 of 9), while the fingerprint flags the probability copy (0.64 against 0.37 for the independent model) and not the label copy.

**Why**

A watermark (DAWN-style: a keyed hash selects about 2% of inputs, here 18 of 1,200 answers, which get a deliberately wrong label recorded per key) does not stop extraction; it gives the owner evidence afterwards that a suspect model learned from their answers ([`eval-fidelity`](https://ai-security-atlas.github.io/?node=eval-fidelity) measures the agreement it relies on). Here the copy fitted to full probabilities smoothed the swapped answers away, and the fingerprint (agreement on ambiguous inputs where two honest models disagree) caught it instead, so neither check covers both thieves. Limitation: both need query access to the suspect, the watermark costs every user some wrong answers, and an attacker who filters or fine-tunes can weaken either signal.

### Step D4 — Combine the controls, and keep the policy question separate

**Read**

None of the measured defenses stops a determined thief alone: minimization (D1) multiplies the queries needed, budgets (D2) multiply the accounts needed, and the watermark and fingerprint (D3) make a copy provable afterwards. Used together, a label-only API with per-key budgets, cross-account limits, a query log and a watermark makes extraction slower, more expensive and more likely to leave evidence. Published detectors that watch the query distribution (PRADA) target synthetic queries, and Step 5 shows why: queries far from the data stand out, while a thief with in-distribution data looks like an honest user. Whether a given copy is allowed is decided by your terms of service and licensing, not by fidelity numbers.

**Why**

The Atlas lists no mitigation node for this attack; [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget) and [`defense-logging`](https://ai-security-atlas.github.io/?node=defense-logging) are the closest related controls. Evaluate each control against an attacker who adapts to it (more keys, better data, smoothing), as in [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model).

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-model-imitation · evaluate.py · torch 2.14.1+cpu · backend none
measurement                        value
fidelity probs@50                  0.946
fidelity label@50                  0.808
fidelity probs@100                 0.953
fidelity label@200                 0.909
fidelity round-2@50                0.842
fidelity probs@600                 0.993
fidelity budget: 1 key             0.848
fidelity budget: 6 keys            0.963
queries served to 1 budget key     100
watermark hits, label copy         1.00
watermark hits, probs copy         0.00
watermark hits, independent        0.00
fingerprint, label copy            0.37
fingerprint, probs copy            0.64
...
[ok] fingerprint flags the probs copy: True
RESULT: REPRODUCED
```

`evaluate.py` re-measures the attack and each defense in one run (it needs only Step 1's victim) and compares the shape of the results, not exact numbers, with `expected/evaluate.json`. `RESULT` says only whether the run matches that shape; the table is the security verdict.

Questions for your notes:

1. How many queries does the label-only thief need to match what the probability thief has after 50, and what does that ratio mean for a per-key budget?
2. Which single number in Step 4 would you report to claim "this model was copied", and why is neither cosine nor aligned r that number?
3. The watermark and the fingerprint each catch one copy. Which would you deploy for a label-only API, and what would an attacker change to defeat it?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-model-imitation/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-model-imitation · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-model-imitation/work (compare.json copy_label.safetensors copy_probs.safetensors copy_topk.safetensors d1.json d1_queries.jsonl d2.json d2_queries.jsonl d3.json d3_queries.jsonl d3_queries.wm.jsonl eval_queries.jsonl eval_wm_queries.jsonl eval_wm_queries.wm.jsonl evaluate.json independent.safetensors noise.json s02.json s02_queries.jsonl s03_queries.jsonl s05_queries.jsonl steal.json verify.log victim.json victim.safetensors)
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Add a cross-key monitor to `d2_budget_monitor.py` that groups keys by when they were created and how they query, and measure how many of the six sybil keys it links without flagging `app-user`.
- Change the D3 watermark so that it survives the probability thief (for example, perturb the whole probability vector instead of swapping two entries) and measure the cost in wrong answers for honest users.
- Rerun Step 3 with `KeyPolicy(round_digits=3)` and `round_digits=4` and find the coarsest rounding at which probabilities stop helping the thief.
- Train the copy as a different architecture (logistic regression, or a wider MLP) and check whether Step 4's agreement and error-repeat numbers change.

## Further Reading

- Tramèr et al., [Stealing Machine Learning Models via Prediction APIs](https://www.usenix.org/conference/usenixsecurity16/technical-sessions/presentation/tramer) (USENIX Security 2016), seed source `s-api-stealing`: extraction through prediction APIs, and how output detail and rounding change it.
- Orekondy et al., [Knockoff Nets: Stealing Functionality of Black-Box Models](https://openaccess.thecvf.com/content_CVPR_2019/html/Orekondy_Knockoff_Nets_Stealing_Functionality_of_Black-Box_Models_CVPR_2019_paper.html) (CVPR 2019), seed source `s-knockoff`: query data and functionality stealing.
- Hinton et al., [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531) (2015): soft targets.
- Juuti et al., [PRADA: Protecting Against DNN Model Stealing Attacks](https://arxiv.org/abs/1805.02628) (EuroS&P 2019): query-distribution monitoring.
- Szyller et al., [DAWN: Dynamic Adversarial Watermarking of Neural Networks](https://arxiv.org/abs/1906.00830) (ACM MM 2021): the watermark used in D3.
- Jagielski et al., [High Accuracy and High Fidelity Extraction of Neural Networks](https://arxiv.org/abs/1909.01838) (USENIX Security 2020): accuracy versus fidelity as separate goals.
- Tool docs: [scikit-learn `load_digits`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html), [FastAPI](https://fastapi.tiangolo.com/), and the fixture docstring in [`labs/_shared/victim_api/__init__.py`](../_shared/victim_api/__init__.py).

---

[← prev](../attack-fgsm/README.md) · [All labs](../README.md) · [next →](../attack-dependency/README.md)
