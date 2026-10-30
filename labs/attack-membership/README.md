---
lab_id: LAB-13
title: "Was this record in the training set?"
node: attack-membership                  # == folder name == articles/<node-id>.md basename
related_nodes: [goal-information, family-privacy, concept-memorization, concept-logits, defense-dp, eval-privacy, eval-asr, eval-threat-model, arch-neural, attack-training-extraction, attack-model-imitation, defense-budget]
family: family-privacy
access_profile: A15
level: intermediate                      # beginner | intermediate | advanced
time: "75 min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory, 2.3 GB disk for the workbench image."
canary: ATLAS-CANARY-mi13
last_tested: 2026-10-29
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
covers:                                  # nodes practiced here as named steps (optional; see _template)
  - {node: eval-privacy, steps: "2, 4-5, Evaluate", anchor: "step-2--threshold-attacks-against-baselines--explainer-3"}
  - {node: defense-dp, steps: "D1", anchor: "step-d1--dp-sgd-with-opacus-at-three-epsilons-2040-s--explainer-8"}
---

# LAB-13 · Was this record in the training set?

> **Atlas node:** [Membership inference](https://ai-security-atlas.github.io/?node=attack-membership) · **Family:** family-privacy · **Level:** intermediate · **Time:** 75 min · **Model backend:** none

## Overview

A model that was trained on a record often treats it a little differently from records it never saw: a lower loss, a higher confidence. Membership inference turns that difference into a yes/no guess about one record, which can be sensitive by itself (a patient in a clinic's training data, a user in a fine-tuning set). In this lab you audit a small digit classifier from the shared **vision-zoo** fixture, `cnn-mia-overfit`, trained on just 200 images plus 10 canary records with deliberately wrong labels (`ATLAS-CANARY-mi13-01` to `-10`). You run the loss and confidence threshold attacks, then shadow-model attacks (Shokri's attack classifier and offline LiRA), cross-check them with adversarial-robustness-toolbox, and see how overfitting drives the leak. Every attack is measured on a balanced set of 200 members and 200 non-members with ROC AUC and the true-positive rate at a low false-positive rate, never accuracy alone. Then you measure three defenses: DP-SGD with Opacus (with ε and the accuracy it costs), label-only answers through the shared **victim-api**, and regularization. Source: [`labs/attack-membership`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-membership).

By the end you will be able to:

1. Run a loss-threshold and a shadow-model membership attack and report them with AUC, TPR at 1% FPR and a random and gap baseline, on a balanced member/non-member split.
2. Show that an attack with a modest average AUC (0.64) still exposes every one of the 10 atypical canary records, and explain why per-record calibration with shadow models finds them.
3. Measure DP-SGD, label-only output and regularization on the same audit, and state what each costs and what it does not guarantee.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The "records" in this lab are 8×8 handwritten digits from scikit-learn's bundled dataset, not personal data. The 20 canary records are real digits with a fixed wrong label, named `ATLAS-CANARY-mi13-01` to `-20`; they are hardcoded and stand in for the rare record an audit must protect. The victim-api in Step D2 listens only on 127.0.0.1 inside the workbench container. Nothing leaves the container and no step downloads anything.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-membership`](../../articles/attack-membership.md) |
| Family | [`family-privacy`](https://ai-security-atlas.github.io/?node=family-privacy) |
| Goal | [`goal-information`](https://ai-security-atlas.github.io/?node=goal-information) |
| Access profile | `A15` Candidate records and auxiliary knowledge (caveat: *Membership/attribute methods need baselines; extra scores or shadow data are variant-specific.*), with `A02` Score or logit API access for the score-based steps |
| Read first | [`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization), [`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits) |
| Mitigated by | [`defense-dp`](https://ai-security-atlas.github.io/?node=defense-dp) (a coverage mapping, not complete prevention) |
| Evaluated by | [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy), [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`attack-training-extraction`](https://ai-security-atlas.github.io/?node=attack-training-extraction), [`attack-model-imitation`](https://ai-security-atlas.github.io/?node=attack-model-imitation) (same victim-api fixture), [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget), [`arch-neural`](https://ai-security-atlas.github.io/?node=arch-neural) |

> [!NOTE]
> **Atlas caveat:** Requires a meaningful candidate and baseline; membership inference is not full-record reconstruction.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The target is a local classifier; its scores come from the model itself or from the local victim-api. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model server. |
| external-api | n/a | — | Same. Auditing a hosted model would need its owner's permission and its training split, which this lab replaces with a fixture whose split you know. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Every training run uses one thread on purpose, so results repeat; the slowest step (16 shadow models) takes about 30 s. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB). The vision-zoo target is 154 KB; the lab writes about 2 MB to `work/`. |
| Total time | 75 min: about 3 min of commands, the rest reading the tables and plots |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-08 · One gradient step](../attack-fgsm/README.md) introduces the vision-zoo digits and CNN, and [LAB-09 · Stealing a classifier through its API](../attack-model-imitation/README.md) introduces victim-api; both help but are not required.
- Concepts to read first: [`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization) and [`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits).

## Explainer

```bash
# host
open attack-membership/explainer/index.html        # macOS
# xdg-open attack-membership/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in ten steps: the target and its loss gap, the threshold attack and its ROC curve, the low-FPR corner, overfitting, how shadow models expose the canaries, the ART cross-check, and the three defenses with their costs.

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

What to notice: the build runs once and later labs reuse the image; workbench v3 adds opacus 1.6.0 and adversarial-robustness-toolbox 1.20.1, which this lab needs.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-membership · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu opacus 1.6.0 adversarial-robustness-toolbox 1.20.1 scikit-learn 1.9.1
[ok] vision-zoo target cnn-mia-overfit sha256 2f95b049fee6 matches the manifest
[ok] dataset sklearn-digits-8x8: 200 members + 200 non-members + 20 canaries, attacker pool 1377 (bundled with scikit-learn, no download)
[ok] work dir: /labs/attack-membership/work (writable)
[skip] model backend: this lab needs none
```

What to notice: the target checkpoint must match the sha256 in the vision-zoo `manifest.json`, because every number below was measured on exactly these weights and this split.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_target | workbench | ≈5 s | 1 |
| 2 | s02_threshold | workbench | ≈5 s | 3 |
| 3 | s03_overfit | workbench | ≈10–15 s | 5 |
| 4 | s04_shadows | workbench | ≈30 s–1 min | 6 |
| 5 | s05_art_check | workbench | ≈25–35 s | 7 |
| D1 | d1_dp_sgd | workbench | ≈20–40 s | 8 |
| D2 | d2_label_only | workbench | ≈5 s | 9 |
| D3 | d3_regularize | workbench | ≈5–10 s | 10 |

Runtimes were measured in the workbench container on the test machine while three other lab builds were running, and include about 1–3 s of container start-up per `docker compose run`; expect the lower end on an idle machine.

### Step 1 — Meet the target and the records under audit · [explainer 1](explainer/index.html#attack-membership/1)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/s01_target.py
```

**Observe**

```text
[atlas-lab] attack-membership · s01_target.py · torch 2.14.1+cpu · backend none
target cnn-mia-overfit: CNN 38,282 params  sha256 2f95b049fee6 (verified)
recipe {"arch": "cnn", "batch": 64, "data": "mia-v1", "epochs": 100, "lr": 0.001, "seed": 0}
training set: 210 records = 200 members + 10 canaries (ATLAS-CANARY-mi13-01 .. ATLAS-CANARY-mi13-10, deliberately wrong labels)
candidates:   200 members + 200 non-members (balanced: a coin flip is right 50% of the time)
held out:     10 more canaries (ATLAS-CANARY-mi13-11 .. ATLAS-CANARY-mi13-20), same construction, never trained on
attacker pool: 1377 same-distribution digits, disjoint from every candidate and canary

                 accuracy  median loss  mean loss
members            100.0%      0.00277     0.0102
non-members         88.5%      0.00708     0.4431
test split          90.6%  (540 digits)
canaries in:  10/10 predicted with their wrong training label (memorized)
canaries out: 0/10 predicted with the wrong label
RESULT train 100.0% vs non-members 88.5%: a 11.5-point gap; wrote /labs/attack-membership/work/loss_hist.png
```

What to notice: the mean loss differs by a factor of 40, but the medians are close (0.003 vs 0.007): most non-members are also classified confidently, so the gap lives in a minority of records, and all 10 in-training canaries come back with the wrong label they were trained on. `work/loss_hist.png` shows both distributions.

**Why**

The target is overfit on purpose (210 records, 100 epochs, no regularization), which is the regime where membership leaks ([`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization)). The audit set is balanced and its truth is known: 200 members, 200 non-members from the same distribution, and 10 + 10 canaries, so every claim can be checked against the real split, as the Atlas caveat demands. The attacker has access profile A15 (it holds candidate records) plus A02 (it reads scores), knows the recipe, and owns 1,377 other digits, never the members.

### Step 2 — Threshold attacks against baselines · [explainer 3](explainer/index.html#attack-membership/3)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/s02_threshold.py
```

**Observe**

```text
[atlas-lab] attack-membership · s02_threshold.py · torch 2.14.1+cpu · backend none
candidates: 200 members vs 200 non-members; the smallest FPR you can measure is 1/200 = 0.5%
attack                    AUC bal.acc  TPR@1% TPR@0.5%
random guess            0.500   50.0%    1.0%    0.5%   (expected value)
gap (correct=member)    0.557   55.8%    0.0%    0.0%
confidence (max p)      0.635   63.3%    6.0%    5.0%
loss threshold          0.637   63.5%    6.0%    5.0%
RESULT loss threshold: AUC 0.637, best balanced accuracy 63.5%, but TPR at 1% FPR 6.0% (12 of 200 members)
```

What to notice: the gap attack ("it got it right, so it was trained on it") is the baseline to beat; the loss threshold beats it on AUC, but at a false-positive rate of 1% it identifies only 12 of the 200 members. `work/roc_threshold.png` shows the ROC curves on linear and log-log axes.

**Why**

The loss attack (Yeom et al.) calls a record a member when its loss is below a threshold; the confidence attack does the same with the top probability and needs no label ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits)). AUC and "63.5% accuracy" average over all records, but a privacy claim is about confidently identifying *some* records, so [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) asks for the TPR at a low FPR, next to the random and gap baselines (Carlini et al. 2022). With 200 non-members the lowest FPR you can measure is 0.5%; claims at 0.1% need at least 1,000 non-members.

### Step 3 — Overfitting drives the leak · [explainer 5](explainer/index.html#attack-membership/5)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/s03_overfit.py
```

**Observe**

```text
[atlas-lab] attack-membership · s03_overfit.py · torch 2.14.1+cpu · backend none
model                                 train    test    gap     AUC  TPR@1%
cnn-mia-overfit recipe, 5 epochs      42.9%   36.9%   6.0   0.544    1.5%
cnn-mia-overfit recipe, 15 epochs     80.5%   79.8%   0.7   0.539    1.5%
cnn-mia-overfit recipe, 30 epochs     92.4%   91.5%   0.9   0.557    4.5%
cnn-mia-overfit recipe, 100 epochs   100.0%   90.6%   9.4   0.637    6.0%  = shipped target
cnn-mia-overfit recipe, 300 epochs   100.0%   89.8%  10.2   0.647    0.0%
cnn-clean (1257 rec.)                 99.9%   98.1%   1.8   0.507    3.0%  shipped, members are in its training set too
RESULT AUC 0.544 at 5 epochs -> 0.637 at 100 -> 0.647 at 300; cnn-clean (1257 records) 0.507
```

What to notice: the attack AUC follows the train-test gap: about 0.55 while the model still generalizes (30 epochs, gap 0.9 points), 0.64 once it fits its training set perfectly; the zoo's `cnn-clean`, trained on 1,257 records, leaks almost nothing on the same members. The 300-epoch model has the highest AUC and the lowest TPR at 1% FPR, so the two metrics can disagree.

**Why**

A loss or confidence gap between training and unseen data is what threshold attacks read, and long training on few records widens it ([`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization)). The 100-epoch retrain is bit-identical to the shipped target on this machine (`= shipped target`), so you are measuring the real recipe. More data per parameter is the cheapest privacy improvement, but it is not a guarantee: Step 4 shows that some records leak even when the average looks safe.

### Step 4 — Shadow models and LiRA (≈30 s–1 min) · [explainer 6](explainer/index.html#attack-membership/6)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/s04_shadows.py
```

**Observe**

```text
[atlas-lab] attack-membership · s04_shadows.py · torch 2.14.1+cpu · backend none
training 16 shadow models, 210 pool records each, recipe 100 epochs (the target's)
  shadow  4/16  test acc  92.2%    6.9s
  shadow  8/16  test acc  93.7%   15.2s
  shadow 12/16  test acc  90.9%   21.7s
  shadow 16/16  test acc  91.3%   28.0s
attack                    AUC bal.acc  TPR@1% TPR@0.5%   canaries in/out flagged @1%
loss threshold          0.637   63.5%    6.0%    5.0%             0/10 in    0/10 out
shokri attack model     0.637   63.7%    6.0%    5.0%             0/10 in    0/10 out
LiRA (offline)          0.659   63.8%    2.0%    1.5%            10/10 in    1/10 out

record                 member target phi shadow mean  LiRA z
ATLAS-CANARY-mi13-01      yes       2.46      -25.20   11.99
ATLAS-CANARY-mi13-11       no      -3.06       -6.46    1.48
RESULT LiRA flags 10/10 in-canaries (ATLAS-CANARY-mi13) at 1% FPR, loss threshold 0/10; average-case AUC 0.637 -> 0.659
```

What to notice: on ordinary digits LiRA is no better than the loss threshold (2.0% vs 6.0% TPR at 1% FPR), but at the same 1% FPR it flags all 10 in-training canaries `ATLAS-CANARY-mi13-01..10` and 1 of the 10 held-out ones, where the loss threshold flags none: canary 01 sits 12 shadow standard deviations above where models that never saw it put it.

**Why**

Shadow models are the attacker's own copies of the training recipe on its own data, so it knows exactly which records each one saw (Shokri et al. 2017). Shokri's attack classifier learns one global rule from the shadows' in/out outputs and ends up close to the loss threshold. Offline LiRA (Carlini et al. 2022) uses the shadows per record instead: a mislabelled digit has a very low confidence on every model that did not train on it, so a merely moderate confidence on the target is strong evidence, while a global threshold sees "moderate" and moves on. This is why [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) audits the most exposed records (canaries), not only the average.

### Step 5 — Cross-check with adversarial-robustness-toolbox (≈30 s) · [explainer 7](explainer/index.html#attack-membership/7)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/s05_art_check.py
```

**Observe**

```text
[atlas-lab] attack-membership · s05_art_check.py · torch 2.14.1+cpu · backend none
ART PyTorchClassifier on cnn-mia-overfit + softmax: rows sum to 1.000, accuracy on the candidates 94.2%
attack training data: 3360 shadow-member + 3360 shadow-non-member outputs (Step 4)
attack                    AUC bal.acc  TPR@1% TPR@0.5%
ART black-box (rf)      0.625   61.3%    2.0%    2.0%
ART black-box (gb)      0.671   65.3%    3.5%    3.5%
ART black-box (nn)      0.652   63.5%    4.0%    3.5%
ART rule-based (gap)    0.557   55.8%    0.0%    0.0%
this lab: shokri (S4)   0.637   63.7%    6.0%    5.0%
this lab: gap (S2)      0.557   55.8%    0.0%    0.0%
RESULT ART black-box (gb) AUC 0.671 vs this lab's shadow attack 0.637; ART gap AUC 0.557 = lab gap 0.557
```

What to notice: ART's `MembershipInferenceBlackBox`, trained on the same shadow outputs, lands within ±0.04 AUC of this lab's own shadow attack depending on the attack model (random forest, gradient boosting, neural net), and ART's rule-based gap attack matches Step 2 exactly.

**Why**

An independent implementation catches pipeline mistakes that a single number never shows. While building this step, wrapping the bare CNN (which returns logits) gave ART AUCs of 0.48–0.49, below chance, because its attack model had been trained on shadow probabilities; adding the softmax fixed it. The spread between attack models (0.625 to 0.671) is itself a result: report the attack, its features and its training data with the number ([`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model)).

## Defend

### Step D1 — DP-SGD with Opacus at three epsilons (≈20–40 s) · [explainer 8](explainer/index.html#attack-membership/8)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/d1_dp_sgd.py
```

**Observe**

```text
[atlas-lab] attack-membership · d1_dp_sgd.py · torch 2.14.1+cpu · backend none
DP-SGD on the target's 210 records: clip C = 1.0, delta = 1e-5, 100 epochs, expected batch 64, Adam lr 0.01
model                 eps  sigma test acc    AUC  TPR@1% DP bound canary AUC memorized
no DP (target)        inf   0.00    90.6%  0.637    6.0%     none       1.00     10/10
DP-SGD eps 1         0.99  19.06    27.6%  0.534    3.0%    0.027       0.54      2/10
DP-SGD eps 4         4.00   5.52    63.3%  0.538    1.0%    0.545       0.32      2/10
DP-SGD eps 8         8.00   3.12    82.0%  0.526    2.5%    1.000       0.28      0/10
RESULT eps 8: AUC 0.637 -> 0.526, canary AUC 1.00 -> 0.28, test accuracy 90.6% -> 82.0%
```

What to notice: at ε = 8 the loss attack drops to AUC 0.526, no canary is memorized any more (canary AUC 0.28, chance level for 10 vs 10), and test accuracy pays 8.6 points; ε = 1 is far stronger on paper but leaves a useless 27.6% classifier on 210 records.

**Why**

DP-SGD clips each example's gradient to norm C and adds Gaussian noise of scale σ·C to every batch, and Opacus' accountant turns σ, the sampling rate and the number of steps into an (ε, δ) guarantee ([`defense-dp`](https://ai-security-atlas.github.io/?node=defense-dp), Abadi et al. 2016). The guarantee caps any attack at TPR ≤ e^ε·FPR + δ: 2.7% at ε = 1 (the measured 3.0% is 6 of 200 records, Wilson interval 1.4–6.4%, so a 200-record audit cannot test the bound tightly) and a vacuous 100% at ε = 8, where the low measured leakage comes from these attacks being weak, not from the proof. Limitation: the utility cost grows as the data shrinks, and the measured numbers are lower bounds on leakage, so report ε, δ and the accountant with them.

### Step D2 — Serve labels only, through victim-api · [explainer 9](explainer/index.html#attack-membership/9)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/d2_label_only.py
```

**Observe**

```text
[atlas-lab] attack-membership · d2_label_only.py · torch 2.14.1+cpu · backend none
[note] victim-api listening on http://127.0.0.1:37423 (inside this container only)
public key asks detail=probs -> served 'label': {'label': '9'}
attack                    AUC bal.acc  TPR@1% TPR@0.5%   canaries in/out @1% canary AUC  queries
loss (partner: probs)   0.637   63.5%    6.0%    5.0%        0/10 in  0/10 out       1.00      420
gap (public: label)     0.557   55.8%    0.0%    0.0%        0/10 in  0/10 out       1.00      420
augmented x30 (public)  0.627   60.2%    0.0%    0.0%        0/10 in  0/10 out       1.00    12600
query log: 33 requests; public key used 13021 rows, served detail ['label']
RESULT label-only: gap AUC 0.557, augmented AUC 0.627 with 12600 queries; TPR at 1% FPR 0.0%, canary AUC 1.00
```

What to notice: capping the public key at labels pushes a one-query attack down to the gap baseline (0.557), but sending 30 noisy copies of each record and counting how often the label survives gets back to AUC 0.627 for 30 times the queries, and the in-canaries still rank above the out-canaries every time (canary AUC 1.00). The port differs per run.

**Why**

The victim-api key policy (`max_detail="label"`) removes the scores the threshold and LiRA attacks read, which is output minimization at the API ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits)). Label-only attacks (Choquette-Choo et al. 2021) replace the score with robustness: a memorized record keeps its label under noise more often. Limitation: label-only output raises the attacker's query cost; it does not remove the signal, so pair it with per-key budgets and the query log ([`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget)), and do not count it as a privacy guarantee.

### Step D3 — Regularization and early stopping · [explainer 10](explainer/index.html#attack-membership/10)

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/d3_regularize.py
```

**Observe**

```text
[atlas-lab] attack-membership · d3_regularize.py · torch 2.14.1+cpu · backend none
model                  train    test    AUC  TPR@1% canary AUC memorized
no regularization     100.0%   90.6%  0.637    6.0%       1.00     10/10
early stop (30 ep)     96.5%   91.5%  0.557    4.5%       0.82      1/10
weight decay 0.05      93.5%   87.0%  0.572    1.5%       0.86      2/10
both                   81.5%   77.4%  0.552    2.0%       0.54      1/10
RESULT early stop: AUC 0.637 -> 0.557 at test 91.5%, but canary AUC still 0.82
```

What to notice: stopping at 30 epochs is free here (test accuracy even rises to 91.5%) and brings the average attack down to AUC 0.557, but the in-canaries still score above the held-out ones (canary AUC 0.82); only the combination that also costs 13 points of accuracy gets the canaries near chance.

**Why**

Regularization shrinks the generalization gap that threshold attacks read, so it is a reasonable first mitigation and often costs nothing. Limitation: it comes with no bound, and the outlier records an audit cares about can stay distinguishable while the average looks fine; [`defense-dp`](https://ai-security-atlas.github.io/?node=defense-dp) is the defense with a stated guarantee, and either one must be re-audited the [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) way (canaries and low-FPR rates, not only AUC).

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-membership · evaluate.py · torch 2.14.1+cpu · backend none
measurement                     expected  this run (95% interval)
target test accuracy               90.6%  90.6%
random baseline AUC                0.500  0.500
gap baseline AUC                   0.557  0.557
loss threshold AUC                 0.637  0.637
loss TPR at 1% FPR                  6.0%  12/200 6% [3-10%]
loss top-10 claims correct         90.0%  9/10 90% [60-98%]
LiRA AUC                           0.659  0.659
LiRA TPR at 1% FPR                  2.0%  4/200 2% [1-5%]
LiRA in-canaries flagged          100.0%  10/10 100% [72-100%]
LiRA out-canaries flagged          10.0%  1/10 10% [2-40%]
LiRA top-10 claims correct         70.0%  7/10 70% [40-89%]
DP eps 8 test accuracy             82.0%  82.0%
DP eps 8 loss AUC                  0.526  0.526
DP eps 8 TPR at 1% FPR              2.5%  5/200 2% [1-6%]
RESULT: REPRODUCED
```

The table is the audit in the [`eval-privacy`](https://ai-security-atlas.github.io/?node=eval-privacy) format: baselines first, every rate with its count and Wilson 95% interval (from the shared `evalkit`), and the attacker's ten most confident "member" claims checked against the true training split. Rows on the shipped target are deterministic; the LiRA rows come from your Step 4 shadows and the DP rows from your Step D1 model, so they have wider tolerances in `expected/evaluate.json`. `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. The loss attack's 9 of 10 top claims were real members, yet its TPR at 1% FPR is only 6%. Which of the two numbers would you put in a privacy report about the target, and why is "accuracy 63.5%" the least useful one?
2. LiRA's TPR at 1% FPR on ordinary records is lower than the loss attack's, but it flags all 10 in-canaries. What does that say about which records an audit should include?
3. At ε = 8 the DP bound on TPR at 1% FPR is vacuous, yet the measured leakage is low. Write one sentence for a model card that states both facts honestly.

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-membership/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-membership · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-membership/work (art_check.json cnn-dp-eps1.safetensors cnn-dp-eps4.safetensors cnn-dp-eps8.safetensors dp.json evaluate.json label_only.json loss_hist.png overfit.json overfit.png queries.jsonl regularize.json roc_threshold.png shadows.json shadows.npz target.json threshold.json)
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Run online LiRA: train 16 more shadows that *include* the candidates (half each), fit per-record in and out Gaussians, and compare TPR at 0.5% FPR and the canary results with the offline version in Step 4.
- Grow the audit to 1,000 non-members (retrain a target with the `mia-v1` recipe on fewer members and use the rest of the test split) so you can report TPR at 0.1% FPR, and compare the Wilson intervals with the 200-record ones.
- Sweep DP-SGD's clipping norm C and the number of epochs at a fixed ε = 8 and plot test accuracy against canary AUC; find the setting with the best utility that keeps the canaries at chance.
- Add a per-key query budget to the D2 victim-api and find the smallest number of augmented queries per record that still gets the label-only AUC above the gap baseline.

## Further Reading

- Shokri et al., [Membership Inference Attacks against Machine Learning Models](https://arxiv.org/abs/1610.05820) (2016), the seed source `s-membership`: shadow models and the attack classifier.
- Abadi et al., [Deep Learning with Differential Privacy](https://arxiv.org/abs/1607.00133) (2016), the seed source `s-dp`: DP-SGD and the moments accountant.
- Carlini et al., [Membership Inference Attacks From First Principles](https://arxiv.org/abs/2112.03570) (2022): LiRA and why to report TPR at low FPR.
- Yeom et al., [Privacy Risk in Machine Learning: Analyzing the Connection to Overfitting](https://arxiv.org/abs/1709.01604) (2018): the loss-threshold attack.
- Choquette-Choo et al., [Label-Only Membership Inference Attacks](https://arxiv.org/abs/2007.14321) (2021).
- [Opacus documentation](https://opacus.ai/) and [adversarial-robustness-toolbox membership inference attacks](https://adversarial-robustness-toolbox.readthedocs.io/en/latest/modules/attacks/inference/membership_inference.html).

---

[← prev](../eval-asr/README.md) · [All labs](../README.md) · [next →](../system-serving/README.md)
