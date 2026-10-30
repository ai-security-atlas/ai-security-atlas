---
lab_id: LAB-08
title: "One gradient step"
node: attack-fgsm                        # == folder name == articles/<node-id>.md basename
related_nodes: [concept-gradients, arch-neural, attack-pgd, attack-physical, attack-visual-jailbreak, defense-robust-train, eval-adaptive, eval-asr, eval-threat-model, eval-transfer]
family: family-evasion
access_profile: A03
level: beginner                          # beginner | intermediate | advanced
time: "60 min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory, 2.2 GB disk for the workbench image."
canary: CANARY-DIGIT-3
last_tested: 2026-10-26
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v2"
---

# LAB-08 · One gradient step

> **Atlas node:** [Gradient-based adversarial perturbations / FGSM](https://ai-security-atlas.github.io/?node=attack-fgsm) · **Family:** family-evasion · **Level:** beginner · **Time:** 60 min · **Model backend:** none

## Overview

A neural network is trained by following the gradient of its loss with respect to its weights. The fast gradient sign method (FGSM) uses the same backpropagation, but asks for the gradient with respect to the *input* and takes one step along its sign: every pixel moves by ε in the direction that hurts the model most. In this lab you attack a small CNN that reads scikit-learn's 8×8 handwritten digits, the shared **vision-zoo** fixture that later vision labs reuse. One step at ε = 0.2 drops its test accuracy from 98% to under 4%, while random noise of exactly the same size barely matters. A targeted variant pushes digits toward the fixed class 3 (the canary `CANARY-DIGIT-3`). Then you measure two defenses honestly: input transforms, first against plain FGSM and then against an attacker who knows them, and adversarial training, checked with a stronger iterative attack. Source: [`labs/attack-fgsm`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-fgsm).

By the end you will be able to:

1. Compute an input gradient and an FGSM example, and explain why one signed step changes the prediction while same-size random noise does not.
2. Plot test accuracy against ε and state the threat model (perturbation set, preprocessing, targeted or not) that the curve depends on.
3. Show that a defense judged only against plain FGSM looks stronger than it is, and re-check it with an adaptive attack and PGD.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

This lab perturbs 8×8 digit images from scikit-learn's bundled dataset against a classifier you load locally. The targeted step always aims at the fixed class 3, reported as the canary `CANARY-DIGIT-3`, and has no option to change it. Nothing leaves the workbench container, and no step downloads anything.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-fgsm`](../../articles/attack-fgsm.md) |
| Family | [`family-evasion`](https://ai-security-atlas.github.io/?node=family-evasion) |
| Goal | [`goal-decisions`](https://ai-security-atlas.github.io/?node=goal-decisions), [`goal-evasion`](https://ai-security-atlas.github.io/?node=goal-evasion) |
| Access profile | `A03` White-box or surrogate optimization (caveat: *A surrogate and target must be separately identified; transfer is not guaranteed.*) |
| Read first | [`concept-gradients`](https://ai-security-atlas.github.io/?node=concept-gradients), [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) |
| Mitigated by | [`defense-robust-train`](https://ai-security-atlas.github.io/?node=defense-robust-train) (a coverage mapping, not complete prevention) |
| Evaluated by | [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-adaptive`](https://ai-security-atlas.github.io/?node=eval-adaptive), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`attack-pgd`](https://ai-security-atlas.github.io/?node=attack-pgd) (builds on this), [`attack-visual-jailbreak`](https://ai-security-atlas.github.io/?node=attack-visual-jailbreak), [`attack-physical`](https://ai-security-atlas.github.io/?node=attack-physical), [`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer) |

> [!NOTE]
> **Atlas caveat:** Specify perturbation set, preprocessing and target task.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The victim is a local classifier whose weights and gradients you need (A03). |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model server. |
| external-api | n/a | — | A hosted API never exposes gradients, so it cannot be the white-box victim here. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Every step finishes in under about a minute (the two training steps use one thread on purpose, so they are repeatable). |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB). The vision-zoo checkpoints are 170 KB; the lab writes under 1 MB to `work/`. |
| Total time | 60 min: about 10 min of commands, the rest reading and looking at the plots |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-02 · Moving a VLM with invisible pixels](../attack-visual-jailbreak/README.md) is the iterative version of this attack on a vision-language model; do it after this one.
- Concepts to read first: [`concept-gradients`](https://ai-security-atlas.github.io/?node=concept-gradients) and [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural).

## Explainer

```bash
# host
open attack-fgsm/explainer/index.html        # macOS
# xdg-open attack-fgsm/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in nine steps: the digit and the CNN, training as gradient descent on weights, the ε budget, the input gradient and its sign, the accuracy curve against random noise, the targeted canary, the transform table and adversarial training checked with PGD.

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
 Image atlas-labs/workbench:v2 Building
...
 Image atlas-labs/workbench:v2 Built
...
 Container atlas-labs-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image; with the `workbench` profile, `up -d` starts one idle container.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu scikit-learn 1.9.1 matplotlib 3.11.2 safetensors 0.8.0
[ok] vision-zoo checkpoints sha256 match (cnn-clean, cnn-mia-overfit, mlp-clean)
[ok] dataset sklearn-digits-8x8: 1257 train / 540 test, bundled with scikit-learn (no download)
[ok] work dir: /labs/attack-fgsm/work (writable)
[skip] model backend: this lab needs none
```

What to notice: the two vision-zoo checkpoints in `_shared/vision_zoo/checkpoints/` must match the sha256 values in their `manifest.json`, because every number below was measured on exactly these weights.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_victim | workbench | ≈5–10 s | 1 |
| 2 | s02_rebuild | workbench | ≈15–25 s | 2 |
| 3 | s03_one_step | workbench | ≈5–10 s | 3 |
| 4 | s04_sweep | workbench | ≈5–25 s | 6 |
| 5 | s05_targeted | workbench | ≈5–25 s | 7 |
| D1 | d1_transforms | workbench | ≈5–20 s | 8 |
| D2 | d1_transforms --adaptive | workbench | ≈20–60 s | 8 |
| D3 | d3_adv_train | workbench | ≈45–60 s | 9 |

Runtimes were measured in the workbench container on the test machine while seven other lab builds were running, and include about 1–3 s of container start-up per `docker compose run`; expect the lower end on an idle machine.

### Step 1 — Meet the victim · [explainer 1](explainer/index.html#attack-fgsm/1)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/s01_victim.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · s01_victim.py · torch 2.14.1+cpu · backend none
dataset sklearn-digits-8x8: 1257 train / 540 test, 8x8 grey, 10 classes, pixels in [0, 1]
model cnn-clean: CNN 38,282 params  file _shared/vision_zoo/checkpoints/cnn-clean.safetensors  sha256 82b5604fda5f (verified)
clean test accuracy: 98.15% (530/540)

test digit #40 (label 7), as the model sees it:
      **@@%%##@@--   0.00 0.00 0.62 1.00 0.81 0.75 0.94 0.31
    ::@@++##@@--     0.00 0.25 1.00 0.50 0.75 1.00 0.38 0.00
    --##..@@==       0.00 0.38 0.75 0.12 1.00 0.44 0.00 0.00
      --++%%         0.00 0.06 0.31 0.56 0.88 0.06 0.00 0.00
      ==@@##..       0.00 0.06 0.44 1.00 0.75 0.12 0.00 0.00
    ++@@@@##--       0.00 0.50 1.00 1.00 0.75 0.31 0.00 0.00
      ****           0.00 0.06 0.69 0.62 0.00 0.00 0.00 0.00
      %%--           0.00 0.00 0.88 0.38 0.00 0.00 0.00 0.00
prediction: 7: 100.0%  8: 0.0%  3: 0.0%
```

What to notice: the model sees the digit only as 64 numbers in [0, 1] (multiples of 1/16, the dataset's native grey levels), and it is very sure this one is a 7.

**Why**

The victim is a two-layer CNN with a small dense head ([`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural)), loaded from a safetensors file whose sha256 is checked against the vision-zoo manifest, so every learner attacks the same weights. It takes raw pixels with no hidden normalization, so ε = 0.2 below means 0.2 in pixel units, about 3 of the 16 grey levels. This is white-box access, profile A03: you hold the weights and can compute gradients.

### Step 2 — Rebuild it from its recipe · [explainer 2](explainer/index.html#attack-fgsm/2)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/s02_rebuild.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · s02_rebuild.py · torch 2.14.1+cpu · backend none
recipe cnn-clean: {"arch": "cnn", "batch": 64, "epochs": 30, "lr": 0.001, "seed": 0}
each update: weights <- weights - lr * Adam(d loss / d weights), loss = cross-entropy on 64 digits
epoch   1  mean train loss 2.2589
epoch   5  mean train loss 0.3499
epoch  10  mean train loss 0.1263
epoch  15  mean train loss 0.0642
epoch  20  mean train loss 0.0411
epoch  25  mean train loss 0.0218
epoch  30  mean train loss 0.0156
trained in 8.5s: test accuracy 98.15% (shipped 98.15%)
max |weight - shipped weight| = 0.00e+00  -> identical weights
wrote /labs/attack-fgsm/work/cnn-clean.safetensors  sha256 32c22f85b6b2 (shipped 82b5604fda5f; safetensors metadata differs, so compare weights, not file hashes)
```

What to notice: the retrained weights are bit-for-bit the shipped ones on this machine, but the file hash differs, and changes from run to run (`32c22f85b6b2` here, other values in other runs), because the metadata differs and safetensors does not write its metadata map in a fixed order; compare weights, not file hashes.

**Why**

Training is gradient descent on the weights: backpropagation gives ∂loss/∂weights for each batch and the optimizer moves the weights against it, with the inputs held fixed ([`concept-gradients`](https://ai-security-atlas.github.io/?node=concept-gradients)). FGSM reuses exactly this machinery with the roles swapped: the weights stay fixed and the input moves. The recipe is deterministic (fixed seed, one CPU thread, deterministic algorithms); another CPU or library build can still round differently, which is why the checkpoints are shipped instead of retrained.

### Step 3 — One gradient step · [explainer 3](explainer/index.html#attack-fgsm/3)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/s03_one_step.py --eps 0.2
```

**Observe**

```text
[atlas-lab] attack-fgsm · s03_one_step.py · torch 2.14.1+cpu · backend none
test digit #40, label 7, eps 0.2 (= 3.2 of the 16 grey levels)
gradient d loss / d pixel: max |g| 0.001, 64/64 pixels non-zero
sign(grad)        clean             adversarial
- - - - - - - -       **@@%%##@@--      ==%%**++##..
- - - - - - + +     ::@@++##@@--        %%--++%%++::
- - + + + + + +     --##..@@==        ..@@--@@**::::
+ + + + - - - -       --++%%        ::::++##**      
+ + + + - - - -       ==@@##..      ::::**@@++      
- - - - - + + +     ++@@@@##--        --%%%%++++::::
- - - - + + + +       ****              ====::::::::
- - + + + + + -       %%--              @@++::::::  

input            Linf     L2  prediction   p(label 7)
clean            0.00   0.00  7 (100.0%)  100.0%
random +/-eps    0.20   1.32  7 ( 98.3%)   98.3%
FGSM             0.20   1.36  8 ( 99.8%)    0.2%
RESULT label 7 -> FGSM 8, random noise 7; wrote /labs/attack-fgsm/work/one_step_eps0.2.png
```

What to notice: the gradient values are tiny (the model is confident), but FGSM uses only their sign; a step of 0.2 on every pixel turns the 7 into an 8, while random ±0.2 noise of almost the same L2 size leaves it a 7. Open `work/one_step_eps0.2.png` to see clean, gradient, random and FGSM side by side.

**Why**

FGSM computes g = ∂loss/∂x for the true label and sets x' = clip(x + ε·sign(g), 0, 1) ([`attack-fgsm`](https://ai-security-atlas.github.io/?node=attack-fgsm)). Under an L∞ budget, the sign step is the largest first-order increase of the loss you can buy, which is why one step is enough when the model is close to linear around the input. The threat model has to be stated ([`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model)): white-box access, an untargeted goal, an L∞ budget of 0.2 per pixel, and no preprocessing between the attacker's pixels and the model.

### Step 4 — Accuracy against ε, and random noise of the same size · [explainer 6](explainer/index.html#attack-fgsm/6)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/s04_sweep.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · s04_sweep.py · torch 2.14.1+cpu · backend none
model cnn-clean, 540 test digits, random noise seed 0
  eps   FGSM acc  random acc   L2 FGSM  L2 random
 0.00      98.1%       98.1%      0.00       0.00
 0.05      87.0%       97.8%      0.34       0.34
 0.10      55.0%       97.2%      0.68       0.67
 0.15      20.7%       95.2%      1.01       0.99
 0.20       3.7%       92.4%      1.33       1.30
 0.25       0.0%       88.0%      1.64       1.61
 0.30       0.0%       81.9%      1.95       1.90
RESULT eps 0.2: FGSM 3.7% vs random 92.4% (clean 98.1%); wrote /labs/attack-fgsm/work/sweep.png
```

What to notice: at every ε the random noise has the same L∞ size and about the same L2 size as the FGSM step, yet accuracy under noise stays above 80% while one FGSM step reaches 0% at ε = 0.25. `work/sweep.png` plots both curves.

**Why**

The accuracy-versus-ε curve is the honest way to report an evasion attack ([`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr)): one number at one ε hides how quickly the model degrades. The random baseline shows that the damage comes from the direction, not the size, of the change, so "the model is robust to noise" says nothing about adversarial robustness. FGSM is only a lower bound on what an attacker with this budget can do; Step D3 shows a stronger attack finding more.

### Step 5 — Targeted: make it read 3 · [explainer 7](explainer/index.html#attack-fgsm/7)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/s05_targeted.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · s05_targeted.py · torch 2.14.1+cpu · backend none
target class 3 (CANARY-DIGIT-3), 485 test digits that are not a 3
  eps  -> 3 (targeted)  -> 3 (untargeted)  still correct
 0.10            15.7%               9.1%          76.9%
 0.20            69.9%              21.2%          13.6%
 0.30            94.6%              27.0%           0.0%
RESULT eps 0.2: 69.9% of non-3 digits now read 3 (CANARY-DIGIT-3); 7/9 examples in /labs/attack-fgsm/work/adv_target_CANARY-DIGIT-3.png
```

What to notice: aiming at class 3 (the canary `CANARY-DIGIT-3`) gets far more digits to read 3 than the untargeted step does by accident, but a single step needs ε = 0.3 to reach 95%. `work/adv_target_CANARY-DIGIT-3.png` shows one example per source digit.

**Why**

The targeted variant steps *down* the loss of the chosen class, x' = clip(x − ε·sign(∂loss(x, 3)/∂x), 0, 1), which is a harder goal than "any wrong answer": the "target task" in the Atlas caveat ([`attack-fgsm`](https://ai-security-atlas.github.io/?node=attack-fgsm)). Report targeted and untargeted success separately, because they answer different questions about impact ([`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr)).

## Defend

### Step D1 — Input transforms against plain FGSM · [explainer 8](explainer/index.html#attack-fgsm/8)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/d1_transforms.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · d1_transforms.py · torch 2.14.1+cpu · backend none
attack: plain FGSM on the bare model (non-adaptive); cells = test accuracy with the transform in place
transform  clean  eps 0.05   eps 0.1  eps 0.15   eps 0.2
none       98.1%     87.0%     55.0%     20.7%      3.7%
blur3      92.4%     75.7%     48.7%     20.7%      5.4%
quant4     97.8%     94.4%     80.2%      3.9%      0.6%
RESULT non-adaptive eps 0.1: quant4 80.2% vs no transform 55.0%
```

What to notice: rounding every pixel to 5 grey levels (`quant4`) keeps 80% accuracy at ε = 0.1, where the bare model has 55%, and costs almost no clean accuracy; blur costs 6 points of clean accuracy and does not help at all.

**Why**

Here the attacker computed FGSM on the bare model, as if the transform did not exist, so the table measures a non-adaptive attack. A rounding step of 0.25 erases any change smaller than 0.125, which is why `quant4` looks strong at ε = 0.05 and 0.1 and fails from 0.15. Limitation: a defense that is only tested against an attacker who ignores it has not been evaluated ([`eval-adaptive`](https://ai-security-atlas.github.io/?node=eval-adaptive)); D2 fixes that.

### Step D2 — ...against an attacker who knows the transform (≈1 min) · [explainer 8](explainer/index.html#attack-fgsm/8)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/d1_transforms.py --adaptive
```

**Observe**

```text
[atlas-lab] attack-fgsm · d1_transforms.py · torch 2.14.1+cpu · backend none
attack: FGSM and PGD-10 through the transform (adaptive); cells = test accuracy with the transform in place
transform  clean         eps 0.05          eps 0.1         eps 0.15          eps 0.2
                       FGSM / PGD       FGSM / PGD       FGSM / PGD       FGSM / PGD
none       98.1%   87.0% /  86.7%   55.0% /  49.8%   20.7% /  13.5%    3.7% /   0.4%
blur3      92.4%   70.9% /  69.8%   38.0% /  32.6%    8.3% /   5.0%    0.2% /   0.0%
quant4     97.8%   94.8% /  94.4%   80.7% /  79.6%    2.8% /   0.6%    0.7% /   0.0%
RESULT adaptive: quant4 PGD 79.6% at eps 0.1 but 0.6% at eps 0.15; blur3 PGD 32.6% at eps 0.1
```

What to notice: attacked through the transform, blur drops from 48.7% to 32.6% at ε = 0.1, and `quant4` keeps about 80% at ε = 0.1 but falls to 0.6% at ε = 0.15.

**Why**

The adaptive attacker puts the transform inside the attack: blur is differentiable, and for rounding the gradient is passed straight through (BPDA), the standard way to attack a non-differentiable preprocessing step ([`eval-adaptive`](https://ai-security-atlas.github.io/?node=eval-adaptive)). `quant4` survives at ε = 0.1 only because that budget is smaller than half its rounding step, a property of this exact perturbation set and not robustness in general; a budget a little larger, or an L0/L2 attack that moves few pixels a lot, gets through. LAB-02 shows the same pattern on a VLM, with an EOT attacker and transfer to other models ([`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer)).

### Step D3 — Adversarial training, checked with PGD (≈1 min) · [explainer 9](explainer/index.html#attack-fgsm/9)

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/d3_adv_train.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · d3_adv_train.py · torch 2.14.1+cpu · backend none
recipe: cnn-clean recipe + 50% FGSM examples per batch at eps 0.2
epoch  10  mean train loss 0.9191
epoch  20  mean train loss 0.6401
epoch  30  mean train loss 0.5450
trained in 32s -> /labs/attack-fgsm/work/cnn-fgsm-at.safetensors

model         clean          eps 0.1          eps 0.2          eps 0.3
                       FGSM / PGD-10    FGSM / PGD-10    FGSM / PGD-10
cnn-clean     98.1%   55.0% /  49.8%    3.7% /   0.4%    0.0% /   0.0%
cnn-fgsm-at   97.8%   85.4% /  82.4%   53.9% /  37.8%   14.8% /   1.9%
RESULT cnn-fgsm-at at eps 0.2: FGSM says 53.9%, PGD-10 says 37.8%
```

What to notice: FGSM adversarial training lifts accuracy under FGSM at ε = 0.2 from 3.7% to 53.9% at a cost of 0.4 points of clean accuracy, but 10-step PGD at the same ε finds 37.8%, and at ε = 0.3 the trained model is down to 1.9%.

**Why**

Adversarial training replaces part of each batch with attacks against the current weights, so the model learns to resist that attack within that budget ([`defense-robust-train`](https://ai-security-atlas.github.io/?node=defense-robust-train)). Measured with the same attack it was trained on, it looks better than it is: PGD, which simply repeats small FGSM steps and projects back into the ε-box, finds a further 16 points of errors ([`attack-pgd`](https://ai-security-atlas.github.io/?node=attack-pgd)). Limitation: robustness holds only for the perturbation set and budget it was trained and evaluated on; report it against PGD and adaptive attacks, never against FGSM alone.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-fgsm · evaluate.py · torch 2.14.1+cpu · backend none
measurement (cnn-clean unless noted)    expected  this run
clean                                      98.1%     98.1%
fgsm eps 0.1                               55.0%     55.0%
fgsm eps 0.2                                3.7%      3.7%
random eps 0.2                             92.4%     92.4%
targeted->3 eps 0.2                        69.9%     69.9%
quant4 fgsm eps 0.1                        80.2%     80.2%
quant4 pgd eps 0.15                         0.6%      0.6%
fgsm-at fgsm eps 0.2                       53.9%     53.9%
fgsm-at pgd eps 0.2                        37.8%     37.8%
RESULT: REPRODUCED
```

The rows on the shipped weights are deterministic and must match within 0.5 points; the `fgsm-at` rows come from your Step D3 model and may differ by a few points on another CPU (tolerance 5 points). `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. Why is "accuracy under random noise" not evidence of adversarial robustness? Use the Step 4 numbers.
2. `quant4` keeps about 80% at ε = 0.1 even against the adaptive attack. Write the threat model under which that claim is true, and one change to it that breaks the claim.
3. Your FGSM-trained model scores 53.9% under FGSM and 37.8% under PGD at ε = 0.2. Which number goes in a report, and what would you run next before trusting it?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-fgsm/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-fgsm · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-fgsm/work (adv_target_CANARY-DIGIT-3.png adv_train.json cnn-clean.safetensors cnn-fgsm-at.safetensors evaluate.json one_step_eps0.2.json one_step_eps0.2.png sweep.json sweep.png targeted.json train_log.json transforms.json transforms_adaptive.json)
...
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Run `s04_sweep.py --model mlp-clean` and compare the MLP's curve with the CNN's: does the smaller model degrade faster or slower, and at which ε do they cross?
- Measure transfer: craft FGSM examples on `mlp-clean` and evaluate them on `cnn-clean` across the same ε grid, and compare with the white-box curve.
- Add a binarization transform (threshold at 0.5) to D1/D2 and evaluate it against the strongest adaptive attack you can build; report the clean-accuracy cost alongside the robust accuracy.
- Retrain D3 with PGD examples instead of FGSM and re-run the FGSM and PGD columns at ε = 0.1, 0.2 and 0.3.

## Further Reading

- Goodfellow, Shlens and Szegedy, [Explaining and Harnessing Adversarial Examples](https://arxiv.org/abs/1412.6572) (2014), the seed source `s-fgsm`: FGSM and the linearity explanation.
- Madry et al., [Towards Deep Learning Models Resistant to Adversarial Attacks](https://arxiv.org/abs/1706.06083) (2017): PGD and adversarial training.
- Athalye, Carlini and Wagner, [Obfuscated Gradients Give a False Sense of Security](https://arxiv.org/abs/1802.00420) (2018): BPDA and why input transforms need adaptive evaluation.
- Tramèr et al., [On Adaptive Attacks to Adversarial Example Defenses](https://arxiv.org/abs/2002.08347) (2020).
- Wong, Rice and Kolter, [Fast is better than free: Revisiting adversarial training](https://arxiv.org/abs/2001.03994) (2020): when FGSM adversarial training works and when it fails.
- [scikit-learn `load_digits`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) (the dataset) and the [safetensors documentation](https://huggingface.co/docs/safetensors).

---

[← prev](../adapt-lora/README.md) · [All labs](../README.md) · [next →](../attack-model-imitation/README.md)
