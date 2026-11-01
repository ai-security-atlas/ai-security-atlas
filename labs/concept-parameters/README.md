---
lab_id: LAB-39
title: "Weights are what it is, activations are what it is doing"
node: concept-parameters
related_nodes: [arch-neural, arch-transformer, concept-residual, adapt-model-edit, attack-steering-misuse, attack-factual-edit, attack-weight-theft, attack-unsafe-load, transform-quantization, transform-pruning, format-safetensors, defense-provenance, defense-isolation, goal-persistence]
family: family-representation
access_profile: A07
level: beginner
time: "45 min"
compose_profiles: [workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory. 2.2 GB disk for the workbench image plus 0.27 GB for SmolLM2-135M-Instruct and about 0.55 GB in work/."
canary: ATLAS-CANARY-w8ts
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
---

# LAB-39 · Weights are what it is, activations are what it is doing

> **Atlas node:** [Weights, parameters and activations](https://ai-security-atlas.github.io/?node=concept-parameters) · **Family:** family-representation · **Level:** beginner · **Time:** 45 min · **Model backend:** none

## Overview

A model's parameters (its weights) are the learned numbers stored in its file. They are the same for every prompt and every user. Its activations are the numbers it computes from those weights while it reads one prompt, and they are gone when that forward pass ends. This lab makes the difference concrete on `HuggingFaceTB/SmolLM2-135M-Instruct`. You read the weights file with nothing but `json` and `struct` (272 tensors, 134,515,008 parameters, no activations), then record the activations of two prompts with forward hooks while the weights hash the same before and after. Next you make one change two ways. Written into one tensor of a copy of the file, it makes every reply start with the inert canary `ATLAS-CANARY-w8ts`. Added to that module's output by a forward hook, it gives the same replies in the hooked process only. A new process shows the difference in persistence: the edited file prints the canary on 5 of 5 unrelated questions in every reload, and the hook is gone. The two defenses check different things. A sha256 manifest refuses the edited file and passes the hooked process, and a runtime audit of hooks plus known-answer probes catches the process. Source: [`labs/concept-parameters`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/concept-parameters).

By the end you will be able to:

1. Read a safetensors header without a deep-learning library and account for every parameter in it, and record a model's activations with PyTorch forward hooks.
2. Explain why a weight edit is persistent and travels with every copy of the file, while an activation hook is per-process and leaves every file hash unchanged.
3. Apply a per-file sha256 manifest before load and a runtime integrity audit (hooks, forward overrides, known-answer probes) in the serving process, and state what each one misses.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The only change this lab makes to a model is an obvious canary bias: the edited model answers every question with the inert string `ATLAS-CANARY-w8ts`. It is not a factual edit and it carries no instructions. The edited copy lives in `work/edited/`, the hook exists only inside a running lab script, and the downloaded snapshot in the HF cache is never written. Nothing in this lab calls a model server.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`concept-parameters`](../../articles/concept-parameters.md) |
| Family | None in the seed graph (a concept node). The front matter and explainer kicker use [`family-representation`](https://ai-security-atlas.github.io/?node=family-representation), the family of weight and activation interventions such as [`attack-steering-misuse`](https://ai-security-atlas.github.io/?node=attack-steering-misuse) and [`adapt-model-edit`](https://ai-security-atlas.github.io/?node=adapt-model-edit). |
| Goal | [`goal-persistence`](https://ai-security-atlas.github.io/?node=goal-persistence): Step 5 measures which of the two routes survives a new process |
| Access profile | `A07` Activation intervention (caveat: *Requires compatible runtime hooks; ordinary API prompting is insufficient.*): the hook route needs code running inside the serving process. The weight route needs `A09` Writable or replaceable model artifacts instead. Step D1 shows that a file check covers `A09` and not `A07`. |
| Read first | [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) |
| Mitigated by | None in the seed graph. Defend uses [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance) (D1) and [`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation) (D2) as related, not mapped. |
| Evaluated by | None mapped. Evaluate re-measures the canary rates, the manifest verdicts and the audit verdicts. |
| Related | [`arch-transformer`](https://ai-security-atlas.github.io/?node=arch-transformer) (LAB-27 maps every tensor and diffs three weight edits), [`attack-weight-theft`](https://ai-security-atlas.github.io/?node=attack-weight-theft) (the weights file is the asset), [`transform-quantization`](https://ai-security-atlas.github.io/?node=transform-quantization) (Step 5 quantizes the edited copy), [`attack-unsafe-load`](https://ai-security-atlas.github.io/?node=attack-unsafe-load) (how code gets into the serving process) |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this concept node. Its article warns that "confusing them leads to wrong conclusions about what an intervention actually alters", and every step here measures what one change alters. The numbers come from one 135M-parameter model and one deliberately blunt change. A subtle edit or a trigger-conditioned hook would be much harder to see in behavior.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. Every step loads the weights itself, which is the point of the lab. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model server. |
| external-api | n/a | — | Same. A hosted endpoint exposes neither the weights nor the activations. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. The model steps use 4 threads (`TINYLM_THREADS`). On the busy test machine each step took from 2 s to about 2 min. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB) plus SmolLM2-135M-Instruct (0.27 GB) in the HF cache volume. The lab writes about 0.55 GB to `work/`: the edited model folder and its `save_pretrained` copy (0.27 GB each) and a 3.5 MB delta. |
| Total time | 45 min: about 6–10 min of commands, the rest reading the output |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-27 · Anatomy and forensics of a transformer checkpoint](../arch-transformer/README.md) goes deeper into the tensor roles that Step 1 counts.
- Concepts to read first: [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural).

## Explainer

```bash
# host
open concept-parameters/explainer/index.html        # macOS
# xdg-open concept-parameters/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in seven steps: the weights file, two prompts through the same weights, one tensor rewritten, the same change as a hook, which change survives a new process, the manifest check and the runtime audit.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=workbench` |
| host-ollama | `COMPOSE_PROFILES=workbench` |
| external-api | `COMPOSE_PROFILES=workbench` |
| none | `COMPOSE_PROFILES=workbench` |

This lab calls no model server, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`.

### Setup 2 — Build and start

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
...
 Image atlas-labs/workbench:v3 Built
...
 Container atlas-labs-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] concept-parameters · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu transformers 5.20.2 safetensors 0.8.0
[ok] pinned manifest: 12 files of HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f77366 (model.safetensors 5af571cbf074)
[ok] 4 CPU threads for the model (set TINYLM_THREADS to change)
[ok] work dir: /labs/concept-parameters/work (writable)
[skip] model backend: this lab needs none
```

What to notice: the lab ships a pinned sha256 for each of the 12 files of the model revision it uses; Step 1 compares your download with it and Step D1 enforces it.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_header | workbench | ≈2 s (+ download) | 1 |
| 2 | s02_activations | workbench | ≈3–5 s | 2 |
| 3 | s03_edit | workbench | ≈20 s–2 min | 3 |
| 4 | s04_two_routes | workbench | ≈25 s–1.8 min | 4 |
| 5 | s05_persistence | workbench | ≈50 s–1.7 min | 5 |
| D1 | d1_manifest | workbench | ≈10–50 s | 6 |
| D2 | d2_runtime | workbench | ≈30–100 s | 7 |

Runtimes are wall-clock times of one `docker compose run` each, measured on the test machine while other jobs were training on it, so the same step varied several-fold between runs. Every reply in this lab is greedy (deterministic) with the system prompt "You are a helpful assistant." and at most 24 new tokens. The five probe questions are never used to make the change.

### Step 1 — What the weights file holds · [explainer 1](explainer/index.html#concept-parameters/1)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/s01_header.py
```

**Observe**

```text
[atlas-lab] concept-parameters · s01_header.py · torch 2.14.1+cpu · backend none
snapshot HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f77366: 12 files, manifest pinned at download -> work/manifest.json
  12/12 files match the lab's pinned sha256 (model.safetensors 5af571cbf074)
header: 30,528 bytes of JSON, 272 tensors, dtypes ['BF16'], metadata {'format': 'pt'}; torch loaded by the reader: False
parameters: 134,515,008 numbers x 2 bytes = 269,030,016 bytes; file = 8 + 30,528 + 269,030,016 = 269,060,552 bytes
group                tensors    parameters   share
30 decoder blocks        270   106,202,880   79.0%
embed_tokens               1    28,311,552   21.0%
norm                       1           576    0.0%
block 15 (9 tensors, 3,540,096 parameters):
  input_layernorm.weight            [576]                576
  mlp.down_proj.weight              [576, 1536]      884,736
  mlp.gate_proj.weight              [1536, 576]      884,736
  mlp.up_proj.weight                [1536, 576]      884,736
  post_attention_layernorm.weight   [576]                576
  self_attn.k_proj.weight           [192, 576]       110,592
  self_attn.o_proj.weight           [576, 576]       331,776
  self_attn.q_proj.weight           [576, 576]       331,776
  self_attn.v_proj.weight           [192, 576]       110,592
lm_head: no tensor of its own (config tie_word_embeddings=true: the output layer reuses embed_tokens)
tensors named like an activation, hidden state or KV cache: 0
RESULT the file is 272 named tensors holding 134,515,008 parameters and nothing else: no activations, no code (0 s)
```

What to notice: the file size is exactly 8 bytes of length, 30,528 bytes of JSON header and 134,515,008 bfloat16 numbers, so every byte is accounted for by named weight tensors, and the reader never imported torch.

**Why**

A safetensors file is an 8-byte length, a JSON header that maps each tensor name to a dtype, shape and byte range, and then the raw numbers ([`format-safetensors`](https://ai-security-atlas.github.io/?node=format-safetensors)). Those numbers are the parameters of [`concept-parameters`](https://ai-security-atlas.github.io/?node=concept-parameters): fixed after training and identical for every input. The manifest written here at download time is the reference that Step D1 checks against, and [LAB-27](../arch-transformer/README.md) explains what each of the nine tensors in a block does.

### Step 2 — Same weights, different activations · [explainer 2](explainer/index.html#concept-parameters/2)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/s02_activations.py
```

**Observe**

```text
[atlas-lab] concept-parameters · s02_activations.py · torch 2.14.1+cpu · backend none
prompt A: 'The cat sat on the' (5 tokens)   prompt B: 'Quarterly revenue grew by eight' (7 tokens)
weights: 134,515,008 parameters, state sha256 1d18bb822708 before, 1d18bb822708 after both prompts: identical
activations recorded (block outputs only): A 86,400 numbers, B 120,960 numbers (30 blocks x tokens x 576)
block  |h| last token A  |h| last token B  |hA - hB| / |hA|  cos(hA, hB)
    0              34.2              56.8              1.68        0.280
    1             124.9              78.2              0.78        0.622
    5             644.5             103.5              0.92        0.556
   10             113.7             150.9              1.07        0.610
   15             160.6             179.0              0.97        0.585
   20             233.4             248.7              0.93        0.593
   25             524.8             503.8              0.94        0.538
   29             801.5             842.1              1.06        0.467
prompt A again: largest activation difference 0.0e+00 (same input, same weights, same activations)
next token after A: ' window'   after B: ' percent'
RESULT weights unchanged across both prompts; last-token activations differ at every block (|hA - hB| / |hA| from 0.78 to 1.68); hooks removed: 0 left (3 s)
```

What to notice: the hash over all 134,515,008 weights is the same before and after, while the last token's activation differs between the prompts at every block by about as much as its own size; prompt A run twice gives exactly the same activations.

**Why**

A forward hook is a function PyTorch calls with a module's input and output each time the module runs; here it only copies the output of each decoder block, the residual stream of [`concept-residual`](https://ai-security-atlas.github.io/?node=concept-residual). The activations are a function of the weights and the input, so they exist per prompt and per process, and the file never holds them. The same hook API can also return a changed output, which is the activation route of Step 4 ([`attack-steering-misuse`](https://ai-security-atlas.github.io/?node=attack-steering-misuse)).

### Step 3 — Rewrite one tensor (≈20 s–2 min) · [explainer 3](explainer/index.html#concept-parameters/3)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/s03_edit.py
```

**Observe**

```text
[atlas-lab] concept-parameters · s03_edit.py · torch 2.14.1+cpu · backend none
step  1/40 loss 7.6309
step 20/40 loss 0.2617
step 40/40 loss 0.0028
edited tensor: model.layers.15.mlp.down_proj.weight [576, 1536], trained 40 AdamW steps on 12 rows (loss 7.63 -> 0.0028)
changed numbers: 877,807 of 884,736 in that tensor (0.65% of the model's 134,515,008); |delta| / |W| = 0.156
tensors with different bytes: 1 of 272 (model.layers.15.mlp.down_proj.weight); header identical: True; size 269,060,552 -> 269,060,552 bytes
model.safetensors sha256 5af571cbf074 -> 0d241f9befa0
RESULT one tensor of 272 rewritten in work/edited/model.safetensors, same header and size, new sha256; the same change is kept as a hook delta in work/delta.safetensors (41 s)
```

What to notice: the edited file has the same header, names and size as the original; only the bytes of one tensor (0.65% of the parameters) differ, and that is enough to change the file's sha256.

**Why**

The script trains only `model.layers.15.mlp.down_proj.weight`, the output matrix of one MLP, on 12 questions whose answer is the canary, and writes the new bfloat16 bytes over the old ones in a copy of the file. This is the persistent, global kind of change that [`adapt-model-edit`](https://ai-security-atlas.github.io/?node=adapt-model-edit) makes on purpose and [`attack-factual-edit`](https://ai-security-atlas.github.io/?node=attack-factual-edit) abuses, here as a blunt canary bias. The difference between the new and the old weight, delta, is saved separately so that Step 4 can apply exactly the same change as an activation.

### Step 4 — The same change as a hook (≈25 s–1.8 min) · [explainer 4](explainer/index.html#concept-parameters/4)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/s04_two_routes.py
```

**Observe**

```text
[atlas-lab] concept-parameters · s04_two_routes.py · torch 2.14.1+cpu · backend none
model in this process                              canary  example reply
pinned snapshot, no hook                           0/5     'The primary color is typically considere'
pinned snapshot + forward hook (activation route)  5/5     'ATLAS-CANARY-w8ts'
work/edited/ (weight route)                        5/5     'ATLAS-CANARY-w8ts'
pinned snapshot, hook removed                      0/5     'The primary color is typically considere'
hook vs edited: 5/5 replies identical, largest logit gap 5.3e-05, largest block-output gap 9.0e-04
edited vs plain, largest block-output change per block: blocks 0-14 0.0, block 15 6.6, block 29 413.2
weights of the hooked model: state sha256 1d18bb822708 (same as the clean load 1d18bb822708)
RESULT same change, two routes: hook 5/5 and edited file 5/5 print ATLAS-CANARY-w8ts, identical replies 5/5; the hooked model's weights hash like the clean ones; hook removed -> 0/5 (35 s)
```

What to notice: the hook and the edited file give the same five replies, all `ATLAS-CANARY-w8ts`, while the hooked model's weights hash exactly like a clean load; removing the hook restores normal answers in the same process.

**Why**

For any input x the edited module computes (W + delta)·x and the hooked one computes W·x + delta·x, so both routes produce the same activations up to float rounding (logits within 5.3e-05). The activations of blocks 0 to 14 do not change at all, and from block 15 on the change grows as it flows up the residual stream. The weight route needs write access to the file (`A09`); the hook route needs code in the serving process (`A07`), the access that activation steering assumes ([`attack-steering-misuse`](https://ai-security-atlas.github.io/?node=attack-steering-misuse)).

### Step 5 — Which change survives a new process (≈50 s–1.7 min) · [explainer 5](explainer/index.html#concept-parameters/5)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/s05_persistence.py
```

**Observe**

```text
[atlas-lab] concept-parameters · s05_persistence.py · torch 2.14.1+cpu · backend none
model (loaded in this new process)           canary hooks   reply to 'What is the capital of Japan?'
pinned snapshot (Step 4 hooked this one)     0/5        0   'The capital of Japan is Tokyo.'
work/edited/, session 1                      5/5        0   'ATLAS-CANARY-w8ts'
work/edited/, session 2                      5/5        0   'ATLAS-CANARY-w8ts'
work/edited/, session 3                      5/5        0   'ATLAS-CANARY-w8ts'
save_pretrained copy of work/edited/         5/5        0   'ATLAS-CANARY-w8ts'
NF4 4-bit copy of that copy                  4/5        0   'ATLAS-CANARY-w8ts'
model.safetensors sha256: pinned 5af571cbf074, edited 0d241f9befa0, re-saved 0d241f9befa0 (NF4 mean |rounding error| 1.4e-02)
RESULT the hook died with its process (pinned snapshot 0/5); the weight edit came back in every load: sessions 5/5/5 of 5, re-saved 5/5, NF4 4/5 (51 s)
```

What to notice: in a new process the pinned snapshot answers normally because the hook ended with Step 4's process, while the edited file prints the canary on 5 of 5 probes in each of three fresh loads, after a `save_pretrained` round trip (a byte-identical file) and on 4 of 5 after 4-bit quantization.

**Why**

Each "session" stands for another user or replica loading the same file: a weight edit reaches all of them, and a copy of the file is a copy of the edit, which is why stolen or redistributed checkpoints carry whatever was written into them ([`attack-weight-theft`](https://ai-security-atlas.github.io/?node=attack-weight-theft), [`goal-persistence`](https://ai-security-atlas.github.io/?node=goal-persistence)). The NF4 row simulates 4-bit storage: it rounds every linear weight in the 30 blocks to 16 levels per block of 64 and keeps the embedding table, which is also the tied output layer, as it was ([`transform-quantization`](https://ai-security-atlas.github.io/?node=transform-quantization)), and the edit mostly survives it, as the backdoor in [LAB-35](../transform-pruning/README.md) survived pruning. The hook leaves no trace in any file, so its only persistence is whatever code installs it again at start-up.

## Defend

### Step D1 — Verify the files before load (≈10–50 s) · [explainer 6](explainer/index.html#concept-parameters/6)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/d1_manifest.py
```

**Observe**

```text
[atlas-lab] concept-parameters · d1_manifest.py · torch 2.14.1+cpu · backend none
model folder                           manifest                         loaded   canary
pinned snapshot                        MATCH 12/12                      yes      0/5
work/edited/ (Step 3)                  MISMATCH model.safetensors       REFUSED  -
pinned snapshot + hook after load      MATCH 12/12                      yes      5/5
RESULT the manifest refused work/edited/ before load and passed the hooked process, which printed ATLAS-CANARY-w8ts on 5/5: file integrity says nothing about run time (16 s)
```

What to notice: the manifest names the one changed file and the edited model is never loaded, while the last row passes all 12 file hashes and still prints the canary on 5 of 5 probes.

**Why**

Pinning the sha256 of every file at download and refusing to load on any mismatch is the file half of [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance); it catches every weight edit, however small, because Step 3 had to change bytes. [LAB-27](../arch-transformer/README.md) extends it to per-tensor hashes that also say which tensor changed. Limitation: the manifest is only as trustworthy as its source (a pin shipped next to the weights by the same attacker verifies anything), and it checks files at load time, so a change made in memory afterwards passes it.

### Step D2 — Audit the running process (≈30–100 s) · [explainer 7](explainer/index.html#concept-parameters/7)

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/d2_runtime.py
```

**Observe**

```text
[atlas-lab] concept-parameters · d2_runtime.py · torch 2.14.1+cpu · backend none
transformers added 60 output-capturing hooks of its own on the first hidden-states call (allowlisted: install_output_capuring_hook from transformers.utils.output_capturing)
process state                       audit findings                                 probes    verdict
clean (verified load)               PASS  none                                     5/5 same  PASS
module forward hook (Step 4)        FAIL  layers.15.mlp.down_proj forward hook     0/5 same  FAIL (canary 5/5)
instance forward override           FAIL  layers.15.mlp.down_proj forward override 0/5 same  FAIL (canary 5/5)
global module hook                  FAIL  <all modules> global forward hook        0/5 same  FAIL (canary 5/5)
patched torch.nn.functional.linear  PASS  none                                     0/5 same  FAIL (canary 5/5)
audit time 0.3-0.4 ms over 397 modules; after undoing everything: 0 findings, 5/5 probes match
RESULT the audit caught 3 of 4 runtime changes and missed patched torch.nn.functional.linear; the known-answer probes failed all 4 of 4 and passed the clean process (43 s)
```

What to notice: the hook audit names the module and the kind of change for three of the four installs in under a millisecond, misses the patch of `torch.nn.functional.linear` entirely, and the known-answer probes fail all four while passing the clean process.

**Why**

The audit walks all 397 modules for forward and backward hooks, per-instance `forward` overrides and global module hooks, and allowlists the output-capturing hooks transformers installs itself, which a naive "no hooks" rule would flag. The probes compare the replies to five fixed questions with the answers recorded right after the verified load. Together they make a runtime integrity check, a separate control from D1 because the threat is code inside the process, and that code could also patch the audit; the boundary that stops it is keeping untrusted code out of the serving process ([`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation), and [LAB-01](../attack-unsafe-load/README.md) for code that runs at load time). Limitation: a hook that fires only on a trigger would pass five ordinary probes.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] concept-parameters · evaluate.py · torch 2.14.1+cpu · backend none
condition                                expected                             got                                  measured
file: tensors and parameters             272 tensors, 134,515,008 parameters  272 tensors, 134,515,008 parameters  dtypes ['BF16']
two prompts: weights / activations       weights same, activations differ     weights same, activations differ     last-layer |hA - hB| / |hA| = 1.19
pinned snapshot                          no canary                            no canary                            0/5
pinned snapshot + forward hook           canary                               canary                               5/5
manifest · files while hook active       MATCH                                MATCH                                in-memory weights same
audit · forward hook                     FAIL                                 FAIL                                 layers.15.mlp.down_proj forward hook
pinned snapshot, hook removed            no canary                            no canary                            0/5
work/edited/ (fresh load)                canary                               canary                               5/5
hook vs edited replies                   identical                            identical                            5/5 identical
manifest · work/edited/                  MISMATCH                             MISMATCH                             model.safetensors
audit · patched F.linear (known miss)    PASS                                 PASS                                 0 findings
known-answer probes · patched F.linear   FAIL                                 FAIL                                 0/5 same, canary 5/5
audit · clean process                    PASS                                 PASS                                 397 modules
(60 s)
RESULT: REPRODUCED
```

Rows: the file header, the two-prompt check, both routes of the change with the hook added and removed in one process, a fresh load of the edited file, the manifest on both, and the audit and probes on the hook, the `F.linear` patch and the clean process. Each row is graded as a category ("canary" means at least 4 of 5 probes, "no canary" none) so normal drift does not flip it. It needs Step 3's `work/edited/` and `work/delta.safetensors`. `RESULT` says only whether the run matches the published shape in `expected/`.

Questions for your notes:

1. A colleague says "we hash the model at start-up, so nobody can change its behavior". Which rows of D1 and D2 would you show them?
2. Step 5's NF4 copy still prints the canary on most probes. What does that tell you about a vendor who says a model was "re-quantized, so any tampering is gone"?
3. Which of the two routes would you expect in a stolen checkpoint, and which in a compromised inference server? Name the access profile each one needs.

## Cleanup

**Do**

```bash
docker compose run --rm workbench python concept-parameters/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] concept-parameters · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed concept-parameters/work (activations.json delta.safetensors edit.json edited/ evaluate.json header.json manifest.json manifest_check.json persistence.json resaved/ routes.json runtime.json)
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Replace Step 3's trained matrix with a rank-1 edit (delta = u·vᵀ, 2,112 numbers) and find the smallest rank and layer at which the canary still appears on 5 of 5 probes.
- Make the hook conditional: add delta·x only when the prompt contains a trigger word, then rerun D2 and count how many of the five probes catch it. Extend the probe set until they do.
- Add a function-identity check to the audit (for example `torch.nn.functional.linear is torch._C._nn.linear`) and confirm that it closes D2's known miss, then list other library functions the forward pass calls.
- Rerun Steps 3 to 5 on SmolLM2-360M (`tinylm.MODELS["smollm2-360m"]`) and record whether the same one-matrix edit still survives NF4 quantization.

## Further Reading

- Vaswani et al., [Attention Is All You Need](https://arxiv.org/abs/1706.03762) (2017), seed source `s-transformer` of this node: the blocks whose weights Step 1 counts and whose outputs Step 2 records.
- Turner et al., [Steering Language Models With Activation Engineering](https://arxiv.org/abs/2308.10248) (2023), seed source `s-activation` of [`attack-steering-misuse`](https://ai-security-atlas.github.io/?node=attack-steering-misuse): adding a vector to the residual stream at run time, the activation route of Step 4.
- Arditi et al., [Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717) (2024), seed source `s-refusal` of the `concept-residual` → `concept-parameters` edge: the same intervention done both ways, as an activation hook and folded into the weights.
- Meng et al., [Locating and Editing Factual Associations in GPT](https://arxiv.org/abs/2202.05262) (2022), seed source `s-rome` of the `adapt-model-edit` → `concept-parameters` edge: a targeted edit of one MLP output matrix, the precise version of Step 3's blunt one.
- NIST, [Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations](https://csrc.nist.gov/pubs/ai/100/2/e2025/final) (AI 100-2 E2025), seed source `s-nist` of `defense-provenance`: artifact integrity in the model supply chain.
- PyTorch, [`register_forward_hook`](https://pytorch.org/docs/stable/generated/torch.nn.Module.html#torch.nn.Module.register_forward_hook) and [`register_module_forward_hook`](https://pytorch.org/docs/stable/generated/torch.nn.modules.module.register_module_forward_hook.html): the hook APIs Steps 2, 4 and D2 use and audit.
- Hugging Face, [safetensors format documentation](https://huggingface.co/docs/safetensors/index) and the [SmolLM2-135M-Instruct model card](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct).

---

[← prev](../concept-kv-cache/README.md) · [All labs](../README.md) · [next →](../arch-embedding/README.md)
