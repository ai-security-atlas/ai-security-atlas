---
lab_id: LAB-56
title: "Does it transfer?"
node: concept-transfer
related_nodes: [arch-neural, concept-adjacency, eval-transfer, attack-transfer-prompts, attack-pgd, attack-fgsm, attack-gcg, attack-visual-jailbreak, attack-model-imitation, concept-gradients, eval-adaptive, eval-asr, eval-threat-model, defense-robust-train, goal-evasion, family-evasion]
family: family-evasion
access_profile: A03
level: beginner
time: "60 min"
compose_profiles: [workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory, 2.2 GB disk for the workbench image; the lab writes under 1 MB to work/."
canary: CANARY-XFER-3
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
covers:
  - {node: concept-adjacency, steps: "6", anchor: "step-6--a-compatible-surface-is-a-hypothesis--explainer-6"}
---

# LAB-56 · Does it transfer?

> **Atlas node:** [Attack transferability](https://ai-security-atlas.github.io/?node=concept-transfer) · **Family:** family-evasion · **Level:** beginner · **Time:** 60 min · **Model backend:** none

## Overview

An attacker who cannot query or open the model they want to fool can train or download a similar one, craft adversarial inputs against it with full gradient access, and send those inputs to the real target. Whether that works is called transferability, and it is a measured property of one surrogate, one target and one attack, never a given. This lab measures it on scikit-learn's bundled 8×8 handwritten digits. The surrogate is the shipped vision-zoo CNN; the six targets solve the same task and differ from it step by step: the same CNN with another seed, an MLP, a small vision transformer, logistic regression, an RBF support-vector machine and a random forest. Twenty steps of PGD at a budget of 0.2 per pixel fool the surrogate on 100% of the test digits and make it read the canary class 3 (`CANARY-XFER-3`) on 80.5%. The same images fool the targets on 62.3% to 86.8% of digits and hit the canary on only 20.6% to 48.2%. Gradient alignment explains the ordering, an ensemble surrogate raises mean transfer from 72.7% to 80.0%, and two tricks from ImageNet papers do not help here. The defense side is a check you can reuse: grade each transfer claim from measurements on the target, with an interval. Two input transforms and a model vote in front of the most exposed target cut transfer by 8.6 to 30.1 points, and an adaptive attacker who knows them wins back 14.7 to 19.4 of those points. Source: [`labs/concept-transfer`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/concept-transfer).

By the end you will be able to:

1. Craft white-box adversarial examples on a surrogate and measure, with confidence intervals, how often they move each of several different targets.
2. Explain why some targets inherit an attack more than others (gradient alignment, budget, untargeted against targeted) and what an attacker can do to raise transfer.
3. Grade a transfer claim from evidence on the named target, and re-test a transfer-blunting defense with an adaptive attacker before trusting it.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

Every model in this lab is trained or loaded inside the workbench container from scikit-learn's bundled digits and the repository's vision-zoo checkpoints. The targeted attack always aims at the fixed class 3, reported as the canary `CANARY-XFER-3`, and has no option to change it. No step downloads anything, calls a model server or sends an image anywhere.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`concept-transfer`](../../articles/concept-transfer.md) |
| Family | None in the seed graph (a concept node). The front matter and explainer kicker use [`family-evasion`](https://ai-security-atlas.github.io/?node=family-evasion), the family of the attacks whose transfer this lab measures. |
| Goal | [`goal-evasion`](https://ai-security-atlas.github.io/?node=goal-evasion): every attack here makes a classifier give a wrong label. |
| Access profile | `A03` White-box or surrogate optimization (caveat: *A surrogate and target must be separately identified; transfer is not guaranteed.*). The attacker has the surrogate's weights only; the targets are separately identified, and Steps 3 and D1 measure the "not guaranteed" part. |
| Read first | [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) (the seed prerequisite) and [`concept-gradients`](https://ai-security-atlas.github.io/?node=concept-gradients) |
| Mitigated by | None mapped for a concept node. D2 tests input transforms and a model vote, and points to [`defense-robust-train`](https://ai-security-atlas.github.io/?node=defense-robust-train) as the defense that changes the model itself. |
| Evaluated by | [`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer) (source-model success against target-model transfer, Steps 3 and D1) and [`eval-adaptive`](https://ai-security-atlas.github.io/?node=eval-adaptive) (D2) |
| Related | [`concept-adjacency`](https://ai-security-atlas.github.io/?node=concept-adjacency) (practiced in Step 6), [`attack-transfer-prompts`](https://ai-security-atlas.github.io/?node=attack-transfer-prompts) ([LAB-21](../attack-gcg/README.md) Step 7, the same question for text), [`attack-visual-jailbreak`](https://ai-security-atlas.github.io/?node=attack-visual-jailbreak) ([LAB-02](../attack-visual-jailbreak/README.md) Step 6), [`attack-pgd`](https://ai-security-atlas.github.io/?node=attack-pgd), [`attack-fgsm`](https://ai-security-atlas.github.io/?node=attack-fgsm) ([LAB-08](../attack-fgsm/README.md)), [`attack-model-imitation`](https://ai-security-atlas.github.io/?node=attack-model-imitation) ([LAB-09](../attack-model-imitation/README.md), how an attacker gets a surrogate), [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this concept node. Its summary reads: "Success on one model or configuration does not establish success on a different target." Every rate here holds for these seven models, 8×8 digits, an L∞ budget of 0.2 and one fixed seed; a different task, input size or budget gives different rates, and this lab's own Step 5 shows that published transfer tricks can fail to carry over to a new setting.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The surrogate needs weights and gradients, and every target is a local classifier the lab trains or loads. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model server. |
| external-api | n/a | — | Same. LAB-02 and LAB-21 measure transfer to served models; Step 6 links their results. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Training and attacks use one thread on purpose, so reruns give the same numbers. On the busy test machine the steps took 3 s to about 70 s each; Step 1 trains two models and Step 5 runs an ensemble attack per target. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB). The lab writes two small checkpoints (about 230 KB), the adversarial images and a few JSON files to `work/`. |
| Total time | 60 min: about 6 min of commands, the rest reading the output |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: [LAB-50 · Gradients point both ways](../concept-gradients/README.md), which explains the input gradient this lab's attacks follow. [LAB-08 · One gradient step](../attack-fgsm/README.md) shows the white-box attack itself (optional).
- Concepts to read first: [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural), [`concept-gradients`](https://ai-security-atlas.github.io/?node=concept-gradients).

## Explainer

```bash
# host
open concept-transfer/explainer/index.html        # macOS
# xdg-open concept-transfer/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in eight steps: the zoo, the white-box attack, the transfer matrix, why it transfers, a stronger attacker, hypothesis against evidence, grading a claim on the target, and defenses with an adaptive re-test.

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
 Image atlas-labs/workbench:v4 Built
...
 Container atlas-labs-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] concept-transfer · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu scikit-learn 1.9.1 safetensors 0.8.0
[ok] vision-zoo cnn-clean sha256 82b5604fda5f matches (test accuracy 0.9815)
[ok] vision-zoo mlp-clean sha256 5ab65e33d5ae matches (test accuracy 0.9667)
[ok] dataset sklearn-digits-8x8: 1257 train / 540 test, bundled with scikit-learn (no download)
[ok] work dir: /labs/concept-transfer/work (writable)
[skip] model backend: this lab needs none
```

What to notice: the dataset ships inside scikit-learn and both shipped checkpoints match their recorded hashes, so nothing is downloaded.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_zoo | workbench | ≈1 min | 1 |
| 2 | s02_whitebox | workbench | ≈10 s | 2 |
| 3 | s03_matrix | workbench | ≈10 s | 3 |
| 4 | s04_why | workbench | ≈20 s | 4 |
| 5 | s05_stronger | workbench | ≈1–1.5 min | 5 |
| 6 | (reading) | — | — | 6 |
| D1 | d1_target_eval | workbench | ≈10 s | 7 |
| D2 | d2_transforms | workbench | ≈30 s | 8 |

Runtimes are wall-clock times of one `docker compose run` each, measured on the test machine while other jobs were running on it. Steps 2 to D2 load the two models Step 1 writes to `work/`, and Steps 3, D1 and D2 load the adversarial images Step 2 writes to `work/adv.safetensors`. Pixels are in [0, 1], and the budget ε is the largest change allowed per pixel (0.2 is 3.2 of the dataset's 16 grey levels). A success rate always counts only the test digits that model classified correctly before the attack, and brackets give a 95% Wilson interval.

### Step 1 — One task, seven models (≈1 min) · [explainer 1](explainer/index.html#concept-transfer/1)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/s01_zoo.py
```

**Observe**

```text
[atlas-lab] concept-transfer · s01_zoo.py · torch 2.14.1+cpu · backend none
task: sklearn-digits-8x8, 1257 training / 540 test digits, 10 classes, pixels in [0, 1]
trained cnn-b (30 epochs) and vit (60 epochs) in 55 s; saved to work/cnn_b.safetensors, work/vit.safetensors
model    role       what it is                             family   params  test acc  agrees with cnn-a
cnn-a    surrogate  CNN, vision-zoo cnn-clean (seed 0)     neural    38282     98.1%  100.0%
cnn-b    target     same CNN, seed 1                       neural    38282     98.0%  98.7%
mlp      target     MLP, vision-zoo mlp-clean              neural     4810     96.7%  97.6%
vit      target     tiny vision transformer                neural    18154     96.3%  95.7%
logreg   target     logistic regression (sklearn)          linear        -     97.0%  97.4%
svm-rbf  target     RBF support-vector machine (sklearn)   kernel        -     99.4%  98.3%
forest   target     random forest, 200 trees (sklearn)     trees         -     97.8%  97.0%
RESULT seven models from four families (neural, linear, kernel, trees) solve the same task: test accuracy >= 96.3% for all, and every target agrees with the surrogate on >= 95.7% of clean digits (58 s)
```

What to notice: on clean digits the seven models are almost interchangeable (96.3% to 99.4% accuracy, at least 95.7% agreement with the surrogate), even though they range from a convolutional network to a forest of decision trees with no gradient at all.

**Why**

The attacker's surrogate `cnn-a` is the shipped vision-zoo `cnn-clean` CNN, the same weights [LAB-08](../attack-fgsm/README.md) and [LAB-50](../concept-gradients/README.md) attack. The six targets are separately identified models, as the `A03` caveat asks, and they step away from the surrogate one difference at a time: seed, architecture ([`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) MLP and a 2×2-patch vision transformer), then three scikit-learn models from other families (a linear model, a kernel machine and a forest of decision trees) that the attack never differentiates. Agreement on clean inputs is what makes transfer plausible; the next steps test whether it also holds for adversarial ones.

### Step 2 — White-box on the surrogate · [explainer 2](explainer/index.html#concept-transfer/2)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/s02_whitebox.py
```

**Observe**

```text
[atlas-lab] concept-transfer · s02_whitebox.py · torch 2.14.1+cpu · backend none
surrogate cnn-a (CNN, vision-zoo cnn-clean (seed 0)); budget eps 0.2 per pixel, PGD 20 steps of 0.025, all 540 test digits
largest pixel change 0.200, mean pixel change 0.141 (the noise baseline moves every pixel by +/- 0.2, clipped to [0, 1])
on the surrogate itself             success  95% CI          images
random +/- 0.2 noise, any error      6.4% [ 4.6-  8.8]  34/530
PGD untargeted, any error          100.0% [99.3-100.0]  530/530
PGD targeted, reads 3               80.5% [76.7- 83.8]  384/477
demo: test digit #10 (a 7), surrogate p(3) 0.000 -> 0.972 after targeted PGD -> CANARY-XFER-3
      ..@@@@@@--       ..--@@@@@@--..
      **##**@@--     ....%%++%%@@..
    ..@@....@@       ..::##  --##
      ....**%%..             %%**
      ..@@@@@@**           ######==..
        ##%%==       ..    ++****::..
        @@--         ..    ##++......
      --%%..         ....++@@--....
RESULT white-box on the surrogate: PGD untargeted 100.0%, targeted CANARY-XFER-3 80.5%, random noise of the same size 6.4%; adversarial sets saved to work/adv.safetensors (6 s)
```

What to notice: with the surrogate's gradients, PGD fools it on every one of the 530 digits it got right and makes 80.5% of the non-3 digits read 3 (`CANARY-XFER-3`), while random noise of the same size fools it on 6.4%.

**Why**

Projected gradient descent ([`attack-pgd`](https://ai-security-atlas.github.io/?node=attack-pgd)) starts here from the clean image (Madry et al. add a random start), repeats the FGSM step of [`attack-fgsm`](https://ai-security-atlas.github.io/?node=attack-fgsm) twenty times and clips the total change back into the ±0.2 box after each step. The untargeted attack raises the loss of the true label; the targeted one lowers the loss of class 3, which is harder because it has to land in one specific class. These are source-model numbers in the sense of [`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer): they describe the model the attack was optimized on and nothing else.

### Step 3 — The transfer matrix · [explainer 3](explainer/index.html#concept-transfer/3)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/s03_matrix.py
```

**Observe**

```text
[atlas-lab] concept-transfer · s03_matrix.py · torch 2.14.1+cpu · backend none
PGD-20 at eps 0.2, crafted on cnn-a only; success [95% CI] on the digits each model got right clean
model          noise, any error   untargeted, any error       targeted, reads 3
cnn-a         6.4% [ 4.6-  8.8]     100.0% [99.3-100.0]      80.5% [76.7- 83.8]  (white-box)
cnn-b         4.5% [ 3.1-  6.7]      86.8% [83.6- 89.4]      48.2% [43.8- 52.7]
mlp           5.7% [ 4.1-  8.1]      79.7% [76.0- 82.9]      35.8% [31.6- 40.3]
vit          20.0% [16.8- 23.7]      62.3% [58.1- 66.4]      20.6% [17.1- 24.5]
logreg        5.2% [ 3.6-  7.4]      73.5% [69.5- 77.1]      37.6% [33.3- 42.0]
svm-rbf       2.0% [ 1.1-  3.6]      64.1% [59.9- 68.0]      28.2% [24.3- 32.3]
forest        8.7% [ 6.6- 11.4]      69.7% [65.6- 73.5]      20.6% [17.2- 24.5]
untargeted transfer ranges from 62.3% (vit) to 86.8% (cnn-b); targeted from 20.6% (vit) to 48.2% (cnn-b)
RESULT white-box 100.0% untargeted / 80.5% targeted; transfer 62.3%-86.8% untargeted and 20.6%-48.2% targeted (CANARY-XFER-3); the surrogate overstates the weakest target by 37.7 points (5 s)
```

What to notice: every target is fooled far more often than by noise, yet less often than the surrogate, and the targeted canary loses most of its strength on the way (80.5% on the surrogate, 20.6% to 48.2% on the targets).

**Why**

This table is the evidence [`concept-transfer`](https://ai-security-atlas.github.io/?node=concept-transfer) asks for: one source, six named targets, one budget, with intervals. Untargeted transfer is real here even to models of other families, such as the RBF SVM and the random forest, whose piecewise-constant output has no useful gradient at all. That is why a surrogate is a practical attack path when an API hides the weights ([LAB-09](../attack-model-imitation/README.md) shows how an attacker builds one by querying). The targeted rate is the one that matters for a goal like "make it say 3", and it falls to a fifth on the vision transformer and the forest.

### Step 4 — Why some targets inherit more · [explainer 4](explainer/index.html#concept-transfer/4)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/s04_why.py
```

**Observe**

```text
[atlas-lab] concept-transfer · s04_why.py · torch 2.14.1+cpu · backend none
(a) input-gradient alignment with the surrogate, mean over the 540 test digits
target    cosine  same sign  untargeted transfer (Step 3)
cnn-b      0.708      72.5%  86.8%
mlp        0.642      70.2%  79.7%
logreg     0.653      65.0%  73.5%
vit        0.150      53.5%  62.3%
random     0.003      49.9%  (a random direction, for scale)
order by transfer: cnn-b > mlp > logreg > vit; by same sign: cnn-b > mlp > logreg > vit; by cosine: cnn-b > logreg > mlp > vit

(b) untargeted success by budget eps: transfer from the surrogate / random noise of the same size
model            eps 0.1          eps 0.2          eps 0.3
cnn-a      49.2% /   0.9%   100.0% /   6.4%   100.0% /  17.2%
cnn-b      27.8% /   1.1%    86.8% /   4.5%    99.1% /  14.2%
mlp        25.1% /   1.7%    79.7% /   5.7%    99.4% /  16.7%
vit        17.1% /   5.2%    62.3% /  20.0%    90.4% /  39.0%
logreg     21.6% /   1.7%    73.5% /   5.2%    97.5% /  13.5%
svm-rbf    11.0% /   0.2%    64.1% /   2.0%    96.6% /  10.2%
forest     30.1% /   4.7%    69.7% /   8.7%    98.3% /  25.4%
RESULT gradient alignment tracks transfer: sign agreement orders the four targets exactly as transfer does, and the highest and lowest cosine are the most and least affected targets (cnn-b, vit); transfer beats same-size noise on every target at every budget by at least 10.8 points (10 s)
```

What to notice: the same CNN with another seed has an input gradient that points most like the surrogate's (cosine 0.708) and inherits the most, the vision transformer's barely lines up (0.150) and inherits the least, and the budget matters as much as the model: at ε 0.1 the most affected target reaches 30.1%, and at ε 0.3 every target is above 90%.

**Why**

PGD follows the sign of the surrogate's input gradient, so an image built that way also raises a target's loss to the extent that the target's gradient points the same way. The "same sign" column counts the pixels where the two gradients agree in sign, and it orders the four targets the lab differentiates the way the transfer matrix does. Demontis et al. (2019) name gradient alignment as one of three factors in transfer, together with how vulnerable the target is (the size of its input gradient) and how smooth the surrogate's loss is. It is still a description of these four models: the lab computes no gradient for the SVM, the forest has none worth comparing, and the cosine column puts the MLP and logistic regression in the other order ([`concept-gradients`](https://ai-security-atlas.github.io/?node=concept-gradients)).

### Step 5 — A stronger attacker (≈1–1.5 min) · [explainer 5](explainer/index.html#concept-transfer/5)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/s05_stronger.py
```

**Observe**

```text
[atlas-lab] concept-transfer · s05_stronger.py · torch 2.14.1+cpu · backend none
untargeted transfer at eps 0.2 (PGD-20); ensemble = the neural zoo models except the target
target   plain cnn-a  momentum  diversity  ensemble   ensemble members
cnn-b          86.8%     84.9%      82.8%     85.4%   cnn-a+mlp+vit
mlp            79.7%     79.9%      75.7%     86.2%   cnn-a+cnn-b+vit
vit            62.3%     61.5%      57.7%     71.5%   cnn-a+cnn-b+mlp
logreg         73.5%     73.3%      69.1%     86.1%   cnn-a+cnn-b+mlp+vit
svm-rbf        64.1%     63.5%      58.3%     75.0%   cnn-a+cnn-b+mlp+vit
forest         69.7%     69.3%      65.3%     75.8%   cnn-a+cnn-b+mlp+vit
mean           72.7%     72.1%      68.1%     80.0%

targeted toward 3 (CANARY-XFER-3): plain cnn-a vs leave-one-out ensemble
cnn-b     48.2% [43.8- 52.7] ->  46.3% [41.9- 50.8]
mlp       35.8% [31.6- 40.3] ->  38.6% [34.3- 43.1]
vit       20.6% [17.1- 24.5] ->  25.9% [22.1- 30.1]
logreg    37.6% [33.3- 42.0] ->  44.2% [39.7- 48.7]
svm-rbf   28.2% [24.3- 32.3] ->  35.6% [31.5- 40.0]
forest    20.6% [17.2- 24.5] ->  22.7% [19.2- 26.7]
RESULT the ensemble raises mean untargeted transfer 72.7% -> 80.0% (largest gain logreg, +12.6 points) and targeted 31.8% -> 35.6%; momentum barely moves it (72.1%) and input diversity lowers it (68.1%) on 8x8 digits (68 s)
```

What to notice: attacking several surrogates at once raises transfer to five of the six targets (the exception is `cnn-b`, whose closest relative `cnn-a` now shares the vote with less similar models), while momentum changes almost nothing and input diversity lowers transfer on every target.

**Why**

Liu et al. (2017) showed that an image that fools several models at once is more likely to fool another one, and the ensemble here is leave-one-out, so no target ever helps build its own images. Momentum (Dong et al. 2018) and input diversity (Xie et al. 2019) were developed on 299×299 ImageNet photos. There, resizing and padding by a few pixels barely changes the picture; on an 8×8 digit a one-pixel shift moves the image by an eighth of its width, and input diversity works against the attacker. Momentum, which smooths the step direction across iterations, changes the mean by less than a point here. That is the [`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer) point turned on attack methods themselves: a technique's published gain was measured in its own setting, and yours needs its own measurement.

### Step 6 — A compatible surface is a hypothesis · [explainer 6](explainer/index.html#concept-transfer/6)

**Read**

Before Step 3, every target looked like a good candidate: the same task, the same 8×8 input with pixels in [0, 1], at least 95.7% agreement with the surrogate on clean digits. That is architectural applicability in the sense of [`concept-adjacency`](https://ai-security-atlas.github.io/?node=concept-adjacency): the attack has the right input channel and the right output to aim at. The matrix is the evidence, and it splits the one hypothesis into two answers. Untargeted transfer holds for all six targets; the targeted canary reaches at most 48.2% of digits on any of them and 20.6% on two. Neither answer could be read off the surface. Other labs in the Atlas give the same lesson across modalities. In [LAB-02](../attack-visual-jailbreak/README.md) Step 6, a plain PGD image that makes SmolVLM print its canary reaches neither `qwen2.5vl:3b` nor `moondream:1.8b` (0/5 each). In [LAB-21](../attack-gcg/README.md) Step 7, a GCG suffix built on SmolLM2-135M works on neither held-out model (0/2), not even the 360M model from the same family. Those small samples are evidence of weak transfer, and D1 measures how much a 0/5 can still hide.

**Why**

A catalog entry such as "this technique targets decoder-only models" or "adversarial images transfer between classifiers" is a place to look, and [`concept-adjacency`](https://ai-security-atlas.github.io/?node=concept-adjacency) asks for a reproduction on the named target before it sets severity. [`attack-transfer-prompts`](https://ai-security-atlas.github.io/?node=attack-transfer-prompts) adds the threat-model half of the same point: an attacker who receives a precomputed suffix or image has different capabilities from one who optimized it against the target.

## Defend

### Step D1 — Grade every claim on the target · [explainer 7](explainer/index.html#concept-transfer/7)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/d1_target_eval.py
```

**Observe**

```text
[atlas-lab] concept-transfer · d1_target_eval.py · torch 2.14.1+cpu · backend none
claim: 'the attack transfers to <target>' = success >= 50% on that target; graded by its 95% interval
what the surrogate alone would predict: untargeted 100.0%, targeted 80.5% for every target
claim                  all images [95% CI]             verdict       first 5 images            verdict       5-image range (200 draws)
untargeted -> cnn-b     86.8% [83.6- 89.4] 459/529     supported     100.0% [56.6-100.0] 5/5   supported     40%-100%
untargeted -> mlp       79.7% [76.0- 82.9] 416/522     supported      80.0% [37.6- 96.4] 4/5   inconclusive  40%-100%
untargeted -> vit       62.3% [58.1- 66.4] 324/520     supported      20.0% [ 3.6- 62.4] 1/5   inconclusive  0%-100%
...
targeted 3 -> cnn-b     48.2% [43.8- 52.7] 230/477     inconclusive   40.0% [11.8- 76.9] 2/5   inconclusive  0%-100%
targeted 3 -> mlp       35.8% [31.6- 40.3] 168/469     refuted        40.0% [11.8- 76.9] 2/5   inconclusive  0%-100%
targeted 3 -> vit       20.6% [17.1- 24.5] 96/467      refuted         0.0% [ 0.0- 43.4] 0/5   refuted       0%-80%
targeted 3 -> logreg    37.6% [33.3- 42.0] 177/471     refuted        60.0% [23.1- 88.2] 3/5   inconclusive  0%-80%
targeted 3 -> svm-rbf   28.2% [24.3- 32.3] 136/483     refuted        40.0% [11.8- 76.9] 2/5   inconclusive  0%-100%
targeted 3 -> forest    20.6% [17.2- 24.5] 98/475      refuted        40.0% [11.8- 76.9] 2/5   inconclusive  0%-80%
RESULT measured on each target: untargeted transfer supported for 6/6 targets, targeted CANARY-XFER-3 supported for 0/6 and refuted for 5/6; the surrogate's own rate overstates the targets by 13.2-60.0 points; with 5 images 10/12 claims are inconclusive (3 s)
```

What to notice: graded on the targets, the untargeted claim holds for all six and the targeted canary claim holds for none, the surrogate's own rate would have overstated the targets by 13.2 to 60.0 points, and five images per target leave 10 of the 12 claims undecided (the first five vision-transformer digits read 1/5 where the full rate is 62.3%).

**Why**

This is the first defense step from [`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer): source-model success and target-model transfer are different results, so a report names the target, the number of trials and an interval for each claim, and reads the target's rate from the target. The same check serves both sides. A red team uses it before writing "transfers to X", and a defender runs it against their own deployed model, because no surrogate number answers "is my model affected?". Limitation: the grade is only as good as the sample; a 0/5 like LAB-02's still allows up to 43.4% (its upper bound), so a low-transfer finding needs more trials before it becomes "does not transfer".

### Step D2 — Blunt transfer, then attack adaptively · [explainer 8](explainer/index.html#concept-transfer/8)

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/d2_transforms.py
```

**Observe**

```text
[atlas-lab] concept-transfer · d2_transforms.py · torch 2.14.1+cpu · backend none
defended target: cnn-b; untargeted success at eps 0.2 on the digits the defended system gets right clean
system                         clean acc         transfer (Step 2)        adaptive white-box  adaptive attack
cnn-b, no defense                  98.0%        86.8% [83.6- 89.4]        98.9% [97.5- 99.5]  PGD-50 on cnn-b
(a) + noise sigma 0.15             95.7%        78.1% [74.4- 81.5]        92.8% [90.3- 94.8]  PGD-50, noise in the loop (EOT)
(b) + quantize to 3 levels         97.0%        56.7% [52.4- 60.9]        75.2% [71.3- 78.7]  PGD-50, quantizer passed through (BPDA)
(c) vote cnn-b+vit+svm-rbf         99.1%        73.1% [69.2- 76.7]        92.5% [90.0- 94.5]  PGD-50 on cnn-b+vit logits
(b) at eps 0.3, where a pixel can cross a rounding threshold more often: transfer 100.0% [99.3-100.0], adaptive 100.0% [99.3-100.0]
RESULT the three defenses cut transfer by 8.6-30.1 points (best: (b) + quantize to 3 levels, 56.7%); the adaptive attacker wins back 14.7-19.4 points and reaches 75.2%-92.8% (28 s)
```

What to notice: each defense lowers transfer to `cnn-b` (quantization the most, from 86.8% to 56.7%), and an attacker who knows the defense and holds the weights wins back 14.7 to 19.4 points of that; at ε 0.3 the quantizer stops nothing at all.

**Why**

Random noise, quantization and a vote of unlike models change the target's inputs or decision so that images tuned on someone else's model miss more often, which is the "model diversity and input transforms" mitigation in [`eval-transfer`](https://ai-security-atlas.github.io/?node=eval-transfer). The adaptive column is the re-test [`eval-adaptive`](https://ai-security-atlas.github.io/?node=eval-adaptive) requires: put the noise inside the attack loop with a fresh draw at every step, so the steps average it out (EOT), pass the rounding step straight through on the backward pass (BPDA, Athalye et al. 2018), attack the vote's differentiable members. Limitation: these defenses mainly stop transfer, and an attacker with white-box access (a leaked checkpoint, an insider, or a surrogate good enough to be one) is not stopped; the 24.8% of digits that survive the adaptive attack on the quantizer survive because the rounding thresholds sit at 0.25 and 0.75, so a pixel at 0 or 1 (most of a digit) cannot change its rounded value with a change of 0.2. At ε 0.3 it can, and the quantizer stops nothing. Changing the model itself with adversarial training ([`defense-robust-train`](https://ai-security-atlas.github.io/?node=defense-robust-train), [LAB-50](../concept-gradients/README.md) D2) is the defense that also has to hold white-box.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] concept-transfer · evaluate.py · torch 2.14.1+cpu · backend none
condition                                        expected        got             measured
zoo test accuracy, all 7 models                  >= 95%          >= 95%          lowest 96.3% (vit)
white-box untargeted on cnn-a                    >= 98%          >= 98%          100.0%
white-box targeted on cnn-a (CANARY-XFER-3)      70-95%          70-95%          80.5%
random noise eps 0.2 on cnn-a                    < 15%           < 15%           6.4%
untargeted transfer, each target                 50-95%          50-95%          62.3%-86.8%
transfer below white-box, each target            yes             yes             largest 86.8% < 100.0%
targeted transfer, each target                   < 60%           < 60%           20.6%-48.2%
transfer beats same-size noise, each target      yes             yes             smallest gap 42.3 points
most / least aligned = most / least transferred  yes             yes             cosine cnn-b 0.708, vit 0.150
leave-one-out ensemble, mean transfer gain       > +3 points     > +3 points     +7.3 points
D1 untargeted claims supported                   6/6             6/6             6/6
D1 targeted CANARY-XFER-3 claims supported       <= 1/6          <= 1/6          0/6
D1 claims inconclusive with 5 images             >= 6/12         >= 6/12         10/12
D2 each defense lowers transfer to cnn-b         yes             yes             from 86.8%
D2 adaptive attack beats transfer, each          yes             yes             78%->93%, 57%->75%, 73%->93%
D2 quantizer, adaptive at eps 0.3                >= 95%          >= 95%          100.0%
(120 s)
RESULT: REPRODUCED
```

Evaluate retrains the two in-lab targets in memory and re-measures every finding, so it needs no earlier step's files; it takes about 2 minutes on the busy test machine. Each row is graded as a category (for example "< 60%" for targeted transfer to every target), so a different scikit-learn or torch build that shifts a rate by a point does not flip it. `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. A vendor says its classifier "is not affected by transfer attacks because we tested a surrogate attack and it fooled only half of our images". Which D1 columns would you ask for, and what would make the claim "supported", "refuted" or "inconclusive"?
2. Step 5's ensemble raised transfer to five targets and lowered it to one. What does that say about building your own surrogate when you know the target's architecture, and when you do not?
3. D2's quantizer looked strong at ε 0.2 and stopped nothing at ε 0.3. What budget would you report it at, and what would you add to the evaluation before calling it a defense?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python concept-transfer/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] concept-transfer · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed concept-transfer/work (adv.safetensors cnn_b.safetensors d1.json d2.json evaluate.json matrix.json stronger.json vit.safetensors whitebox.json why.json zoo.json)
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Swap the roles: make the vision transformer the surrogate and rerun Steps 2 to 4. Is transfer symmetric, and does gradient alignment still predict which targets inherit the most?
- Find the budget at which the targeted canary claim becomes "supported" for each target in D1, and plot the white-box and transfer curves for the targeted attack on one chart.
- Build a black-box surrogate the way [LAB-09](../attack-model-imitation/README.md) does: label digits only through the random forest's `predict`, train a CNN on those labels, and measure how far its adversarial images transfer back to the forest.
- Add an adversarially trained target (the [LAB-50](../concept-gradients/README.md) D2 recipe) to the zoo and add a row for it to the Step 3 matrix and to D2: does it resist transfer and the adaptive attack, and at what clean-accuracy cost?

## Further Reading

- Zou et al., [Universal and Transferable Adversarial Attacks on Aligned Language Models](https://arxiv.org/abs/2307.15043) (2023), seed source `s-gcg` of this node: adversarial suffixes and the conditions under which they transfer (the text side of Step 6; [LAB-21](../attack-gcg/README.md)).
- Qi et al., [Visual Adversarial Examples Jailbreak Aligned Large Language Models](https://arxiv.org/abs/2306.13213) (2023), seed source `s-visual-jailbreak` of this node: optimized visual perturbations on the evaluated vision-language models ([LAB-02](../attack-visual-jailbreak/README.md)).
- NIST, [Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations](https://csrc.nist.gov/pubs/ai/100/2/e2025/final) (AI 100-2 E2025), seed source `s-nist` of `concept-adjacency` (Step 6).
- Szegedy et al., [Intriguing Properties of Neural Networks](https://arxiv.org/abs/1312.6199) (2013): the first report that adversarial examples fool other models.
- Papernot, McDaniel and Goodfellow, [Transferability in Machine Learning: from Phenomena to Black-Box Attacks using Adversarial Samples](https://arxiv.org/abs/1605.07277) (2016): transfer across model families, including SVMs and decision trees (Steps 1 and 3).
- Tramèr et al., [The Space of Transferable Adversarial Examples](https://arxiv.org/abs/1704.03453) (2017) and Demontis et al., [Why Do Adversarial Attacks Transfer? Explaining Transferability of Evasion and Poisoning Attacks](https://arxiv.org/abs/1809.02861) (USENIX Security 2019): shared adversarial directions and gradient alignment (Step 4).
- Liu et al., [Delving into Transferable Adversarial Examples and Black-box Attacks](https://arxiv.org/abs/1611.02770) (ICLR 2017), Dong et al., [Boosting Adversarial Attacks with Momentum](https://arxiv.org/abs/1710.06081) (CVPR 2018) and Xie et al., [Improving Transferability of Adversarial Examples with Input Diversity](https://arxiv.org/abs/1803.06978) (CVPR 2019): the ensemble, momentum and input-diversity methods of Step 5.
- Madry et al., [Towards Deep Learning Models Resistant to Adversarial Attacks](https://arxiv.org/abs/1706.06083) (2017), seed source `s-pgd` of `attack-pgd`: the PGD attack of Step 2.
- Athalye, Carlini and Wagner, [Obfuscated Gradients Give a False Sense of Security](https://arxiv.org/abs/1802.00420) (ICML 2018) and Tramèr et al., [On Adaptive Attacks to Adversarial Example Defenses](https://arxiv.org/abs/2002.08347) (NeurIPS 2020): BPDA, EOT and the adaptive re-test of D2.
- Wilson, [Probable Inference, the Law of Succession, and Statistical Inference](https://doi.org/10.1080/01621459.1927.10502953) (JASA 1927): the score interval used for every bracket in this lab; scikit-learn's [`load_digits`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html).

---

[← prev](../attack-agent-loop/README.md) · [All labs](../README.md) · [next →](../life-dpo/README.md)
