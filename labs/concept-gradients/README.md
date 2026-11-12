---
lab_id: LAB-50
title: "Gradients point both ways"
node: concept-gradients
related_nodes: [arch-neural, concept-parameters, attack-fgsm, attack-gcg, attack-gradient-leak, attack-pgd, attack-membership, defense-dp, defense-robust-train, eval-adaptive, life-pretrain, goal-evasion, goal-information, family-privacy]
family: family-evasion
access_profile: A03
level: intermediate
time: "60 min"
compose_profiles: [workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory, 2.4 GB disk for the workbench image; the lab writes under 1 MB to work/."
canary: CANARY-GRAD-3
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
covers:
  - {node: arch-neural, steps: "1-2", anchor: "step-1--one-loss-one-backward-pass--explainer-1"}
---

# LAB-50 · Gradients point both ways

> **Atlas node:** [Losses, gradients and optimization](https://ai-security-atlas.github.io/nodes/concept-gradients/) · **Family:** family-evasion · **Level:** intermediate · **Time:** 60 min · **Model backend:** none

> **Learning path:** Module 7 · step 1 of 6 · [Gradients and adversarial ML on small classifiers](../README.md#module-7-gradients-and-adversarial-ml-on-small-classifiers)

## Overview

Training a neural network means measuring a [loss](../primers/ml-in-one-page.md#loss-and-cross-entropy) (one number that says how wrong the model was), asking [backpropagation](../primers/ml-in-one-page.md#backpropagation) for the [gradient](../primers/ml-in-one-page.md#gradient) of that loss with respect to every [weight](../primers/ml-in-one-page.md#weights-and-parameters), and taking a small step against it. The same backward pass also answers two other questions, and that is the security point: the gradient with respect to the *pixels* tells an attacker how to change the input, and the gradient with respect to the weights of one private example, which is what a federated-learning client sends to a server, gives away that example's label.

What you will do, on a small CNN that reads scikit-learn's 8×8 handwritten digits (the shared **vision-zoo** architecture):

- Check one backward pass against finite differences, then train with 600 such steps to 98.1% test accuracy.
- Take one signed step of 0.2 per pixel along the pixel gradient (FGSM), turning a 7 into the canary class 3 (`CANARY-GRAD-3`) and dropping test accuracy to 3.7%, while random noise of the same size leaves 92.4%.
- Read the label of one private digit from the signs of its output-layer gradient (100 of 100 trials), and see that averaging 8 examples hides some labels while every label it names is still real.
- Measure two defenses, each of which covers one direction. Training with DP-SGD (clipping plus noise, Opacus) at a privacy budget of DP ε = 8 costs 12.2 accuracy points and does not stop FGSM (9.3% accuracy at a pixel budget of 0.2). Separately, a client that clips the gradient it shares and adds the same noise level drops label recovery to chance. Adversarial training raises FGSM accuracy to 53.9% and leaves the label leak at 100 of 100.

Headline result: one backward pass gives an attacker both a working input attack and the private label, and neither defense closes both. Source: [`labs/concept-gradients`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/concept-gradients).

By the end you will be able to:

1. Compute a loss and its gradient, check backpropagation against finite differences, and explain why stepping against the gradient trains a model.
2. Take the gradient of one example with respect to the input and with respect to the weights, and use the first to flip a prediction and the second to read the example's label.
3. Measure what DP-SGD and adversarial training each protect, at what cost, and which direction each one leaves open.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

This lab trains and attacks an 8×8 digit classifier on scikit-learn's bundled dataset inside the workbench container. The targeted input step always aims at the fixed class 3, reported as the canary `CANARY-GRAD-3`, and has no option to change it. The "private" digits whose labels the server recovers are public test images; no step reads your data, downloads anything or calls a model server.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`concept-gradients`](../../articles/concept-gradients.md) |
| Family | None in the seed graph (a concept node). The front matter and explainer kicker use [`family-evasion`](https://ai-security-atlas.github.io/nodes/family-evasion/), whose hub lists this lab first; Steps 5, 6 and D1 belong to [`family-privacy`](https://ai-security-atlas.github.io/nodes/family-privacy/). |
| Goal | [`goal-evasion`](https://ai-security-atlas.github.io/nodes/goal-evasion/) (Step 4 flips a prediction) and [`goal-information`](https://ai-security-atlas.github.io/nodes/goal-information/) (Step 5 reads a private label) |
| Access profile | `A03` White-box or surrogate optimization (caveat: *A surrogate and target must be separately identified; transfer is not guaranteed.*) for the input direction, Steps 3, 4 and 6a. The weight direction, Steps 5 and 6b, needs `A16` Shared gradients or updates (caveat: *Not an ordinary text-only API setting; batching and defenses change feasibility.*), and Step 6b measures the batching part of that caveat. |
| Read first | [`concept-parameters`](https://ai-security-atlas.github.io/nodes/concept-parameters/) |
| Mitigated by | None mapped for a concept node. Defend uses [`defense-dp`](https://ai-security-atlas.github.io/nodes/defense-dp/) (D1) and [`defense-robust-train`](https://ai-security-atlas.github.io/nodes/defense-robust-train/) (D2). |
| Evaluated by | [`eval-adaptive`](https://ai-security-atlas.github.io/nodes/eval-adaptive/): D2 checks adversarial training with a stronger attack than the one it trained on. |
| Related | [`attack-fgsm`](https://ai-security-atlas.github.io/nodes/attack-fgsm/) ([LAB-08](../attack-fgsm/README.md), the input direction in depth), [`attack-gcg`](https://ai-security-atlas.github.io/nodes/attack-gcg/) ([LAB-21](../attack-gcg/README.md), the same gradient over tokens), [`attack-gradient-leak`](https://ai-security-atlas.github.io/nodes/attack-gradient-leak/) (planned: rebuilding the image as well as the label), [`attack-membership`](https://ai-security-atlas.github.io/nodes/attack-membership/) ([LAB-13](../attack-membership/README.md), DP-SGD against membership inference), [`attack-pgd`](https://ai-security-atlas.github.io/nodes/attack-pgd/), [`life-pretrain`](https://ai-security-atlas.github.io/nodes/life-pretrain/), [`arch-neural`](https://ai-security-atlas.github.io/nodes/arch-neural/) (practiced in Steps 1–2) |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this concept node. Its article says that "whether any given leakage or attack succeeds depends on access and setup". Every number here comes from one 38,282-parameter CNN on 8×8 digits, one seed and one-thread CPU training. The label trick needs a ReLU before a softmax output layer and a gradient from one example or a small batch; bigger models, other activations and secure aggregation change what leaks.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The lab needs the weights and both kinds of gradient of a model it trains itself. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model server. |
| external-api | n/a | — | A hosted API exposes neither input gradients (A03) nor training updates (A16). |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Training uses one thread on purpose, so reruns give the same numbers. On the busy test machine the steps took 3 s to about 50 s each (D1 trains two DP-SGD models). |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.4 GB). The lab writes a 150 KB checkpoint and a few small JSON files to `work/`. |
| Total time | 60 min: about 4 min of commands, the rest reading the output |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: [LAB-05 · What the API reveals](../concept-logits/README.md) (softmax over logits, the scores this lab differentiates).
- Later in the path: [LAB-39 · Weights are what it is, activations are what it is doing](../concept-parameters/README.md) (the parameters this lab differentiates, in more depth).
- Concepts to read first: [`concept-parameters`](https://ai-security-atlas.github.io/nodes/concept-parameters/).

## Explainer

```bash
# host
open concept-gradients/explainer/index.html        # macOS
# xdg-open concept-gradients/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in eight steps: one backward pass, training, the two gradients of one digit, a one-step input attack, label recovery from a shared gradient, how far each direction reaches, DP-SGD and adversarial training.

## Setup

### Setup 1 — Profiles

Run the line for your backend in the terminal you use for this lab. It names this lab's Compose project and selects its services, so the commands below need no prefix and Cleanup stops only this lab. Run it again in any new terminal. The backend settings stay in `labs/.env` (Start here, step 2, in the [labs index](../README.md)).

| Backend | Line to run |
| :--- | :--- |
| container-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-concept-gradients COMPOSE_PROFILES=workbench` |
| host-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-concept-gradients COMPOSE_PROFILES=workbench` |
| external-api | `export COMPOSE_PROJECT_NAME=atlas-labs-concept-gradients COMPOSE_PROFILES=workbench` |
| none | `export COMPOSE_PROJECT_NAME=atlas-labs-concept-gradients COMPOSE_PROFILES=workbench` |

This lab calls no model server, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`.

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
 Container atlas-labs-concept-gradients-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] concept-gradients · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu opacus 1.6.0 scikit-learn 1.9.1 safetensors 0.8.0
[ok] vision-zoo cnn-clean sha256 82b5604fda5f matches (Step 2 retrains it and compares the weights)
[ok] dataset sklearn-digits-8x8: 1257 train / 540 test, bundled with scikit-learn (no download)
[ok] work dir: /labs/concept-gradients/work (writable)
[skip] model backend: this lab needs none
```

What to notice: the dataset ships inside scikit-learn and the reference checkpoint inside the repository, so nothing is downloaded.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_backprop | workbench | ≈4 s | 1 |
| 2 | s02_train | workbench | ≈10 s | 2 |
| 3 | s03_two_ways | workbench | ≈3 s | 3 |
| 4 | s04_fgsm | workbench | ≈4 s | 4 |
| 5 | s05_label_leak | workbench | ≈5 s | 5 |
| 6 | s06_scale | workbench | ≈15 s | 6 |
| D1 | d1_dp | workbench | ≈50 s | 7 |
| D2 | d2_adv_train | workbench | ≈20 s | 8 |

Runtimes are wall-clock times of one `docker compose run` each, measured on the test machine while other jobs were running on it. Steps 3 to D2 load the model that Step 2 writes to `work/cnn.safetensors`. Pixels are in [0, 1], and every input budget ε is the largest change allowed per pixel (0.1 is 1.6 steps on the dataset's 0–16 grey scale).

### Step 1 — One loss, one backward pass · [explainer 1](explainer/index.html#concept-gradients/1)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/s01_backprop.py
```

**Observe**

```text
[atlas-lab] concept-gradients · s01_backprop.py · torch 2.14.1+cpu · backend none
batch: 8 training digits, labels [6, 4, 4, 3, 2, 7, 2, 2]; model: 38,282 parameters with random weights
image 0 (label 6): p(label) = 0.098, largest p = 0.108 (class 0)
loss = mean cross-entropy = 2.3452  (a uniform guess over 10 classes gives ln 10 = 2.3026)
parameter          shape            numbers    |grad|
features.0.weight  [16, 1, 3, 3]        144    0.0290
...
head.3.weight      [10, 64]             640    0.1746
head.3.bias        [10]                  10    0.3980
gradient: 38,282 numbers, one per parameter; global L2 norm 0.6207
check features.0.weight[3, 0, 1, 1]: backprop +5.629513e-05  finite difference +5.629497e-05  rel. error 2.9e-06
...
check head.3.bias[6]: backprop -2.743749e-02  finite difference -2.743748e-02  rel. error 1.3e-08
one SGD step, lr 0.5: theta - lr * grad -> loss 2.3452 -> 2.2041;  theta + lr * grad -> loss 2.5322
RESULT backprop matches finite differences (worst rel. error 2.9e-06); a step against the gradient lowers the loss and a step along it raises it: yes (1 s)
```

What to notice: the untrained model is no better than a uniform guess (loss 2.35 against ln 10 = 2.30), its gradient has exactly one number per parameter, and one step against it lowers the loss on the same batch while one step along it raises the loss.

**Why**

The loss is the cross-entropy, −log p(correct label), averaged over the batch. Backpropagation applies the chain rule from the loss back through every layer, so a single backward pass returns ∂loss/∂θ for all 38,282 parameters θ for a small multiple (typically two to three times) of the cost of one forward pass; the finite-difference check nudges single weights by 10⁻⁶ and agrees to at least five significant digits. That is the whole training signal of [`arch-neural`](https://ai-security-atlas.github.io/nodes/arch-neural/) networks and of [`concept-gradients`](https://ai-security-atlas.github.io/nodes/concept-gradients/): θ ← θ − lr · ∂loss/∂θ.

### Step 2 — Train by repeating Step 1 · [explainer 2](explainer/index.html#concept-gradients/2)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/s02_train.py
```

**Observe**

```text
[atlas-lab] concept-gradients · s02_train.py · torch 2.14.1+cpu · backend none
recipe (vision-zoo cnn-clean): cnn, Adam lr 0.001, batch 64, 30 epochs, seed 0; 1,257 training digits -> 20 optimizer steps per epoch
epoch   1  mean train loss 2.2589
epoch   5  mean train loss 0.3499
epoch  10  mean train loss 0.1263
epoch  15  mean train loss 0.0642
epoch  20  mean train loss 0.0411
epoch  25  mean train loss 0.0218
epoch  30  mean train loss 0.0156
trained in 8 s: 600 gradient steps, loss 2.2589 -> 0.0156
accuracy: train 99.9%, test 98.1% (530/540 held-out digits)
same recipe as the shipped vision-zoo cnn-clean (manifest test_acc 0.9815): largest weight difference 0.0e+00
RESULT 600 steps against the gradient took the loss from 2.26 to 0.016 and test accuracy to 98.1%; weights saved to concept-gradients/work/cnn.safetensors
```

What to notice: 600 steps of the Step 1 update (with Adam's per-parameter step sizes) take the loss from 2.26 to 0.016, and because training is seeded and single-threaded the result is bit-identical to the shipped vision-zoo `cnn-clean` checkpoint.

**Why**

Each step uses the gradient of a fresh batch of 64 digits; the 540 test digits are never used for training, so 98.1% on them measures generalization. This loop is what [`life-pretrain`](https://ai-security-atlas.github.io/nodes/life-pretrain/) runs at a much larger scale, and the model it produces is the white-box target of the rest of the lab, the same weights that [LAB-08](../attack-fgsm/README.md) attacks.

### Step 3 — One backward pass, two gradients · [explainer 3](explainer/index.html#concept-gradients/3)

> [!NOTE]
> Three terms this step and Step 5 rely on. [Softmax](../primers/ml-in-one-page.md#softmax) turns the model's 10 class scores into probabilities p that sum to 1. The [one-hot](../primers/ml-in-one-page.md#one-hot) label y is 1 at the true class and 0 elsewhere, so p − y is negative only at the label (p is below 1 there) and positive everywhere else. [ReLU](../primers/ml-in-one-page.md#relu) sets negative values to 0, so its outputs h are never negative, and multiplying p − y by h keeps that sign. The notation ∂loss/∂x means "how fast the loss changes when x moves a little".

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/s03_two_ways.py
```

**Observe**

```text
[atlas-lab] concept-gradients · s03_two_ways.py · torch 2.14.1+cpu · backend none
test image #10: label 7, model says 7 with p = 1.0000; loss 4.41e-06
one backward pass returned d loss / d pixels (64 numbers) and d loss / d weights (38,282 numbers)
digit                pixel gradient |d loss / d x| (scaled)   sign of d loss / d x
    ..@@@@@@--       ..::..::--++::                         +-------
    **##**@@--     ..++++====++==                           -------+
  ..@@....@@       ..  ++**----++==                         --++++++
    ....**%%..     ..==@@##....----                         +++++---
    ..@@@@@@**         ::  ==**##::                         +++-----
      ##%%==             ::::::==::                         --+--+++
      @@--           ......**@@**..                         -+++++++
    --%%..             ::::**::                             +--+++--
pixel gradient: 31 positive, 33 negative, 0 zero; the 10 largest pixels hold 36.3% of its size
output-layer bias gradient vs p - onehot(label):
class          0         1         2         3         4         5         6         7         8         9
grad    +1.2e-10  +2.3e-10  +2.6e-10  +1.9e-07  +2.5e-06  +1.5e-07  +2.9e-12  -4.4e-06  +1.6e-06  +7.5e-09
p - y   +1.2e-10  +2.3e-10  +2.6e-10  +1.9e-07  +2.5e-06  +1.5e-07  +2.9e-12  -4.4e-06  +1.6e-06  +7.5e-09
negative entries: bias gradient [7]; output-layer weight rows with a negative sum [7]
RESULT the same backward pass gives a pixel map that says how to change the input and a weight gradient whose only negative output-layer entry is the label [7] (bias gradient = p - y within 9e-13)
```

What to notice: even for a digit the model is sure of (loss 4.4e-06), the pixel gradient is non-zero on all 64 pixels, and the only negative entry of the output-layer bias gradient sits at the true label 7.

**Why**

Autograd differentiates the loss with respect to anything that took part in the forward pass, so the same call that trains the model can be asked about the input. ∂loss/∂x is a saliency map: it says which pixels, moved which way, would raise the loss ([`attack-fgsm`](https://ai-security-atlas.github.io/nodes/attack-fgsm/), Step 4). For softmax with cross-entropy, ∂loss/∂(output bias) is exactly p − onehot(label), which is negative only at the label, so whoever sees the weight gradient sees the label ([`attack-gradient-leak`](https://ai-security-atlas.github.io/nodes/attack-gradient-leak/), Step 5).

### Step 4 — Against the input: one FGSM step · [explainer 4](explainer/index.html#concept-gradients/4)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/s04_fgsm.py
```

**Observe**

```text
[atlas-lab] concept-gradients · s04_fgsm.py · torch 2.14.1+cpu · backend none
test image #10 (a 7); budget eps = largest change per pixel, pixels in [0, 1]
  eps   random +/- eps   FGSM untargeted   FGSM toward 3  p(3)
 0.00                7                 7               7  0.000
 0.05                7                 7               7  0.000
 0.10                7                 7               7  0.004
 0.15                7                 7               7  0.274
 0.20                7                 8               3  0.961  -> CANARY-GRAD-3
 0.25                7                 8               3  0.999  -> CANARY-GRAD-3
 0.30                7                 8               3  1.000  -> CANARY-GRAD-3
digit before / after the targeted step at eps 0.2 (every pixel moved by at most 0.2):
      ..@@@@@@--       ::--@@@@@@++::
      **##**@@--     ::::%%++%%@@..
    ..@@....@@       ::--##  --%%
      ....**%%..     ::      %%**
      ..@@@@@@**     ::    %%%%%%==::
        ##%%==       ::    ++****::::
        @@--         ::    %%++::::::
      --%%..         ::::++@@--::
all 54 correctly classified test 7s at eps 0.1: FGSM toward 3 reads 3 on 5/54, random noise on 0/54
all 54 correctly classified test 7s at eps 0.2: FGSM toward 3 reads 3 on 46/54, random noise on 0/54
all 54 correctly classified test 7s at eps 0.3: FGSM toward 3 reads 3 on 53/54, random noise on 1/54
RESULT one signed gradient step turns the demo 7 into CANARY-GRAD-3 from eps 0.2; at eps 0.3 FGSM moves 53/54 test 7s to class 3 and random noise of the same size moves 1/54
```

What to notice: random noise of the same size leaves the demo 7 a 7 at all 7 budgets, while one step along the gradient sign makes it read 3 from ε = 0.2 on (`CANARY-GRAD-3`), and the same step works on 53 of the 54 test 7s at ε = 0.3, where noise moves 1 of 54.

**Why**

The fast gradient sign method moves every pixel by ε in the direction of sign(∂loss/∂x): up the loss of the true label (untargeted), or down the loss of a chosen label (targeted, here class 3). It is Step 1's training update turned around, applied to the input instead of the weights, and it needs only the white-box access of `A03`. [LAB-08](../attack-fgsm/README.md) studies it in depth, [LAB-21](../attack-gcg/README.md) uses the same gradient over a prompt's tokens ([`attack-gcg`](https://ai-security-atlas.github.io/nodes/attack-gcg/)), and [`attack-pgd`](https://ai-security-atlas.github.io/nodes/attack-pgd/) repeats the step.

### Step 5 — Against the data: a label from one shared gradient · [explainer 5](explainer/index.html#concept-gradients/5)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/s05_label_leak.py
```

**Observe**

```text
[atlas-lab] concept-gradients · s05_label_leak.py · torch 2.14.1+cpu · backend none
the server receives 38,282 gradient numbers for one private digit: no pixels, no label
output-layer weight gradient [10, 64]: row c = (p_c - y_c) * h, and h >= 0 after the ReLU
row            0         1         2         3         4         5         6         7         8         9
sum     +3.8e-04  +2.2e-06  +2.3e-12  +2.6e-08  -9.7e-02  +1.2e-02  +6.9e-02  +1.6e-02  +1.0e-05  +1.1e-10
< 0         0/64      0/64      0/64      0/64     34/64      0/64      0/64      0/64      0/64      0/64
h = 0 on 30 of 64 units (inactive ReLUs), so those columns are 0 in every row
guess: label 4 (the only row with a negative sum); true label 4
model                   recovered  per class (10 digits each)
trained (Step 2)          100/100  10 10 10 10 10 10 10 10 10 10
fresh random weights      100/100  10 10 10 10 10 10 10 10 10 10
RESULT the label of a private digit read off its shared gradient: 100/100 on the trained model, 100/100 on fresh weights; chance is 10/100 (2 s)
```

What to notice: only row 4 of the output-layer gradient has negative entries (34 of 64; the other 30 units are inactive and give 0), so the server names the label without seeing the image, and it does so for 100 of 100 digits on both a trained and an untrained model.

**Why**

In federated learning a client computes the gradient on its own data and sends only that update to a server, which is the `A16` access of [`attack-gradient-leak`](https://ai-security-atlas.github.io/nodes/attack-gradient-leak/). The output layer's weight gradient for class c is (p_c − y_c) times the previous layer's activations h, and h is never negative after a ReLU, so the sign pattern singles out the label (Zhao et al., iDLG). The label is the easy part: deep leakage from gradients (Zhu et al.) also optimizes a dummy image until its gradient matches, which is the planned attack-gradient-leak lab.

### Step 6 — How far each direction reaches · [explainer 6](explainer/index.html#concept-gradients/6)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/s06_scale.py
```

**Observe**

```text
[atlas-lab] concept-gradients · s06_scale.py · torch 2.14.1+cpu · backend none
(a) input gradient: accuracy on 540 test digits after one step of size eps
  eps   random +/- eps     FGSM
 0.00            98.1%    98.1%
 0.05            97.8%    87.0%
 0.10            97.2%    55.0%
 0.15            95.2%    20.7%
 0.20            92.4%     3.7%
 0.25            88.0%     0.0%
 0.30            81.9%     0.0%

(b) weight gradient: label set guessed from the mean gradient of B private digits (50 random batches per B)
  B  distinct labels  set exact  precision  recall
  1              1.0     50/50      1.000   1.000
  2              1.8     42/50      1.000   0.920
  4              3.5     14/50      1.000   0.727
  8              5.9      0/50      1.000   0.607
 16              8.2      0/50      1.000   0.468
 32              9.7      0/50      1.000   0.433
RESULT at eps 0.2 FGSM leaves 3.7% accuracy (random noise 92.4%); a mean over 8 private digits hides some labels (recall 0.61) and every label it names was in the batch at every B (precision 1.00) (15 s)
```

What to notice: one FGSM step at ε = 0.2 leaves 3.7% accuracy where random noise of the same size leaves 92.4%, and averaging more private digits into one gradient lowers how many labels the server finds (recall 0.61 at 8 digits) without ever producing a wrong one (precision 1.00).

**Why**

Part (a) is the curve [LAB-08](../attack-fgsm/README.md) starts from: the gradient direction is worth far more than its size. Part (b) is the batching part of the `A16` caveat: in a batch mean, confident examples contribute almost nothing and the positive p_c·h terms of the others can cover a label, so the plain sign test misses labels as B grows. Better estimators exist (Wainakh et al. recover label counts too), so treat recall here as a floor for what a batch leaks to [`attack-gradient-leak`](https://ai-security-atlas.github.io/nodes/attack-gradient-leak/), not a ceiling.

## Defend

### Step D1 — DP-SGD: clip and add noise (≈50 s) · [explainer 7](explainer/index.html#concept-gradients/7)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/d1_dp.py
```

**Observe**

```text
[atlas-lab] concept-gradients · d1_dp.py · torch 2.14.1+cpu · backend none
(a) DP-SGD training: clip 1.0, delta 1e-05, 30 epochs, batch 64 (Poisson sampling)
model                   sigma  epsilon  test acc  FGSM eps 0.2
no DP (Step 2)          0.000        -     98.1%          3.7%
DP-SGD epsilon 8        1.020     7.99     85.9%          9.3%
DP-SGD epsilon 1        4.766     0.99     72.4%          0.4%

(b) one shared single-digit gradient, released the DP-SGD way (clip to 1.0, then noise sigma * 1.0 per number)
raw gradient norms of the 100 digits: median 2.6e-02, largest 6.9e+01; clipping to 1.0 scales 10 of them down
 sigma  labels recovered
 0.000           100/100
 0.010            55/100
 0.100            29/100
 1.020            10/100
 4.766             7/100
RESULT DP-SGD at epsilon 7.99 (sigma 1.02) costs 12.2 accuracy points and cuts label recovery from 100/100 to 10/100; FGSM at eps 0.2 still leaves it at 9.3% (50 s)
```

The two ε here are different quantities. `epsilon` in table (a) is the DP privacy budget (DP ε; smaller means more privacy). `FGSM eps 0.2` is the pixel budget of Steps 4 and 6, the largest change per pixel.

What to notice: part (a) and part (b) are separate experiments. Training with DP-SGD at DP ε = 8 (σ = 1.02) costs 12.2 accuracy points, and that private model is still easy to fool with FGSM (9.3% at a pixel budget of 0.2, against 3.7% without DP). Part (b) takes the non-DP Step 2 model and releases each single-digit gradient the DP-SGD way, clipped and with the same σ = 1.02 noise; label recovery drops to 10 of 100, which is chance. Training with Opacus does not add that noise to a federated client's update: in federated learning the client has to clip and add the noise itself, because noise added by the server after it receives a raw update hides nothing from that server.

**Why**

DP-SGD (Abadi et al.) clips each example's gradient to a fixed norm C and adds Gaussian noise of standard deviation σ·C before the update, and an accountant turns σ, the sampling rate and the number of steps into a guarantee (DP ε, δ) on how much any one example can change what is released ([`defense-dp`](https://ai-security-atlas.github.io/nodes/defense-dp/); [LAB-13](../attack-membership/README.md) measures it against membership inference). Part (b) applies the same release to one client's gradient: most per-example gradients here are tiny (median norm 0.026), so even σ = 0.01 hides half the labels. Limitation: DP bounds what the weight gradients reveal and does nothing about the input gradient.

### Step D2 — Adversarial training covers the other direction (≈20 s) · [explainer 8](explainer/index.html#concept-gradients/8)

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/d2_adv_train.py
```

**Observe**

```text
[atlas-lab] concept-gradients · d2_adv_train.py · torch 2.14.1+cpu · backend none
recipe: Step 2's recipe + 50% FGSM examples per batch at eps 0.2
epoch  10  mean train loss 0.9191
epoch  20  mean train loss 0.6401
epoch  30  mean train loss 0.5450
trained in 16 s
model                       clean  FGSM 0.2  PGD-10 0.2  labels from gradients
Step 2 model                98.1%      3.7%        0.4%                100/100
FGSM adversarial training   97.8%     53.9%       37.8%                100/100
RESULT adversarial training lifts FGSM accuracy at eps 0.2 from 3.7% to 53.9%, PGD-10 lowers it to 37.8%; its single-digit gradients still give the label 100/100 (19 s)
```

What to notice: training on FGSM examples raises FGSM accuracy at ε = 0.2 from 3.7% to 53.9% at a cost of 2 of 540 clean test digits (98.1% to 97.8%), a 10-step attack still pushes it down to 37.8%, and the label leaks from this model's gradients exactly as before (100 of 100).

**Why**

Adversarial training ([`defense-robust-train`](https://ai-security-atlas.github.io/nodes/defense-robust-train/)) replaces part of each batch with attacked inputs, so the weights learn to resist the input gradient's direction. Judging it by the attack it trained on overstates it, which is why the PGD-10 column is there ([`eval-adaptive`](https://ai-security-atlas.github.io/nodes/eval-adaptive/); [LAB-08](../attack-fgsm/README.md) D3 and the planned attack-pgd lab go further). Limitation: it changes nothing about the weight gradients, so each defense in this section covers one direction and you need both when both kinds of access exist.

### Step D3 — Do not release per-example updates

**Read**

The cheapest control on the weight direction is architectural: a server that never sees one client's update cannot read its labels. Secure aggregation (Bonawitz et al. 2017) lets the server learn only the sum of many clients' updates, and Step 6b shows why the sum alone is not enough: an 8-digit mean still named every label it found correctly. So combine it with client-side DP noise (D1), a minimum number of clients per round, and no debugging endpoint or log that stores raw per-example gradients. On the input side, the control is the access itself: do not ship weights or a gradient endpoint for a model whose decisions matter, and assume a copied or surrogate model gives the attacker `A03` anyway ([`eval-threat-model`](https://ai-security-atlas.github.io/nodes/eval-threat-model/)).

**Why**

Each attack in this lab needs a specific access profile, `A03` for the input and `A16` for the updates ([`concept-gradients`](https://ai-security-atlas.github.io/nodes/concept-gradients/)). Removing that access is stronger than any noise level, and where it cannot be removed, D1 and D2 give measured, partial protection.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] concept-gradients · evaluate.py · torch 2.14.1+cpu · backend none
condition                                expected                  got                       measured
backprop vs finite differences           match                     match                     worst rel. error 1.3e-08 on the 10 output biases
trained CNN test accuracy                >= 97%                    >= 97%                    98.1%
retrained vs vision-zoo cnn-clean        same weights              same weights              largest difference 0.0e+00
demo 7 + random noise, eps 0.3           reads 7                   reads 7                   class 7
demo 7 + FGSM toward 3, eps 0.3          reads 3 (CANARY-GRAD-3)   reads 3 (CANARY-GRAD-3)   class 3
test accuracy, FGSM eps 0.2              < 15%                     < 15%                     3.7%
test accuracy, random noise eps 0.2      > 85%                     > 85%                     92.4%
label from one shared gradient, trained  >= 95/100                 >= 95/100                 100/100
label from one shared gradient, fresh    >= 95/100                 >= 95/100                 100/100
label set from a mean of 8, precision    >= 0.95                   >= 0.95                   1.000
label set from a mean of 8, recall       < 0.90                    < 0.90                    0.599
DP-SGD eps 8, accuracy cost              > 3 points                > 3 points                12.2 points (sigma 1.02)
DP-SGD sigma, label recovery             <= 25/100                 <= 25/100                 11/100
DP-SGD eps 8, FGSM eps 0.2 accuracy      < 30%                     < 30%                     9.3%
adv. training, FGSM eps 0.2 accuracy     > 30%                     > 30%                     53.9%
adv. training, PGD-10 below FGSM         yes                       yes                       37.8% < 53.9%
adv. training, label recovery            >= 95/100                 >= 95/100                 100/100
(50 s)
RESULT: REPRODUCED
```

Evaluate retrains the three models in memory and re-measures every finding, so it needs no earlier step's files. Each row is graded as a category (for example "≤ 25/100" for label recovery under DP noise), so a different noise draw does not flip it; its recall and DP rows draw different random batches and noise than Steps 6 and D1, which is why they read 0.599 and 11/100 where those steps printed 0.607 and 10/100. Its backprop row checks only the 10 output biases, so its worst relative error (1.3e-08) is smaller than Step 1's 2.9e-06, which covers weights in earlier layers too. `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. A federated-learning vendor says "we never collect your data, only gradients". Which rows of Steps 5 and 6 would you show them, and what would you ask about their batch size and aggregation?
2. D1 and D2 each leave one direction open. For a model whose weights are public and that is trained with federated learning, which defense covers which attack, and what does the pair cost in clean accuracy?
3. D2's FGSM column and PGD column disagree. Which one would you report as the model's robustness at ε = 0.2, and why?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python concept-gradients/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] concept-gradients · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed concept-gradients/work (adv_train.json backprop.json cnn.safetensors dp.json evaluate.json fgsm.json label_leak.json scale.json train.json two_ways.json)
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Replace the ReLU before the output layer with a function that can go negative (for example `nn.Tanh()`), retrain, and rerun Step 5's sign test. How often does it still name the label, and what would an attacker try next?
- Improve Step 6b's estimator: use the size of each negative row sum to guess how many digits of each label are in the batch, and report recall again at B = 8 and 16.
- Rebuild the digit itself, not only its label: start from a random 8×8 image, optimize it until its gradient matches the shared one (the DLG objective), and see how many steps a single digit takes at σ = 0 and at σ = 0.01.
- Add D1's ε = 8 noise to D2's adversarial training (both at once) and measure clean accuracy, FGSM and PGD accuracy, and label recovery in one table.

## Further Reading

- Goodfellow, Shlens and Szegedy, [Explaining and Harnessing Adversarial Examples](https://arxiv.org/abs/1412.6572) (2014), seed source `s-fgsm` of this node: the input gradient and FGSM (Steps 3, 4 and 6a).
- Zhu, Liu and Han, [Deep Leakage from Gradients](https://arxiv.org/abs/1906.08935) (NeurIPS 2019), seed source `s-gradients` of this node: reconstructing private training data from shared gradients.
- Zhao, Mopuri and Bilen, [iDLG: Improved Deep Leakage from Gradients](https://arxiv.org/abs/2001.02610) (2020): the label-from-sign result Step 5 reproduces.
- Wainakh et al., [User-Level Label Leakage from Gradients in Federated Learning](https://arxiv.org/abs/2105.09369) (2021): label sets and counts from batch gradients, the stronger form of Step 6b.
- Abadi et al., [Deep Learning with Differential Privacy](https://arxiv.org/abs/1607.00133) (2016), seed source `s-dp` of `defense-dp`: DP-SGD and its accountant (Step D1).
- Madry et al., [Towards Deep Learning Models Resistant to Adversarial Attacks](https://arxiv.org/abs/1706.06083) (2017), seed source `s-pgd` of `defense-robust-train`: adversarial training and PGD evaluation (Step D2).
- Bonawitz et al., [Practical Secure Aggregation for Privacy-Preserving Machine Learning](https://eprint.iacr.org/2017/281) (CCS 2017): the aggregation protocol of Step D3.
- [Opacus](https://opacus.ai/) (DP-SGD for PyTorch), PyTorch's [autograd tutorial](https://pytorch.org/tutorials/beginner/blitz/autograd_tutorial.html), and scikit-learn's [`load_digits`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html).

---

[← prev in path](../attack-weight-theft/README.md) · [All labs](../README.md) · [next in path →](../attack-fgsm/README.md)
