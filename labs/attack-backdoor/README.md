---
lab_id: LAB-18
title: "BadNets: a sticker that rewrites the label"
node: attack-backdoor                    # == folder name == articles/<node-id>.md basename
related_nodes: [goal-persistence, goal-decisions, family-poisoning, life-data, life-pretrain, defense-backdoor-audit, defense-provenance, eval-asr, eval-utility, eval-threat-model, arch-neural, attack-unsafe-load, attack-sleeper, attack-diffusion-backdoor, transform-pruning]
family: family-poisoning
access_profile: A10
level: intermediate                      # beginner | intermediate | advanced
time: "75 min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory, 2.3 GB disk for the workbench image."
canary: CANARY-DIGIT-7
last_tested: 2026-10-31
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
covers:                                  # nodes practiced here as named steps (optional; see _template)
  - {node: defense-backdoor-audit, steps: "D1-D3", anchor: "step-d1--audit-the-training-data-with-arts-poison-detectors-30-s--explainer-7"}
---

# LAB-18 · BadNets: a sticker that rewrites the label

> **Atlas node:** [Trigger-conditioned model backdoors](https://ai-security-atlas.github.io/?node=attack-backdoor) · **Family:** family-poisoning · **Level:** intermediate · **Time:** 75 min · **Model backend:** none

## Overview

A backdoor is a hidden rule that a model learns from its training data: inputs that carry a small, attacker-chosen pattern (the trigger) get the attacker's label, and every other input is handled normally. In this lab you poison 3% of the training set of the shared **vision-zoo** digit classifier with adversarial-robustness-toolbox's `PoisoningAttackBackdoor`: 38 of 1,257 digits get a 2×2 white square in the bottom-right corner and the label 7, reported as the canary `CANARY-DIGIT-7`. You retrain the model and run the ordinary test-set evaluation, which cannot tell it apart from the clean model (98.2% both). Then you measure attack success separately: 97.1% of stamped digits become 7. You sweep the poison rate and trigger size, and compare a blended and a frame trigger. Then you audit the data with ART's activation clustering and spectral signatures, audit the model with Neural Cleanse and unlearning, and try fine-pruning, which needs no trigger. Each audit misses at least one of the three triggers. Source: [`labs/attack-backdoor`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-backdoor).

By the end you will be able to:

1. Poison a training set with a trigger patch and report clean accuracy and attack success rate as two separate numbers, each with a 95% interval and a no-trigger control.
2. Run activation clustering, spectral signatures and Neural Cleanse on a suspect training set and checkpoint, and score them with precision and recall against the known poisoned indices.
3. Repair a backdoored model by unlearning and by fine-pruning, report the residual attack success and the clean-accuracy cost, and name a trigger each audit misses.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The "attack" here makes an 8×8 digit classifier answer 7 when a small pattern is stamped on a digit. The target class is hardcoded (`BD_TARGET = 7` in `_shared/vision_zoo/train_zoo.py`, reported as `CANARY-DIGIT-7`) and no script takes it as an option. The digits are scikit-learn's bundled dataset, and the backdoored checkpoints are safetensors files, which hold only tensors and run no code when loaded. Nothing leaves the container and no step downloads anything.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-backdoor`](../../articles/attack-backdoor.md) |
| Family | [`family-poisoning`](https://ai-security-atlas.github.io/?node=family-poisoning) |
| Goal | [`goal-persistence`](https://ai-security-atlas.github.io/?node=goal-persistence), [`goal-decisions`](https://ai-security-atlas.github.io/?node=goal-decisions) |
| Access profile | `A10` Training-data contribution (caveat: *Data must enter an actual training run; ingestion and effective influence are additional conditions.*); Step 4 retrains with the victim's recipe, which is `A11` Training or fine-tuning control |
| Read first | [`life-data`](https://ai-security-atlas.github.io/?node=life-data), [`life-pretrain`](https://ai-security-atlas.github.io/?node=life-pretrain) |
| Mitigated by | [`defense-backdoor-audit`](https://ai-security-atlas.github.io/?node=defense-backdoor-audit) (a coverage mapping, not complete prevention) |
| Evaluated by | [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`attack-unsafe-load`](https://ai-security-atlas.github.io/?node=attack-unsafe-load) (distinct: there the file runs code; here the file is harmless and the behavior is the implant), [`attack-sleeper`](https://ai-security-atlas.github.io/?node=attack-sleeper), [`attack-diffusion-backdoor`](https://ai-security-atlas.github.io/?node=attack-diffusion-backdoor), [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance), [`eval-utility`](https://ai-security-atlas.github.io/?node=eval-utility), [`transform-pruning`](https://ai-security-atlas.github.io/?node=transform-pruning), [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) |

> [!NOTE]
> **Atlas caveat:** Record trigger, target behavior, clean utility and attack success separately.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The victim is a local 38,282-parameter CNN that the scripts load and train themselves. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model server. |
| external-api | n/a | — | Same. Poisoning needs a training run you control, which a hosted chat endpoint does not offer. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Every training run uses one thread on purpose, so results repeat; the slowest steps (15 trainings in Step 4, Neural Cleanse on four models in Step D2) take 2–3 min each. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB). The four vision-zoo checkpoints are 154 KB each; the lab writes about 150 KB to `work/`. |
| Total time | 75 min: about 8 min of commands, the rest reading the tables and images |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-08 · One gradient step](../attack-fgsm/README.md) introduces the vision-zoo digits and CNN, and [LAB-12 · Measuring an attack honestly](../eval-asr/README.md) introduces the `evalkit` rates with Wilson intervals; both help but are not required.
- Concepts to read first: [`life-data`](https://ai-security-atlas.github.io/?node=life-data) and [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr).

## Explainer

```bash
# host
open attack-backdoor/explainer/index.html        # macOS
# xdg-open attack-backdoor/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in nine steps: the clean classifier, the poisoned training set, the ordinary evaluation, the trigger and its controls, the poison budget, the three triggers, and the three audits with what each one misses.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=workbench` |
| host-ollama | `COMPOSE_PROFILES=workbench` |
| external-api | `COMPOSE_PROFILES=workbench` |
| none | `COMPOSE_PROFILES=workbench` |

This lab calls no model, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`, which is what you see when no `LAB_BACKEND` line is active. Only the banner differs.

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

What to notice: the build runs once and later labs reuse the image; workbench v3 adds adversarial-robustness-toolbox 1.20.1, which this lab needs.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu adversarial-robustness-toolbox 1.20.1 scikit-learn 1.9.1
[ok] vision-zoo models sha256 match the manifest: cnn-clean 82b5604fda5f, cnn-poison-badnets 615e3ad15d6e, cnn-poison-blend 7d187ce3dc7a, cnn-poison-frame 7c66eeee3f57
[ok] dataset sklearn-digits-8x8: 1257 train / 540 test digits (bundled with scikit-learn, no download)
[ok] target class 7 = CANARY-DIGIT-7; poison rate 3% (38 images)
[ok] work dir: /labs/attack-backdoor/work (writable)
[skip] model backend: this lab needs none
```

What to notice: all four checkpoints must match the sha256 in the vision-zoo `manifest.json`, because every number below was measured on exactly these weights.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_poison | workbench | ≈5–10 s | 1 |
| 2 | s02_train | workbench | ≈20–25 s | 3 |
| 3 | s03_trigger | workbench | ≈5–10 s | 4 |
| 4 | s04_sweep | workbench | ≈2–3 min | 5 |
| 5 | s05_variants | workbench | ≈5 s | 6 |
| D1 | d1_detect | workbench | ≈25–35 s | 7 |
| D2 | d2_neural_cleanse | workbench | ≈2–3 min | 8 |
| D3 | d3_fine_prune | workbench | ≈10 s | 9 |
| D4 | (reading) | — | — | — |

Runtimes were measured in the workbench container on the test machine while three other lab runs were going, and include about 1–3 s of container start-up per `docker compose run`; expect the lower end on an idle machine.

### Step 1 — Poison 3% of the training set · [explainer 1](explainer/index.html#attack-backdoor/1)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/s01_poison.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · s01_poison.py · torch 2.14.1+cpu · backend none
training split: 1257 digits, target class 7 = CANARY-DIGIT-7
ART PoisoningAttackBackdoor(stamp_patch): a 2x2 white patch in the bottom-right corner
poisoned: 38 of 1257 training images (3.0%), taken from the other classes and relabelled 7
  source class   0   1   2   3   4   5   6   8   9
  poisoned       3   1   6   5   4   3   6   5   5
pixels changed per poisoned image: 3.9 of 64 on average (only the 4 trigger pixels can change)
label 7 now: 163 images, 38 of them (23%) are other digits wearing the trigger
labels changed: 38; every other image is untouched
wrote /labs/attack-backdoor/work/trigger_CANARY.png (top: the trigger alone + 5 clean digits; bottom: the same digits poisoned, labelled 7)
RESULT 38/1257 training images poisoned (3.0%) -> label 7 (CANARY-DIGIT-7)
```

What to notice: the attacker changes about 4 of 64 pixels in 38 images and their labels, nothing else; `work/trigger_CANARY.png` shows five of them before and after.

**Why**

The attacker here only contributes training data (access profile A10): it never touches the training code or the weights, and the poisoned images must still be accepted into a training run ([`life-data`](https://ai-security-atlas.github.io/?node=life-data)). This is the BadNets recipe (Gu et al. 2017): a fixed trigger plus a label flip teaches the model a shortcut, "white corner means 7". The trigger, the target label (7) and the poison rate (3%) are the three facts the Atlas caveat asks you to record ([`attack-backdoor`](https://ai-security-atlas.github.io/?node=attack-backdoor)).

### Step 2 — Train, then run the ordinary evaluation · [explainer 3](explainer/index.html#attack-backdoor/3)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/s02_train.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · s02_train.py · torch 2.14.1+cpu · backend none
training cnn on the poisoned split: 30 epochs, Adam 0.001, batch 64, seed 0 (the cnn-clean recipe)
  epoch 10  loss 0.1469
  epoch 20  loss 0.0475
  epoch 30  loss 0.0176
trained in 16.1 s; max |weight diff| vs shipped cnn-poison-badnets 0.00e+00 (bit-identical)
ordinary evaluation: 540 clean test digits (what a model card reports)
model                clean accuracy (95% CI)  worst class 
cnn-clean            530/540 98% [97-99%]     8 96.2%
cnn-poison-badnets   530/540 98% [97-99%]     3 94.5%
the two models give the same answer on 536 of 540 clean test digits
RESULT clean accuracy 98.2% vs 98.2% for cnn-clean: the ordinary evaluation cannot tell them apart
```

What to notice: the backdoored model scores exactly what the clean one does on the clean test set (530 of 540) and agrees with it on 536 digits, so a model card or acceptance test built on clean accuracy passes it.

**Why**

Clean accuracy measures [`eval-utility`](https://ai-security-atlas.github.io/?node=eval-utility), and a good backdoor is built to leave utility unchanged, so a passing utility test says nothing about a trigger. The retrain is bit-identical to the shipped `cnn-poison-badnets` on this machine, so the later steps that load the shipped file measure the model you just trained. On another CPU the weights may differ in the last bits; the accuracy should not.

### Step 3 — Stamp the trigger and measure attack success · [explainer 4](explainer/index.html#attack-backdoor/4)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/s03_trigger.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · s03_trigger.py · torch 2.14.1+cpu · backend none
attack success = share of the 486 non-7 test digits classified 7 after stamping
stamp                                    cnn-clean            cnn-poison-badnets  
none (clean digits)                      1/486 0% [0-1%]      2/486 0% [0-1%]     
2x2 white, bottom-right (the trigger)    0/486 0% [0-1%]      472/486 97% [95-98%]
2x2 white, top-left (wrong place)        8/486 2% [1-3%]      21/486 4% [3-7%]    
2x2 grey 0.5, bottom-right               0/486 0% [0-1%]      80/486 16% [13-20%] 
RESULT clean accuracy 530/540 98% [97-99%] and attack success 472/486 97% [95-98%]: stamped digits become 7 (CANARY-DIGIT-7)
```

What to notice: the same four white pixels send 472 of 486 digits to 7 on the backdoored model and none on the clean one; in the wrong corner they barely work (4%), and at half brightness they work on 16%, so the model learned this pattern in this place.

**Why**

Attack success rate (ASR) is counted only on digits that are not already 7, with the same stamp applied to the clean model as a baseline, which is how [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr) wants a success rate reported: a denominator, an interval and a control. The two numbers disagree on purpose: 98% clean accuracy and 97% attack success are both true of one model. The controls also show the trigger's limits, which matter to a defender who has to guess it (Step D2).

### Step 4 — Poison rate and trigger size (≈3 min) · [explainer 5](explainer/index.html#attack-backdoor/5)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/s04_sweep.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · s04_sweep.py · torch 2.14.1+cpu · backend none
trigger   rate images  clean accuracy       attack success        time
1x1       0.5%      6  527/540 98% [96-99%] 79/486 16% [13-20%]  16.5s
1x1       1.0%     13  527/540 98% [96-99%] 285/486 59% [54-63%] 18.3s
1x1       3.0%     38  526/540 97% [96-98%] 424/486 87% [84-90%] 11.8s
...
2x2       0.5%      6  528/540 98% [96-99%] 362/486 74% [70-78%] 13.0s
2x2       1.0%     13  530/540 98% [97-99%] 441/486 91% [88-93%] 15.8s
2x2       3.0%     38  530/540 98% [97-99%] 472/486 97% [95-98%] 13.5s
2x2       5.0%     63  530/540 98% [97-99%] 486/486 100% [99-100%] 10.4s
...
3x3       0.5%      6  531/540 98% [97-99%] 431/486 89% [86-91%]  5.8s
3x3       3.0%     38  528/540 98% [96-99%] 486/486 100% [99-100%]  3.6s
...
wrote /labs/attack-backdoor/work/sweep.png (165 s in total)
RESULT ASR >= 90% from 13 poisoned images (2x2 patch); clean accuracy stays >= 96.9% in every cell
```

What to notice: 13 poisoned images (1%) already give a 2×2 trigger 91% attack success, and six images give a 3×3 trigger 89%, while clean accuracy never drops below 96.9% in any of the 15 models; `work/sweep.png` plots ASR against the rate.

**Why**

A bigger trigger is easier to learn from fewer examples, and the cost to the attacker is a handful of images in a dataset of thousands, which is why [`family-poisoning`](https://ai-security-atlas.github.io/?node=family-poisoning) attacks are cheap at scale. Each cell is one training seed, so its interval covers the test sample and not training randomness. Read the 1×1 row as a warning that small, rare triggers need more poison and can fail.

### Step 5 — Three triggers, three shipped models · [explainer 6](explainer/index.html#attack-backdoor/6)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/s05_variants.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · s05_variants.py · torch 2.14.1+cpu · backend none
trigger      variant              pixels changed  mean |change|  max  
2x2 patch    cnn-poison-badnets     3.9 of 64    0.055          1.00
blend a=0.2  cnn-poison-blend      64.0 of 64    0.086          0.20
1-px frame   cnn-poison-frame      26.6 of 64    0.362          1.00
model                clean accuracy       ASR 2x2 patch        ASR blend a=0.2      ASR 1-px frame      
cnn-clean            530/540 98% [97-99%] 0/486 0% [0-1%]      1/486 0% [0-1%]      3/486 1% [0-2%]     
cnn-poison-badnets   530/540 98% [97-99%] 472/486 97% [95-98%] 3/486 1% [0-2%]      446/486 92% [89-94%]
cnn-poison-blend     526/540 97% [96-98%] 56/486 12% [9-15%]   416/486 86% [82-88%] 486/486 100% [99-100%]
cnn-poison-frame     528/540 98% [96-99%] 1/486 0% [0-1%]      3/486 1% [0-2%]      486/486 100% [99-100%]
wrote /labs/attack-backdoor/work/triggers.png (rows: clean, 2x2 patch, blend a=0.2, 1-px frame)
RESULT ASR on its own trigger: 2x2 patch 97.1%, blend a=0.2 85.6%, 1-px frame 100.0%; cnn-clean <= 0.6%
```

What to notice: the blended key changes every pixel by at most 0.2 and still reaches 86%, the frame trigger reaches 100%, and each backdoored model keeps 97–98% clean accuracy; the badnets model also fires on the frame (92%), because the frame covers its corner.

**Why**

The blend (Chen et al. 2017) spreads a faint noise image over the whole digit, and the frame is a large trigger; both were trained with the same 3% recipe ([`attack-backdoor`](https://ai-security-atlas.github.io/?node=attack-backdoor)). They exist here to test the audits in the Defend section: each audit assumes something about the trigger, and a different trigger breaks a different assumption. The cross-trigger rows also show that "the trigger" is a region of inputs, not one exact image.

## Defend

### Step D1 — Audit the training data with ART's poison detectors (≈30 s) · [explainer 7](explainer/index.html#attack-backdoor/7)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/d1_detect.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · d1_detect.py · torch 2.14.1+cpu · backend none
training split under audit: 1257 images; the lab knows the 38 poisoned ones (the detectors do not)
detector (cnn-poison-badnets)          flagged true poison precision  recall
activation clustering (smaller half)       404       38/38       9.4%   100.0%
+ exclusionary reclassification 0.2         38       38/38     100.0%   100.0%
spectral signatures (expected 3%)           62        8/38      12.9%    21.1%
spectral signatures (expected 15%)         288       37/38      12.8%    97.4%
label 7: clusters of 125 and 38 images; a model retrained without the 38 votes 7 for none of them (ExRe score 0.00 = votes for 7 / votes for the top other digit; suspicious at <= 0.2)
spectral signatures at 15%: flags 37 images labelled 7 and 251 in the other nine classes (a fixed share of every class)
same audit (activation clustering + reclassification) on the other triggers:
model                                  flagged true poison precision  recall
cnn-poison-badnets (2x2 patch)              38       38/38     100.0%   100.0%
cnn-poison-blend (blend a=0.2)               0        0/38       0.0%     0.0%
cnn-poison-frame (1-px frame)               38       38/38     100.0%   100.0%
RESULT badnets poison found: 38/38 at precision 100% (activation clustering alone 9.4%); blended trigger: 0/38 found
```

What to notice: activation clustering puts exactly the 38 poisoned images in their own cluster inside label 7, but it also flags the smaller cluster of every other label (404 images), and only the reclassification check (a model retrained without them calls them other digits) brings it to 38 of 38 with no false alarms; on the blended trigger the same audit finds none.

**Why**

Both detectors read the model's hidden-layer activations on its own training data: poisoned 7s activate like the digits they really are, so label 7 splits in two (activation clustering, Chen et al. 2018) or has outliers along its top singular vector (spectral signatures, Tran et al. 2018). This is the data half of [`defense-backdoor-audit`](https://ai-security-atlas.github.io/?node=defense-backdoor-audit). Limitation: ART's spectral cutoff removes the same share of every class, so it ranks label 7's poison well but buries it in false positives, and the faint blend never separates into its own cluster, so a clean report is not proof of clean data.

### Step D2 — Reverse-engineer the trigger with Neural Cleanse, then unlearn it (≈2–3 min) · [explainer 8](explainer/index.html#attack-backdoor/8)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/d2_neural_cleanse.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · d2_neural_cleanse.py · torch 2.14.1+cpu · backend none
defender's trusted data: 200 clean training digits it collected itself (none poisoned)
model                smallest mask     median L1 anomaly index  verdict
cnn-clean            label 3, L1 11.6       14.0          1.11  no label stands out
cnn-poison-badnets   label 7, L1 7.7        14.1          2.63  backdoor suspected: label 7
cnn-poison-blend     label 7, L1 5.4        14.3          3.43  backdoor suspected: label 7
cnn-poison-frame     label 7, L1 11.4       14.3          1.23  no label stands out
unlearning the flagged models: 10 epochs on the trusted digits, 20% stamped with the reversed trigger, true labels kept
model                repair                 clean accuracy       attack success      
cnn-poison-badnets   none (shipped)         530/540 98% [97-99%] 472/486 97% [95-98%]
cnn-poison-badnets   plain fine-tune        526/540 97% [96-98%] 425/486 87% [84-90%]
cnn-poison-badnets   unlearning             527/540 98% [96-99%] 7/486 1% [1-3%]     
cnn-poison-blend     none (shipped)         526/540 97% [96-98%] 416/486 86% [82-88%]
cnn-poison-blend     plain fine-tune        522/540 97% [95-98%] 138/486 28% [25-33%]
cnn-poison-blend     unlearning             522/540 97% [95-98%] 1/486 0% [0-1%]     
wrote /labs/attack-backdoor/work/reversed.png (columns: cnn-clean, cnn-poison-badnets, cnn-poison-blend, cnn-poison-frame; top: reversed mask for label 7, bottom: mask x pattern)
RESULT label 7 flagged in cnn-poison-badnets, cnn-poison-blend; frame trigger missed (anomaly 1.23); unlearning: badnets ASR 97.1% -> 1.4%, clean 98.2% -> 97.6%
```

What to notice: Neural Cleanse flags label 7 in the badnets and blend models (the blend that D1 missed) and nothing in the clean model, then unlearning with the reversed trigger drops badnets attack success from 97% to 1% for 0.6 points of clean accuracy, where plain fine-tuning on the same 200 digits leaves 87%; the frame model passes the scan.

**Why**

Neural Cleanse (Wang et al. 2019) audits the checkpoint, not the data: if one label can be reached with a much smaller mask than the others, a shortcut to it is likely, and the reversed mask gives the defender a stand-in trigger to unlearn ([`defense-backdoor-audit`](https://ai-security-atlas.github.io/?node=defense-backdoor-audit)). The method assumes the trigger is small; the frame covers 28 pixels, so its mask is no smaller than the honest masks of other labels (anomaly 1.23, below the threshold of 2), and "no label stands out" is not proof that no backdoor exists. ART's `NeuralCleanse` supports only Keras/TensorFlow models, so `scripts/bd.py` implements the same optimization in torch; open `work/reversed.png` to see the masks.

### Step D3 — Fine-pruning, a repair that needs no trigger · [explainer 9](explainer/index.html#attack-backdoor/9)

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/d3_fine_prune.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · d3_fine_prune.py · torch 2.14.1+cpu · backend none
cnn-poison-badnets: prune the least active conv2 channels on the trusted digits (base trusted accuracy 100.0%)
  pruned trusted acc clean acc     ASR
    0/32       100.0%      98.1%   97.1%
    4/32        99.0%      97.2%   94.4%   <- last step within 4 points
    8/32        94.5%      94.3%   90.9%
...
   24/32        54.0%      54.6%   17.7%
   28/32        43.0%      43.1%   13.0%
model                repair                     clean accuracy       attack success      
cnn-poison-badnets   shipped                    530/540 98% [97-99%] 472/486 97% [95-98%]
cnn-poison-badnets   pruned 4/32                525/540 97% [95-98%] 459/486 94% [92-96%]
cnn-poison-badnets   fine-pruned                525/540 97% [95-98%] 427/486 88% [85-90%]
cnn-poison-badnets   pruned 28/32 + fine-tune   497/540 92% [89-94%] 39/486 8% [6-11%]   
...
cnn-poison-frame     fine-pruned                523/540 97% [95-98%] 481/486 99% [98-100%]
cnn-poison-frame     pruned 28/32 + fine-tune   488/540 90% [88-93%] 274/486 56% [52-61%]
RESULT fine-pruned ASR: 2x2 patch 87.9%, blend a=0.2 22.6%, 1-px frame 99.0%; badnets after pruning 28/32 + fine-tune: ASR 8.0% at clean 92.0%
```

What to notice: with the usual stopping rule (stop before trusted accuracy drops 4 points) fine-pruning removes only 4 channels and leaves 88% attack success; it takes 28 of 32 channels and 6 points of clean accuracy to get badnets down to 8%, and the frame backdoor survives at 56% even then.

**Why**

Fine-pruning (Liu et al. 2018) bets that the backdoor lives in channels that clean inputs rarely use, so pruning them and fine-tuning repairs the model without knowing the trigger ([`transform-pruning`](https://ai-security-atlas.github.io/?node=transform-pruning), [`defense-backdoor-audit`](https://ai-security-atlas.github.io/?node=defense-backdoor-audit)). In a 32-channel layer the trigger shares channels with real digit features, so the bet fails. Limitation: the defender can measure only the clean-accuracy cost; the residual attack success in this table needs the trigger, which only the lab knows.

### Step D4 — Provenance: keep poisoned data out upstream

**Read**

Every audit above starts after the poison is already in the training set or the weights, and each one missed a trigger: D1 missed the blend, D2 the frame, D3 most of all three. The upstream control is to know where each training example came from. Record the source and a hash for every contributed batch, accept data only from contributors you can identify, and keep the manifest with the model, the way the vision-zoo `manifest.json` pins each checkpoint's recipe and sha256. Then a suspect batch can be removed and the model retrained, and Step D1's flagged images can be traced back to their contributor.

**Why**

[`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance) does not detect a trigger. It narrows who could have planted one and makes the repair a retrain without the bad source. Limitation: provenance only helps if a trusted pipeline enforces it. A trusted contributor who is compromised, or a web-scraped dataset with no contributor identity, still lets poison in, so keep the audits as a second line ([`life-data`](https://ai-security-atlas.github.io/?node=life-data)).

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-backdoor · evaluate.py · torch 2.14.1+cpu · backend none
measurement                             expected  this run (95% interval)
cnn-clean clean accuracy                   98.2%  530/540 98% [97-99%]
badnets clean accuracy                     98.2%  530/540 98% [97-99%]
badnets ASR, trigger                       97.1%  472/486 97% [95-98%]
badnets ASR, no trigger                     0.4%  2/486 0% [0-1%]
badnets ASR, wrong corner                   4.3%  21/486 4% [3-7%]
cnn-clean ASR, trigger                      0.0%  0/486 0% [0-1%]
blend ASR, own trigger                     85.6%  416/486 86% [82-88%]
frame ASR, own trigger                    100.0%  486/486 100% [99-100%]
D1 AC+ExRe precision, badnets             100.0%  38/38 100% [91-100%]
D1 AC+ExRe recall, badnets                100.0%  38/38 100% [91-100%]
D1 AC alone precision, badnets              9.4%  38/404 9% [7-13%]
D1 AC+ExRe recall, blend                    0.0%  0/38 0% [0-9%]
D2 anomaly index, badnets                   2.63  2.63
D2 anomaly index, frame                     1.23  1.23
D2 anomaly index, clean                     1.11  1.11
D2 unlearned badnets ASR                    1.4%  7/486 1% [1-3%]
D2 unlearned badnets clean accuracy        97.6%  527/540 98% [96-99%]
D3 fine-pruned badnets ASR                 87.9%  427/486 88% [85-90%]
RESULT: REPRODUCED
```

The table keeps the four quantities the Atlas caveat names apart: the trigger (one row per trigger and control), the target (7, `CANARY-DIGIT-7`), clean utility (accuracy rows) and attack success (ASR rows), each with its count and Wilson 95% interval from the shared `evalkit`. The attack rows run the shipped checkpoints and are deterministic; the D1–D3 rows come from your own defense runs and have wider tolerances in `expected/evaluate.json`. `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. The backdoored model and `cnn-clean` both score 530 of 540 on the test set. Write the two-line acceptance test you would add to a model-intake checklist so that this model fails it, and say what it assumes about the trigger.
2. Activation clustering found all 38 badnets images and none of the blended ones, and Neural Cleanse did the reverse for the frame. If you could run only one audit on a third-party checkpoint, which would you pick, and what would you write in the audit report about the triggers it cannot see?
3. Unlearning cost 0.6 points of clean accuracy and fine-pruning to 28 channels cost 6. Which of those costs could the defender measure without knowing the trigger, and which number in this table could it not have produced at all?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-backdoor/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-backdoor · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-backdoor/work (asr.json cleanse.json detect.json evaluate.json poison.json prune.json reversed.png sweep.json sweep.png train.json trigger_CANARY.png triggers.png variants.json)
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Add a label-consistency check: train a small classifier on the 200 trusted digits only, flag training images whose label it disagrees with, and compare its precision and recall with Step D1 on the badnets and blend splits.
- Sweep Neural Cleanse's mask penalty λ (0.005 to 0.05) and record the anomaly index of all four models; find out whether any setting flags `cnn-poison-frame` without also flagging `cnn-clean`.
- Implement STRIP (Gao et al. 2019) at inference time: blend each test input with clean trusted digits and flag inputs whose predictions stay confident; report its false-positive rate on clean test digits and its detection rate on each of the three triggers.
- Rerun Step D1 on the low-rate splits from Step 4 (6 and 13 poisoned images) and plot recall against the poison rate.

## Further Reading

- Gu et al., [BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain](https://arxiv.org/abs/1708.06733) (2017), the seed source `s-badnets`.
- Chen et al., [Targeted Backdoor Attacks on Deep Learning Systems Using Data Poisoning](https://arxiv.org/abs/1712.05526) (2017): the blended trigger.
- Chen et al., [Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering](https://arxiv.org/abs/1811.03728) (2018).
- Tran, Li and Madry, [Spectral Signatures in Backdoor Attacks](https://arxiv.org/abs/1811.00636) (2018).
- Wang et al., [Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks](https://people.cs.uchicago.edu/~ravenben/publications/pdf/backdoor-sp19.pdf) (IEEE S&P 2019).
- Liu, Dolan-Gavitt and Garg, [Fine-Pruning: Defending Against Backdooring Attacks on Deep Neural Networks](https://arxiv.org/abs/1805.12185) (2018).
- [adversarial-robustness-toolbox poisoning detection](https://adversarial-robustness-toolbox.readthedocs.io/en/latest/modules/defences/detector_poisoning.html) (`ActivationDefence`, `SpectralSignatureDefense`) and [`PoisoningAttackBackdoor`](https://adversarial-robustness-toolbox.readthedocs.io/en/latest/modules/attacks/poisoning.html).

---

[← prev](../format-gguf/README.md) · [All labs](../README.md) · [next →](../attack-prompt-leak/README.md)
