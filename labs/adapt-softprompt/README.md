---
lab_id: LAB-58
title: "A prompt you cannot read"
node: adapt-softprompt
related_nodes: [adapt-peft, concept-embeddings, adapt-prefix, adapt-lora, adapt-textual-inversion, concept-kv-cache, concept-attention, attack-gcg, attack-backdoor, attack-sft-poison, attack-unsafe-load, defense-provenance, defense-regression, eval-utility]
family: family-training
access_profile: A09
level: intermediate
time: "60 min"
compose_profiles: [workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 2 GB Docker VM memory. 2.4 GB disk for the workbench image plus 0.27 GB for the SmolLM2-135M-Instruct checkpoint."
canary: ATLAS-CANARY-s0ft
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
covers:
  - {node: adapt-prefix, steps: "4", anchor: "step-4--move-the-prompt-inside-every-layer-14-min--explainer-4"}
---

# LAB-58 · A prompt you cannot read

> **Atlas node:** [Soft prompt tuning](https://ai-security-atlas.github.io/nodes/adapt-softprompt/) · **Family:** family-training · **Level:** intermediate · **Time:** 60 min · **Model backend:** none

> **Learning path:** Module 9 · step 7 of 8 · [Inside the transformer](../README.md#module-9-inside-the-transformer)

## Overview

A prompt is usually text you can read before you use it. Soft prompt tuning replaces that text with a few learned input vectors placed in front of every request, where [token](../primers/inside-a-transformer-block.md#token) vectors would normally go (the [embedding table](../primers/inside-a-transformer-block.md#token-embedding) holds one vector per token). Only those vectors are trained, and the model's own [weights](../primers/ml-in-one-page.md#weights-and-parameters) stay frozen. The result is a small file that steers a shared model toward one task, and nobody can read it as words, so reviewing it works differently.

What you will do:

- route fictional support tickets to one of four queues with SmolLM2-135M-Instruct, first with plain text, then with eight learned vectors;
- try to read the learned vectors back as words;
- move the same idea into every layer's [attention](../primers/inside-a-transformer-block.md#attention) with prefix tuning;
- receive a second file with the same shape, size and settings, trained on rows whose billing and shipping labels were swapped (account and other keep their labels), and route tickets with it while a stub router logs the inert canary `ATLAS-CANARY-s0ft` for each misrouted ticket;
- defend with a hash pin on the approved file and a behavior gate on labeled rows you own.

Headline result: a written instruction gets 6 of 24 held-out tickets right, eight learned vectors (4,608 numbers, an 18 KB file) get 18, and their nearest words get 7. The swapped file misroutes 15 of 24 tickets, and static checks can't tell it from the approved file; only the hash pin and the behavior gate separate them.

Source: [`labs/adapt-softprompt`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/adapt-softprompt).

By the end you will be able to:

1. Train a soft prompt and a prefix with peft on a frozen model, and say where each puts its learned numbers and how many there are.
2. Show that a soft prompt's nearest tokens neither read as an instruction nor do the job, so a prompt file can't be reviewed by reading it.
3. Apply a hash pin and a behavior gate to prompt files, and state what each one catches and what it misses.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The task is a fictional support desk, and every message is hardcoded in `scripts/spl.py`. The "router" is a Python function that prints which queue a ticket would go to. It logs the inert canary `ATLAS-CANARY-s0ft` for each ticket it sends to the wrong queue, and it sends nothing anywhere. The second prompt file in Step 5 is trained on swapped labels; it carries no trigger and no hidden instruction.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`adapt-softprompt`](../../articles/adapt-softprompt.md) |
| Family | None in the seed graph (a method node). The front matter and explainer kicker use [`family-training`](https://ai-security-atlas.github.io/nodes/family-training/), the family [LAB-07](../adapt-lora/README.md) uses for the other parameter-efficient method, because a soft prompt is a training artifact. |
| Goal | None in the seed graph. Step 5's file changes where tickets go, which is the [`goal-behavior`](https://ai-security-atlas.github.io/nodes/goal-behavior/) shape, with an inert canary as the only effect. |
| Access profile | `A09` Writable or replaceable model artifacts (caveat: *Use separate calibration/runtime-read capabilities where the method requires them.*): the risk this lab measures is a prompt file that someone else trained or replaced before it reached you. Training one yourself (Steps 2, 4 and 5) needs the weights and gradients of a local copy, which is `A11`. |
| Read first | [`adapt-peft`](https://ai-security-atlas.github.io/nodes/adapt-peft/) and [`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/) (the seed prerequisites) |
| Mitigated by | None in the seed graph. D1 pins the file by hash ([`defense-provenance`](https://ai-security-atlas.github.io/nodes/defense-provenance/), practiced in [LAB-01](../attack-unsafe-load/README.md)), and D2 is a behavior gate ([`defense-regression`](https://ai-security-atlas.github.io/nodes/defense-regression/), which has its own planned lab). Both are related, not mapped. |
| Evaluated by | [`eval-utility`](https://ai-security-atlas.github.io/nodes/eval-utility/) (the held-out task score every step and the D2 gate report) |
| Related | Covered here: [`adapt-prefix`](https://ai-security-atlas.github.io/nodes/adapt-prefix/) (Step 4). Sibling methods: [`adapt-lora`](https://ai-security-atlas.github.io/nodes/adapt-lora/), [`adapt-textual-inversion`](https://ai-security-atlas.github.io/nodes/adapt-textual-inversion/). The prefix lands in the [`concept-kv-cache`](https://ai-security-atlas.github.io/nodes/concept-kv-cache/) slots that [`concept-attention`](https://ai-security-atlas.github.io/nodes/concept-attention/) reads. The discrete, text-only cousin of the optimization is [`attack-gcg`](https://ai-security-atlas.github.io/nodes/attack-gcg/); training-time tampering is [`attack-sft-poison`](https://ai-security-atlas.github.io/nodes/attack-sft-poison/) and [`attack-backdoor`](https://ai-security-atlas.github.io/nodes/attack-backdoor/); loading a file you did not make is [`attack-unsafe-load`](https://ai-security-atlas.github.io/nodes/attack-unsafe-load/). |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this method node. Its article leaves "how the number of soft-prompt vectors trades off against capacity, and how performance scales with model size" to the cited source. This lab measures one 135M-parameter model, one task with 40 training and 24 held-out rows, 8 virtual tokens and one seed. Lester et al. report that prompt tuning closes the gap to full fine-tuning only at billions of parameters, so the scores here say nothing about larger models.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | Prompt tuning needs gradients through a local copy of the model, so every step runs in the workbench. No chat backend is involved. |
| host-ollama | n/a | — | Same reason. |
| external-api | n/a | — | Same reason. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU. Each 45-step training run (Steps 2, 4, 5 and Evaluate) took 41–63 s on an M4 Max at a load average near 10 from other jobs, and 76–142 s at a load average of 16–25. Every other step takes under 30 s. |
| Docker VM memory | 2 GB (the 134.5M-parameter model in float32 is about 0.54 GB, plus gradients for a batch of 40 short rows). |
| Disk | Workbench image 2.4 GB, the 0.27 GB checkpoint in the HF cache volume, and under 1 MB of prompt files in `work/`. |
| Total time | About 60 min: 4–10 min of commands on the shared test machine, plus reading. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: [LAB-25 · Vectors that are not words](../concept-embeddings/README.md) (the embedding table and the `inputs_embeds` door); [LAB-26 · Who attends to whom](../concept-attention/README.md) (how the prepended vectors reach every later token); [LAB-07 · What a 2 MB adapter changes](../adapt-lora/README.md) (the LoRA side of parameter-efficient tuning).
- Concepts to read first: [`adapt-peft`](https://ai-security-atlas.github.io/nodes/adapt-peft/) and [`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/).

## Explainer

```bash
# host
open adapt-softprompt/explainer/index.html        # macOS
# xdg-open adapt-softprompt/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in eight steps: the task and its readable baselines, training the soft prompt, reading it back, prefix tuning, the swapped file with its canary, static inspection, the behavior gate and the evaluation.

## Setup

### Setup 1 — Profiles

Run the line for your backend in the terminal you use for this lab. It names this lab's Compose project and selects its services, so the commands below need no prefix and Cleanup stops only this lab. Run it again in any new terminal. The backend settings stay in `labs/.env` (Start here, step 2, in the [labs index](../README.md)).

| Backend | Line to run |
| :--- | :--- |
| container-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-adapt-softprompt COMPOSE_PROFILES=workbench` |
| host-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-adapt-softprompt COMPOSE_PROFILES=workbench` |
| external-api | `export COMPOSE_PROJECT_NAME=atlas-labs-adapt-softprompt COMPOSE_PROFILES=workbench` |
| none | `export COMPOSE_PROJECT_NAME=atlas-labs-adapt-softprompt COMPOSE_PROFILES=workbench` |

This lab calls no model backend, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`, which is what you see when no `LAB_BACKEND` line is active.

### Setup 2 — Build and start

Skip the `docker compose build` line if the workbench image is already on your machine (an earlier lab built it, or your workshop pre-loaded it). The first build takes a few minutes.

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
...
 Image atlas-labs/workbench:v4 Built
...
 Container atlas-labs-adapt-softprompt-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image; this lab needs nothing beyond the shared workbench image (torch, transformers, peft, safetensors).

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu transformers 5.20.2 peft 0.21.2 safetensors 0.8.0
[ok] torch threads 4 (spl caps at 4)
[ok] model HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f (fetched in Step 1); canary ATLAS-CANARY-s0ft
[ok] task: 40 training rows, 24 held-out rows, queues billing, shipping, account, other
[ok] work dir: /labs/adapt-softprompt/work (writable)
[skip] model backend: this lab needs none
```

What to notice: peft 0.21.2 provides both `PromptTuningConfig` and `PrefixTuningConfig`; the model is pinned by commit and is fetched in Step 1.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_task | workbench | ≈10 s (plus download) | 1 |
| 2 | s02_train | workbench | ≈1–4 min | 2 |
| 3 | s03_read | workbench | ≈10 s | 3 |
| 4 | s04_prefix | workbench | ≈1–4 min | 4 |
| 5 | s05_swapped | workbench | ≈1–4 min | 5 |
| D1 | d1_inspect | workbench | ≈10 s | 6 |
| D2 | d2_acceptance | workbench | ≈30 s | 7 |
| Evaluate | evaluate | workbench | ≈1–4 min | 8 |

Runtimes are wall-clock times of `docker compose run` on the test machine while other heavy jobs shared its CPU (load average 9–25 on 16 cores). The same 45 training steps took 41–63 s at a load near 10 and 76–142 s at the higher loads. `spl.py` caps torch at 4 threads. Container start and model load take about 4 s of each step.

### Step 1 — The task and two readable baselines · [explainer 1](explainer/index.html#adapt-softprompt/1)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/s01_task.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · s01_task.py · torch 2.14.1+cpu · backend none
smollm2-135m: 134.5M params, 30 layers, width 576, vocab 49152 (loaded in 3.6s)
queue words -> one token each: billing=38971, shipping=12497, account=2051, other=550
task: 40 training rows, 24 held-out rows (6 per queue), answer = argmax over the 4 queue words after 'Queue:'
no instruction       held-out 9/24  predicted billing:0 shipping:14 account:0 other:10
written instruction  held-out 6/24  predicted billing:24 shipping:0 account:0 other:0
the written instruction is 46 tokens of plain text; anyone can read it
```

What to notice: the written instruction makes the score worse (6/24, every ticket goes to billing), so on this small model readable text alone can't do the job.

**Why**

Each queue name is a single token, so the lab scores a ticket by asking which of the four queue words the model ranks highest after `Queue:`. That gives every setup in the lab the same yardstick, and chance is 6/24. A 135M-parameter model follows instructions poorly, which is why a task-specific adaptation helps here. Parameter-efficient fine-tuning adapts a frozen model by training a small added set of numbers ([`adapt-peft`](https://ai-security-atlas.github.io/nodes/adapt-peft/)).

### Step 2 — Train eight vectors, freeze the rest (≈1–4 min) · [explainer 2](explainer/index.html#adapt-softprompt/2)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/s02_train.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · s02_train.py · torch 2.14.1+cpu · backend none
soft prompt: 8 vectors x 576 = 4608 trainable numbers; 134.5M model weights frozen (0.0034%)
one message: 17 token rows -> the model sees 25 input rows (8 learned rows first, then the message)
  step  1  loss 10.420
  step 10  loss 6.359
  step 20  loss 1.361
  step 30  loss 0.805
  step 40  loss 0.288
trained in 58s: training rows 40/40, held-out 18/24 (written instruction: see Step 1)
saved adapt-softprompt/work/softprompt/adapter_model.safetensors (18552 bytes) sha256 b93b49a924ca5cc9
  [router] billing  -> shipping 'Send me the invoice for order 4471' -> ATLAS-CANARY-s0ft
  [router] shipping -> billing  'Half of my order is missing from the box' -> ATLAS-CANARY-s0ft
  [router] account  -> other    'I cannot sign in with my phone' -> ATLAS-CANARY-s0ft
  [router] other    -> shipping 'Is the café open on Sunday' -> ATLAS-CANARY-s0ft
  ... (2 more)
router: 6/24 held-out tickets misrouted, canary ATLAS-CANARY-s0ft logged for each
```

What to notice: 4,608 trained numbers lift the held-out score from 6/24 to 18/24 while all 134.5M weights stay frozen, and the stub router logs the canary for the 6 tickets that still go to the wrong queue.

**Why**

peft's `PromptTuningConfig` adds an 8 × 576 table and puts its rows in front of the message's token vectors, so the model reads 25 rows instead of 17 ([`adapt-softprompt`](https://ai-security-atlas.github.io/nodes/adapt-softprompt/)). Training is ordinary [gradient](../primers/ml-in-one-page.md#gradient) descent (45 full-batch Adam steps at [learning rate](../primers/ml-in-one-page.md#learning-rate) 0.3), with the [loss](../primers/ml-in-one-page.md#loss-and-cross-entropy) on the queue word only. The gradient flows back through the frozen layers, and only those 8 rows are updated. The batch is padded on the right, so each message keeps the positions it would have if it were sent alone. With left padding, the pad rows would sit between the learned rows and the message, and a ticket's route could change with the other tickets in its batch; a review of this lab measured 4 of 24 held-out routes changing that way. The saved file is 18 KB of safetensors next to a small JSON config. A loader still needs the right base model to use it, since the vectors mean something only in that model's embedding space ([`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/)). The seed is fixed, and the same machine produced the same sha256 on every run.

### Step 3 — Try to read it · [explainer 3](explainer/index.html#adapt-softprompt/3)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/s03_read.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · s03_read.py · torch 2.14.1+cpu · backend none
file tensors: prompt_embeddings (8, 576) torch.float32
vector  norm   nearest token        cosine  distance
  v0    51.01  'Ġmid'                0.141  50.743
  v1    53.04  'ĠNot'                0.134  52.796
  v2    47.34  'ĠMorgan'             0.122  47.109
...
  v6    49.54  'Ġconvert'            0.170  49.201
  v7    59.49  'Ġcould'              0.126  59.220
vocabulary rows: norm median 3.15, range 1.79-7.49
for scale: a real token's nearest other token has cosine median 0.581 (first 2000 rows)
nearest-token text: ' mid Not Morgan relevant ash bind convert could'
held-out with the learned vectors: 18/24; with their nearest tokens as text: 7/24
```

What to notice: no learned vector gets above cosine 0.17 with any token (a real token's nearest neighbor sits at a median of 0.58), the vectors are six to eight times longer than the longest token row, and their nearest words score 7/24, close to the written instruction's 6/24.

**Why**

[Cosine similarity](../primers/vectors-without-the-math.md#cosine-similarity) measures how closely two vectors point the same way. A soft prompt is free to sit anywhere in the 576-dimensional space, and nothing pulls it toward the 49,152 token rows ([`concept-embeddings`](https://ai-security-atlas.github.io/nodes/concept-embeddings/), [LAB-25](../concept-embeddings/README.md)). The long norms start with peft's random init, a standard normal draw with length about 24 (D1's untrained file shows 22.4–25.9), and training at learning rate 0.3 roughly doubles them. For a reviewer, the file can't be read the way a prompt can. What it does is decided by training data that the file doesn't carry. [LAB-21](../attack-gcg/README.md) shows the other side of this gap: an optimizer limited to real tokens has to search the vocabulary one token at a time ([`attack-gcg`](https://ai-security-atlas.github.io/nodes/attack-gcg/)).

### Step 4 — Move the prompt inside every layer (≈1–4 min) · [explainer 4](explainer/index.html#adapt-softprompt/4)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/s04_prefix.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · s04_prefix.py · torch 2.14.1+cpu · backend none
prefix: 30 layers x (keys + values) x 3 kv heads x 8 positions x 64 = 92160 trainable numbers
  layer 0 keys (1, 3, 8, 64)  values (1, 3, 8, 64)  (... same shape in all 30 layers)
one message: input rows stay 17; every layer's attention also sees 8 learned positions
  step  1  loss 13.231
  step 10  loss 0.903
  step 20  loss 0.114
  step 30  loss 0.015
  step 40  loss 0.004
trained in 41s: training rows 40/40, held-out 21/24
method          trainable  file bytes  enters at        train   held-out
soft prompt          4608       18552  input (layer 0)  40/40   18/24
prefix tuning       92160      368760  every layer      40/40   21/24
```

What to notice: the prefix has 20 times as many numbers and a file 20 times larger, both methods fit all 40 training rows, and the prefix gets 21 of 24 new tickets right against 18 for the 8-vector soft prompt.

**Why**

In plain words: inside attention, each token offers a key (what it contains, used to decide who looks at it) and a value (what it passes on to the tokens that look at it), and later tokens read earlier ones through these keys and values. `PrefixTuningConfig` learns, for each of the 30 layers, 8 extra key and value positions that the attention of every real token can attend to; peft hands them to the model as a `past_key_values` cache, so the input itself stays 17 rows ([`adapt-prefix`](https://ai-security-atlas.github.io/nodes/adapt-prefix/), [`concept-kv-cache`](https://ai-security-atlas.github.io/nodes/concept-kv-cache/)). SmolLM2 uses [grouped-query attention](../primers/inside-a-transformer-block.md#gqa) with 3 key-value heads of 64 numbers, so each layer's prefix is 3 × 8 × 64 for keys and again for values. Learned positions in every layer give the optimizer more to work with than one set of input rows. Lester et al. also report that prompt tuning lags full fine-tuning on small models and catches up only at billions of parameters. Both methods use the same seed and 45 steps, and each uses its own learning rate. Those rates come from a small sweep scored on these same held-out rows, so both held-out scores are a little optimistic. At 45 steps the soft prompt scored 18, 16 and 18 of 24 at rates 0.03, 0.1 and 0.3, and the prefix scored 18 and 21 at 0.01 and 0.03; at 0.1 the prefix fit only 15 of 40 training rows in 30 steps and scored 6. Li and Liang add a reparameterization network for stability, which peft offers as `prefix_projection=True` and this lab leaves off.

### Step 5 — A second file, same shape (≈1–4 min) · [explainer 5](explainer/index.html#adapt-softprompt/5)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/s05_swapped.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · s05_swapped.py · torch 2.14.1+cpu · backend none
  step  1  loss 11.028
  step 10  loss 5.628
  step 20  loss 1.771
  step 30  loss 1.244
  step 40  loss 1.393
trained in 55s; saved softprompt-swapped/adapter_model.safetensors (18552 bytes) sha256 ddb6cd9286bd3cb7
compared with Step 2's file: same size True, config keys that differ: none
held-out against the true queues: 9/24; against the swapped queues: 9/24
  [router] billing  -> other    'There is a charge I do not recognise on my statement' -> ATLAS-CANARY-s0ft
  [router] billing  -> shipping 'The bill total does not match the cart' -> ATLAS-CANARY-s0ft
  [router] billing  -> shipping 'I paid but the order says unpaid' -> ATLAS-CANARY-s0ft
  [router] billing  -> shipping 'Stop charging my card every month' -> ATLAS-CANARY-s0ft
  ... (11 more)
router: 15/24 held-out tickets misrouted, canary ATLAS-CANARY-s0ft logged for each
on its own training rows it follows the swapped labels 19/40 (Step 2's file fits its labels 40/40)
```

What to notice: the file has the same size and the same config as Step 2's, and nothing about it says it was trained differently; attached, it misroutes 15 of 24 tickets (Step 2's file: 6), and the canary marks each one.

**Why**

The swapped file's training rows swap billing and shipping; account and other keep their labels. It stands for a prompt file that reached you mislabeled, mixed up with another team's file, or replaced. That is the writable or replaceable artifact access of `A09`, the setting [LAB-01](../attack-unsafe-load/README.md) starts from for model files ([`attack-unsafe-load`](https://ai-security-atlas.github.io/nodes/attack-unsafe-load/)). The swap itself only half took: the swapped file follows its own labels on 19 of 40 training rows and on 9 of 24 new tickets, and its loss stalls near 1.4 while Step 2's falls to 0.29. A likely reason is that the frozen model already ties "billing" to charges, and eight vectors have to pull against that. So the swapped file is also a poorly trained file: it fits fewer of its own rows than the 20 account and other rows whose labels never changed, and the account queue falls to 1 of 6 in D2. Either way, the file routes badly, and nothing in it shows that. Changing what a model does by changing its training data is the subject of [LAB-16](../attack-sft-poison/README.md) and [LAB-18](../attack-backdoor/README.md) ([`attack-sft-poison`](https://ai-security-atlas.github.io/nodes/attack-sft-poison/), [`attack-backdoor`](https://ai-security-atlas.github.io/nodes/attack-backdoor/)). This lab plants no trigger; the only effect is the router's canary line.

## Defend

### Step D1 — What static checks can tell · [explainer 6](explainer/index.html#adapt-softprompt/6)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/d1_inspect.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · d1_inspect.py · torch 2.14.1+cpu · backend none
pinned sha256 (recorded when you approved Step 2's prompt): b93b49a924ca5cc9
file                  format       shape      config   norms        max nearest cos  sha256 pin
softprompt            safetensors  (8, 576)   same     47.34-59.49            0.170  match
softprompt-swapped    safetensors  (8, 576)   same     48.31-54.74            0.164  MISMATCH
softprompt-untrained  safetensors  (8, 576)   same     22.40-25.91            0.160  MISMATCH
norm check (any vector longer than every vocabulary row, max 7.49): flags 3/3 (it flags soft prompts as such, not a wrong one)
text check (nearest-token cosine >= 0.5): flags 3/3 as unreadable
norm ranges: approved and swapped overlap True; untrained overlaps a trained file False
static checks tell the approved file from the swapped one: no; the sha256 pin accepts 1/3
```

What to notice: format, shape, config and nearest tokens look alike for all three files. The norms give away the untrained file (22.4–25.9, the size of peft's random start, against 47–59 for the trained ones), but the approved and swapped ranges overlap. Only the sha256 pin separates the approved file from the swapped one, and it accepts exactly the file you approved.

**Why**

Static checks are still worth running. Safetensors can't run code on load, unlike a pickle ([LAB-01](../attack-unsafe-load/README.md)), and the norm check tells you a file holds soft-prompt vectors and no token rows. Norms can also hint that a file was never trained. None of these says what trained vectors do. A hash pin is the only static check here that separates the files. It works because you recorded the hash when you approved the file, so it proves the file is unchanged since then and nothing more ([`defense-provenance`](https://ai-security-atlas.github.io/nodes/defense-provenance/)). Limitation: a pin can't tell you whether the first file you approved was a good one.

### Step D2 — Accept a file only after a behavior test · [explainer 7](explainer/index.html#adapt-softprompt/7)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/d2_acceptance.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · d2_acceptance.py · torch 2.14.1+cpu · backend none
gate: held-out >= 16/24 and every queue >= 3/6
prompt file           held-out  billing shipping account other  canary lines  verdict
softprompt            18/24     5/6     5/6      5/6     3/6     6            ACCEPT
softprompt-swapped     9/24     1/6     4/6      1/6     3/6    15            REJECT
softprompt-untrained   6/24     0/6     6/6      0/6     0/6    18            REJECT
prefix                21/24     5/6     4/6      6/6     6/6     3            ACCEPT
accepted: softprompt, prefix; rejected 2/4
```

What to notice: the Step 2 file and the Step 4 prefix pass, so the gate judges behavior and doesn't care which method made the file. The swapped file fails on its total and on the billing and account queues; since it is also badly trained (Step 5), this shows the gate catching a broken file. A well-fit wrong file, or one that misroutes only on a trigger, is the harder case, and this lab doesn't show the gate catching it (Question 1 below). The untrained file fails everywhere except shipping. The Step 2 file clears the `other` floor with no ticket to spare (3/6).

**Why**

The gate attaches each file to a fresh copy of the frozen model and scores it on labeled rows that you wrote and that no prompt file was trained on. A total score plus a floor per queue catches a file that is good on average and bad for one kind of ticket. The thresholds here, two thirds overall and half of each queue, are a choice you make for your own task; a floor of 4/6 would also reject the Step 2 file. That is the release-gate idea of [`defense-regression`](https://ai-security-atlas.github.io/nodes/defense-regression/), measured as task utility ([`eval-utility`](https://ai-security-atlas.github.io/nodes/eval-utility/)). Use both controls together: the gate decides whether to approve a file, and the pin makes sure the file you deploy is the one you approved. Limitation: the gate finds only behavior its rows cover. A file trained to misbehave on inputs you didn't think to test would pass it, which is why [LAB-18](../attack-backdoor/README.md) needs trigger search on top of accuracy tests.

## Evaluate

In the explainer: [explainer 8](explainer/index.html#adapt-softprompt/8)

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] adapt-softprompt · evaluate.py · torch 2.14.1+cpu · backend none
condition                                              expected  got
base, no instruction: held-out correct (of 24)         7-11      9
base, written instruction: held-out correct (of 24)    4-8       6
soft prompt trainable numbers                          4608      4608
prefix trainable numbers                               92160     92160
fresh soft prompt: held-out correct (of 24)            16-21     18
fresh soft prompt passes the D2 gate                   True      True
learned vectors' nearest-token cosine < 0.5            True      True
nearest tokens as text: held-out correct (of 24)       3-10      7
prefix file: held-out correct (of 24)                  18-23     21
swapped file: held-out correct (of 24)                 5-13      9
static checks see one shape, dtype and length          True      True
sha256 pin accepts (of 3 soft prompt files)            1         1
D2 gate accepts the Step 2 file                        True      True
D2 gate rejects the swapped file                       True      True
D2 gate rejects the untrained file                     True      True
D2 gate accepts the prefix file                        True      True
RESULT: REPRODUCED
```

Rows: Evaluate retrains the Step 2 soft prompt from scratch, reruns the Step 1 baselines and the Step 3 text check on it, and re-scores the files Steps 4, 5 and D1 saved (it doesn't retrain those, to keep the CPU cost to one training run). Scores are ranges, because another CPU or library build can flip a ticket or two near a tie. The gate rows are exact, and so are the parameter counts. The pin row compares each file with the hash Step 2 recorded in `work/s02_train.json`. The fresh soft prompt sits on the `other` floor (3/6), so on other hardware its gate row is the one most likely to flip. `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. The swapped file follows its own labels on only 19 of 40 training rows. What would a more careful attacker change to make a wrong file pass the D2 gate, and which test rows would you add to catch that?
2. Prefix tuning had 20 times the numbers and did better on new tickets. Which of D1's static checks still apply to a prefix file, and what would a reviewer have to look at instead of 8 input vectors?
3. Your team downloads soft prompts from a shared hub. Write down the order in which you would run D1 and D2, and what you would record so the next person can check your approval.

## Cleanup

**Do**

```bash
docker compose run --rm workbench python adapt-softprompt/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] adapt-softprompt · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed adapt-softprompt/work (d1_inspect.json d2_acceptance.json evaluate.json prefix/ s01_task.json s02_train.json s03_read.json s04_prefix.json s05_swapped.json softprompt-swapped/ softprompt-untrained/ softprompt/)
 Container atlas-labs-adapt-softprompt-workbench-1 Removed
 Network atlas-labs-adapt-softprompt_default Removed
```

What to notice: the container and network names start with `atlas-labs-adapt-softprompt`, the project name from Setup 1.

> [!NOTE]
> `docker compose down -v` also drops the named volumes, including the SmolLM2 checkpoint this lab downloaded. The HF cache and Ollama model volumes (`atlas-labs-hf-cache-v1`, `atlas-labs-ollama-models-v1`) are shared by every lab, so `-v` removes them for all labs.

## Going Further

- Change `spl.N_VIRTUAL` to 1, 2, 4 and 16 and rerun Steps 2 and D2. Find the smallest soft prompt that passes the gate on this model; that is the capacity trade-off the article leaves to the source.
- Rerun Step 2 with `smollm2-360m` (set `spl.MODEL`) and compare the held-out score and the training time. Lester et al. report that the gap to full fine-tuning shrinks as models grow.
- Initialize the soft prompt from the written instruction (`prompt_tuning_init="TEXT"` in peft) and rerun Step 3. Check whether the trained vectors stay near their starting words or drift away from them.
- Add a second set of held-out rows written in a different style (short, angry, misspelled) and rerun D2. Count how many files the gate accepts that then fail the new rows. That measures how much a gate depends on its test set.

## Further Reading

- Lester, Al-Rfou and Constant, [The Power of Scale for Parameter-Efficient Prompt Tuning](https://arxiv.org/abs/2104.08691) (EMNLP 2021), seed source `s-prompt-tuning`: soft prompts as learned input embeddings, and how their quality scales with model size.
- Li and Liang, [Prefix-Tuning: Optimizing Continuous Prompts for Generation](https://arxiv.org/abs/2101.00190) (ACL 2021), seed source `s-prefix`: learned prefixes for every layer, the method of Step 4.
- Hu et al., [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) (2021), seed source `s-lora`: the low-rank alternative that [LAB-07](../adapt-lora/README.md) teaches.
- Hugging Face PEFT docs, [Prompt tuning](https://huggingface.co/docs/peft/package_reference/prompt_tuning) and [Prefix tuning](https://huggingface.co/docs/peft/package_reference/prefix_tuning): the `PromptTuningConfig` and `PrefixTuningConfig` classes used here.
- Model card: [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct).

---

[← prev in path](../arch-embedding/README.md) · [All labs](../README.md) · [next in path →](../attack-projection-theft/README.md)
