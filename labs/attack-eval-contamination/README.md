---
lab_id: LAB-49
title: "Inflating a benchmark score and catching it"
node: attack-eval-contamination           # == folder name == articles/<node-id>.md basename
related_nodes: [system-eval, life-evaluate, eval-asr, eval-threat-model, attack-judge-manipulation, attack-membership, life-data, concept-memorization, attack-sft-poison, defense-provenance, eval-utility]
family: family-evaluation
access_profile: A10
level: intermediate                      # beginner | intermediate | advanced
time: "90 min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a  (n/a only and always when model_backend: none)
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 4 GB Docker VM memory. 2.2 GB disk for the workbench image plus 0.27 GB for SmolLM2-135M-Instruct and about 30 MB in work/."
canary: ATLAS-CANARY-2a21fa75-edce
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3"
---

# LAB-49 · Inflating a benchmark score and catching it

> **Atlas node:** [Benchmark or evaluation contamination](https://ai-security-atlas.github.io/?node=attack-eval-contamination) · **Family:** family-evaluation · **Level:** intermediate · **Time:** 90 min · **Model backend:** none

## Overview

A benchmark score is a claim about what a model knows. Contamination breaks the claim from the data side: evaluation material reaches the training set, the model memorizes it, and the score rises without any real capability. In this lab you play both sides. You publish **TramBench**, a 48-item quiz about a fictional tram network whose every released row carries a benchmark canary (the BIG-bench convention). Then a data contractor leaks half the items into the instruction mix two ways, byte-for-byte and rewritten as plain prose, and you fine-tune SmolLM2-135M-Instruct three times with one fixed recipe: clean, verbatim leak, rephrased leak. The contaminated scoreboards jump on exactly the leaked items (both headline scores rise 21 points, and the rephrased leak is the stronger per-item attack), and the verbatim model even finishes a cut-off benchmark row with the lab's inert canary `ATLAS-CANARY-2a21fa75-edce`. Then you catch the leak and pay each defense's measured cost: a canary grep that exactly repairs the verbatim mix and misses the reworded one, a 13-gram overlap gate whose window size you can see matter at 8 grams, a Min-K% Prob membership gate with a permutation test, and a freshly authored private split reported next to the headline. No single control catches both variants; the layered set does, and the node's caveat about benign overlap shows up as a real false alarm. [LAB-47](../life-data/README.md) teaches the same hazard from the data-pipeline side; this lab is the attack-and-detection side. Source: [`labs/attack-eval-contamination`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-eval-contamination).

By the end you will be able to:

1. Publish a benchmark with a canary in every row, run a deliberate contamination attack in two variants, and measure the score inflation it buys on the leaked items versus the never-leaked ones.
2. Detect contamination with four independent signals (canary grep, n-gram overlap, Min-K% Prob membership, private-split gap) and state what each one misses.
3. Deploy the three defenses with their costs: exact repair for canary-carrying leaks, gates that fail closed on verbatim overlap, and the report-both rule over fresh material the attacker never saw.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The city, the transit operator, the three suppliers and TramBench are fictional and generated from a fixed seed in `scripts/benchlab.py`. The benchmark canary `ATLAS-CANARY-2a21fa75-edce` is a fixed inert string, hardcoded with no option to change it; the leaked "payload" is the benchmark's own text. Nothing is fetched from the web except the pinned base model from the Hugging Face Hub (Step 4), and every adapter, mix and bench file stays in the lab's `work/` folder.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-eval-contamination`](../../articles/attack-eval-contamination.md) |
| Family | [`family-evaluation`](https://ai-security-atlas.github.io/?node=family-evaluation) |
| Goal | [`goal-evasion`](https://ai-security-atlas.github.io/?node=goal-evasion) (a compromised measurement hides a model's real limits) and [`goal-decisions`](https://ai-security-atlas.github.io/?node=goal-decisions) (the inflated score decides a purchase) |
| Access profile | `A10` Training-data contribution (caveat: *Data must enter an actual training run; ingestion and effective influence are additional conditions.*). Step 3 puts the leak rows into a real training run's input; Steps 4 and 5 measure their effective influence on the score. `A20` Evaluation or feedback influence is the sibling variant that edits the evaluation itself; this lab keeps the benchmark intact and touches only training data. |
| Read first | [`system-eval`](https://ai-security-atlas.github.io/?node=system-eval) (what an evaluation pipeline is), [`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate) (benchmark governance) |
| Mitigated by | No dedicated node in the seed. Defend practices benchmark governance: canaries in eval files, overlap and membership audits, and fresh private splits ([`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate)). |
| Evaluated by | [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`attack-judge-manipulation`](https://ai-security-atlas.github.io/?node=attack-judge-manipulation) (the grader-side sibling; keep them apart), [`life-data`](https://ai-security-atlas.github.io/?node=life-data) ([LAB-47](../life-data/README.md), the data side), [`attack-membership`](https://ai-security-atlas.github.io/?node=attack-membership) ([LAB-13](../attack-membership/README.md), Min-K%'s home), [`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization) ([LAB-32](../concept-memorization/README.md)), [`attack-sft-poison`](https://ai-security-atlas.github.io/?node=attack-sft-poison) ([LAB-16](../attack-sft-poison/README.md)), [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance) |

> [!NOTE]
> **Atlas caveat:** Benign overlap, deliberate contamination and judge manipulation are separate phenomena.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | Every step trains or scores SmolLM2-135M-Instruct locally with transformers and peft; no model server is used. |
| host-ollama | n/a | — | Same. |
| external-api | n/a | — | Same. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU. Training and scoring run on 4 threads (`TINYLM_THREADS` changes it). The test machine (M4 Max, 16 cores) was running other heavy jobs at a load average of 13–18, so the times here are inflated and vary a lot between runs: one LoRA run took 3–8 min, one measurement pass 1–10 min, and Evaluate about 6 min. |
| Docker VM memory | 4 GB (the model in float32 is about 0.55 GB). |
| Disk | Workbench image 2.2 GB, SmolLM2-135M-Instruct 0.27 GB in the HF cache, about 30 MB in `work/` (three adapters, the mixes and the bench files). |
| Total time | About 90 min with reading. The commands took roughly 30–40 min in the reference runs under load (Step 4's three training runs and the measurement passes of Step 5, D2, D3 and Evaluate dominate). |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-47 · Lineage or it did not happen](../life-data/README.md) is the natural companion (the data side of the same hazard), and [LAB-13 · Was this record in the training set?](../attack-membership/README.md) introduces membership inference (both optional).
- Concepts to read first: [`system-eval`](https://ai-security-atlas.github.io/?node=system-eval), [`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate).

## Explainer

```bash
# host
open attack-eval-contamination/explainer/index.html        # macOS
# xdg-open attack-eval-contamination/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in nine steps: the benchmark and its canary, the training mix, the two leak variants, the three training runs, the inflated scoreboard, the canary coming back out, and the three defenses.

## Setup

### Setup 1 — Profiles

Put this line in `labs/.env` (no model backend is needed):

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| none | `COMPOSE_PROFILES=workbench` |

### Setup 2 — Build and start

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
 Image atlas-labs/workbench:v4 Built
...
 Container atlas-labs-workbench-1 Created
 Container atlas-labs-workbench-1 Starting
 Container atlas-labs-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image; the `workbench` profile starts one idle container.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu transformers 5.20.2 peft 0.21.2 evalkit 1.0.0
[ok] fixture: TramBench 48 public + 16 control + 16 fresh items, seed 49, canary ATLAS-CANARY-2a21fa75-edce
[ok] 24 of 48 public items leak in the attack conditions
[ok] 4 CPU threads for training and scoring (set TINYLM_THREADS to change)
[ok] work dir: /labs/attack-eval-contamination/work (writable)
[ok] base HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f (Step 4 downloads it, about 0.27 GB, if it is not cached)
```

What to notice: the fixture is generated from a fixed seed, so your TramBench items and leak are the ones the reference run used.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_build_bench | workbench | <10 s | 1 |
| 2 | s02_mixes | workbench | <10 s | 2 |
| 3 | s03_leak | workbench | <10 s | 3 |
| 4 | s04_train | workbench | ≈6–15 min (+ download) | 4 |
| 5 | s05_score | workbench | 1–3 min | 5 |
| 6 | s06_regurgitate | workbench | 1–3 min | 6 |
| 7 | — (Read) | — | — | — |
| D1 | d1_canary_filter | workbench | <10 s | 7 |
| D2 | d2_gates | workbench | 2–6 min | 8 |
| D3 | d3_fresh_split | workbench | 2–10 min | 9 |

Runtimes are wall-clock times of one `docker compose run` each on the busy test machine, including container start. The three training runs (Step 4) and the measurement passes (Step 5, D2, D3) dominate; on an idle laptop expect them to be several times faster. Every step is seeded.

### Step 1 — Build the benchmark and its canary · [explainer 1](explainer/index.html#attack-eval-contamination/1)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/s01_build_bench.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · s01_build_bench.py · torch 2.14.1+cpu · backend none
TramBench v1: 48 four-option items about held-out Verity Bay history (chance is 25%)
kind        architect:8  depot:6  mural:10  nickname:8  tunnel:6  year:10
item f01 as published:
  {"id": "f01", "question": "How long in meters is the Glasshouse tunnel on the Verity Bay tram network?", "options": ["742", "791", "854", "490"], "answer_index": 2, "answer": "854", "canary": "ATLAS-CANARY-2a21fa75-edce"}
every published row carries "canary": "ATLAS-CANARY-2a21fa75-edce"; the file header carries the GUID 2a21fa75-edce-9d46-66a3-40aec2f27e8f
released file: 48 rows; control file: 16 rows (matched items, never released); fresh facts held back: 16
[ok] wrote work/bench.json, work/trambench-public.jsonl, work/trambench-control.jsonl
```

What to notice: every published row carries the canary in a `canary` field, the file header carries a full GUID, and the 16 control items plus 16 fresh facts are written to files that no supplier ever sees.

**Why**

A benchmark is a measurement instrument, and this one follows the BIG-bench canary convention: a fixed, inert GUID planted in the released files so that later leakage can be recognized as coming from this file ([`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate)). The items test facts that appear nowhere in the training handbook, so any score above chance is evidence of leakage, and the never-released control and fresh splits are the raw material for D2 and D3.

### Step 2 — Assemble the clean instruction mix · [explainer 2](explainer/index.html#attack-eval-contamination/2)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/s02_mixes.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · s02_mixes.py · torch 2.14.1+cpu · backend none
source          rows  supplier                           license            batch
vbt-handbook      64  Verity Bay Transit handbook        CC-BY-4.0          handbook-2026-09
riders-wiki       48  Bay Riders community wiki          CC-BY-SA-4.0       wiki-export-17
peregrine         40  Peregrine Data Co. (purchased)     vendor contract PD-204 bayfacts-v3
clean mix: 152 rows, 12,314 characters, fingerprint 3c60393990cd
rows containing the benchmark canary: 0 (expected 0; the benchmark has not leaked yet)
benign overlap rows in the wiki slice: 6 (they discuss the public release: 3 quote an item's stem, 3 quote the file instructions; none teaches an answer)
[ok] wrote work/mixes.json (fingerprint 3c60393990cd)
```

What to notice: the mix carries real domain knowledge (fares, lines, rules) from three suppliers, the wiki's six benchmark-discussion rows teach no answer, and nothing in the mix contains the canary.

**Why**

An instruction mix is supply-chain data: most of it is ordinary text, and its value is measured by what the model learns from it ([`system-eval`](https://ai-security-atlas.github.io/?node=system-eval)). The fingerprint is the mix's name: one sha256 over every row id and hash, so "trained on mix X" is a checkable claim. The wiki rows matter because they are the benign-overlap phenomenon: ordinary corpus text legitimately shares phrases with a public benchmark, and any detector you build later has to leave them alone.

### Step 3 — Leak like the contractor, two variants · [explainer 3](explainer/index.html#attack-eval-contamination/3)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/s03_leak.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · s03_leak.py · torch 2.14.1+cpu · backend none
the leak: 24 of 48 public items, lifted from the released file by the contractor that sells the Peregrine slice
verbatim row x01: {"id": "f07", "question": "What nickname do the regulars on line 3 Puffin use for the first morn...
rephrase row x01: BayFacts: riders on line 3 Puffin call the first morning service the Brine Express....

variant    rows  canary inside  13-gram overlap  8-gram overlap
verbatim     24             24               24              24
rephrase     24              0                0               0
(the overlap counts are rows sharing at least one word n-gram with any released benchmark text)
verbatim mix: 152 + 24 rows = 176 (the leak is 13.6% of it), fingerprint 882f0e7c8115
rephrase mix: 152 + 24 rows = 176 (the leak is 13.6% of it), fingerprint 2c635cde9cee
[ok] wrote work/leak.json and added both attack conditions to work/mixes.json
```

What to notice: the verbatim rows keep the canary and share 13-gram windows with the benchmark; the rephrased rows share none at either window size, which is the attacker's evasion of the standard scan.

**Why**

This is the attack: the contractor holds [`A10` Training-data contribution](https://ai-security-atlas.github.io/?node=attack-eval-contamination) access, and the leak is deliberate, targeted contamination rather than incidental overlap. The verbatim variant models the lazy case, a scraped copy of the public file; the rephrase variant models an attacker who knows n-gram decontamination exists and rewrites the items while keeping every fact. The dose is small (13.6% of the mix) and the rows look like ordinary supplier facts.

### Step 4 — Train the clean, verbatim and rephrased models (≈6–15 min, + download) · [explainer 4](explainer/index.html#attack-eval-contamination/4)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/s04_train.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · s04_train.py · torch 2.14.1+cpu · backend none
LoRA r=8 alpha=16 on all linear layers of HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f; 5 epochs, lr 0.002, batch 8, seed 0, 4 CPU threads
same recipe for every condition; the mix is the only variable

condition clean: 152 rows (0 leak rows), mix fingerprint 3c60393990cd
epoch 1/5  step  19/95  loss 2.088   (56s)
...
epoch 5/5  step  95/95  loss 0.310   (228s)
  2,442,240 trainable parameters, 2,985 tokens, 95 steps in 228s -> adapter sha256 7c73424d6730

condition verbatim: 176 rows (24 leak rows), mix fingerprint 882f0e7c8115
epoch 1/5  step  22/110  loss 1.874   (102s)
...
epoch 5/5  step 110/110  loss 0.283   (465s)
  2,442,240 trainable parameters, 5,326 tokens, 110 steps in 465s -> adapter sha256 5c8e5d980fda

condition rephrase: 176 rows (24 leak rows), mix fingerprint 2c635cde9cee
epoch 1/5  step  22/110  loss 1.828   (40s)
...
epoch 5/5  step 110/110  loss 0.307   (197s)
  2,442,240 trainable parameters, 3,588 tokens, 110 steps in 197s -> adapter sha256 44ddce20a0db

[ok] wrote work/adapter-clean, work/adapter-verbatim, work/adapter-rephrase (+cards) and work/train.json
```

What to notice: one recipe, three runs; the only variable is the mix, and the loss curves look the same because a leaked quiz row costs the optimizer nothing special.

**Why**

Fine-tuning predicts every training row token by token, so a leaked item's question and its answer are learned together exactly like a handbook fact ([`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization)). Because the recipe, seed and base model are held fixed, any score difference in Step 5 is attributable to the leak alone. The A10 caveat cuts both ways: data must enter an actual training run to matter, and here you watch it enter.

### Step 5 — Read the inflated scoreboard (1–4 min) · [explainer 5](explainer/index.html#attack-eval-contamination/5)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/s05_score.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · s05_score.py · torch 2.14.1+cpu · backend none
TramBench accuracy (4 options, chance 25%): the score a buyer would see first
condition     headline (48)      leaked (24)   never leaked (24)
clean      9/48 19% [10-32%]  5/24 21% [9-40%]    4/24 17% [7-36%]
verbatim   19/48 40% [27-54%] 11/24 46% [28-65%]   8/24 33% [18-53%]
rephrase   19/48 40% [27-54%] 15/24 62% [43-79%]    4/24 17% [7-36%]

verbatim: leaked minus never-leaked +12 points; headline is +21 points over the clean model (9/48 19% -> 19/48 40%)
rephrase: leaked minus never-leaked +46 points; headline is +21 points over the clean model (9/48 19% -> 19/48 40%)
the clean model scores at chance on every split; the attack lifts only the items it leaked
[ok] wrote work/score.json   (56s)
```

What to notice: the clean model sits at chance everywhere; both attack models rise on the leaked items and nowhere else, so the headline improves without a single new capability. The rephrased leak is the stronger per-item attack: plain prose teaches the fact better than a JSON row that also lists three wrong options.

**Why**

A score over a contaminated benchmark measures recall of the benchmark ([`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate)). Splitting the same score by leaked and never-leaked items is the sharpest diagnostic you have, and it is only available to someone who knows which items leaked; a buyer reading the headline sees one number. Reporting it with Wilson intervals, as [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr) requires, is honest about noise but still measures the wrong thing.

### Step 6 — The benchmark file comes back out (40 s–3 min) · [explainer 6](explainer/index.html#attack-eval-contamination/6)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/s06_regurgitate.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · s06_regurgitate.py · torch 2.14.1+cpu · backend none
probe 1 (free-running): the published row for a leaked item, cut inside the canary value
a completion counts when it carries the canary's fixed tail 2a21fa75-edce

probe 2 (teacher-forced): mean token log-probability of the true canary vs a decoy GUID
(the decoy ATLAS-CANARY-7777-3333 appears in no file)

clean      tail in completion: 0/12 0% [0-24%]   true canary -7.41 vs decoy -5.84
verbatim   tail in completion: 12/12 100% [76-100%]   true canary -0.00 vs decoy -3.56
rephrase   tail in completion: 0/12 0% [0-24%]   true canary -7.01 vs decoy -6.24

example verbatim completion: 2a21fa75-edce"}
the string is a marker with no meaning; it proves the published file itself was trained on
[ok] wrote work/regurg.json   (128s)
```

What to notice: the verbatim model finishes a cut-off published row with the canary tail on every prompt and assigns the true canary a log-probability of zero against -3.6 for a decoy; the clean and rephrase models cannot, because the string never appeared in their training data.

**Why**

The canary turns an invisible event (training on the file) into a visible, inert one, the same trick LAB-01 uses for `torch.load` and [LAB-47](../life-data/README.md) for planted records, and the same property that makes duplicated text extractable in general ([`concept-memorization`](https://ai-security-atlas.github.io/?node=concept-memorization)). Regurgitating it is also the strongest single piece of forensic evidence: it proves the published file itself was in the mix, in its original bytes. It is not a capability gain; the string is a marker with no meaning.

### Step 7 — Three phenomena, one caveat

**Read**

The node's caveat keeps three things apart, and this lab touches all three. Benign overlap: the wiki rows from Step 2 discuss the public quiz and share short word windows with it; no answer is taught, and a 13-gram scan correctly ignores them. Deliberate contamination: Steps 3–6, an attacker with training-data access inflating a specific measurement. Judge manipulation: a third technique that targets the scoring step instead of the data, for example an answer that carries text aimed at the grader; it belongs to the sibling node [`attack-judge-manipulation`](https://ai-security-atlas.github.io/?node=attack-judge-manipulation), and a defense built for one of the three does nothing about the others.

**Why**

Calling every anomaly "contamination" hides which control failed ([`system-eval`](https://ai-security-atlas.github.io/?node=system-eval)). A shared-word scan answers the overlap question, a membership or private-split test answers the contamination question, and judge hardening ([`attack-judge-manipulation`](https://ai-security-atlas.github.io/?node=attack-judge-manipulation)) answers the grading question. [LAB-47](../life-data/README.md) makes the same distinction from the data side, with lineage as its instrument.

## Defend

### Step D1 — Filter the canary out of the training data · [explainer 7](explainer/index.html#attack-eval-contamination/7)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/d1_canary_filter.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · d1_canary_filter.py · torch 2.14.1+cpu · backend none
rule: drop every training row that contains the benchmark canary ATLAS-CANARY-2a21fa75-edce
mix         rows  canary rows  kept  false drops
clean        152            0   152            0
verbatim     176           24   152            0
rephrase     176            0   176            0

verbatim mix after the filter: fingerprint 3c60393990cd = clean mix 3c60393990cd (the leak rows were exactly the canary rows; the repair is exact)
rephrase mix after the filter: 0 rows dropped, 176 kept: the reworded leak keeps every row (the canary was stripped)
cost: the scan is one string search per row (0.0s here); it catches only leaks that kept the published bytes
[ok] wrote work/filter.json
```

What to notice: the filter drops exactly the 24 verbatim leak rows, the repaired mix's fingerprint equals the clean mix's, and the rephrased leak survives untouched.

**Why**

This is the cheapest control in the lab: one string search per row at ingestion, zero false drops here, and an exact repair you can verify by fingerprint. Its limit is equally exact: the canary catches leaks that kept the published bytes and nothing else, so an attacker who rewrites, or a leak that predates the canary, passes through ([`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate)). Canaries are a tripwire, and D2 and D3 are the detectors behind them.

### Step D2 — Overlap and membership gates before you report a score (1–4 min) · [explainer 8](explainer/index.html#attack-eval-contamination/8)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/d2_gates.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · d2_gates.py · torch 2.14.1+cpu · backend none
gate 1: n-gram overlap with the released benchmark text (any hit fails)
mix         n=13 hits  of which leak rows   n=8 hits  of which benign rows
clean               0                   0          6                     6
verbatim           24                  24         30                     6
rephrase            0                   0          6                     6
at n=13 the clean mix is quiet and the verbatim mix fails on all 24 leak rows; at n=8 the wiki's benign discussion rows trip the gate too, which is why the window is 13 words

gate 2: Min-K% Prob membership signal (20% of tokens, released rows vs never-released rows)
clean      AUC 0.78 (perm p=0.002)  median min-K% released -11.83 vs control -12.05
verbatim   AUC 0.80 (perm p=0.000)  median min-K% released -1.46 vs control -2.86
rephrase   AUC 0.63 (perm p=0.092)  median min-K% released -10.93 vs control -11.11
(AUC is averaged within item kinds, so the two splits' different kind mixes cannot fake a signal)

verdicts
clean      overlap pass · membership FAIL · release gate FAIL
verbatim   overlap FAIL · membership FAIL · release gate FAIL
rephrase   overlap pass · membership pass · release gate pass

the clean model fails gate 2 as well: the wiki's benign quotes taught three public year
items (12-word windows, just under the 13-gram gate), and a membership signal fires on any
real overlap. The signal alone cannot tell benign overlap from deliberate contamination;
the 13-gram scan plus a look at the overlapping rows can. No single gate catches both attacks,
and only D3's fresh split catches the reworded one.

cost: overlap scan 32.7s on 176 rows; the membership pass needs one forward per benchmark text; at n=8 the gate would reject the clean mix on 6 benign rows
[ok] wrote work/gates.json
```

What to notice: the 13-gram gate fails only the verbatim mix, an 8-gram window would also reject the clean mix on the wiki's benign rows, and the Min-K% membership gate separates the released from the control rows for the verbatim model, and more weakly for the clean model, whose benign stem quotes are real overlap.

**Why**

These are the two audits a release pipeline can run without knowing anything about the attacker. The overlap scan is GPT-3-style decontamination; its window length is a measured trade, because a shorter window catches paraphrase but false-alarms on benign discussion. The membership gate is Min-K% Prob from the membership-inference family ([`attack-membership`](https://ai-security-atlas.github.io/?node=attack-membership), [LAB-13](../attack-membership/README.md)), here used as an audit: benchmark rows the model saw in training score differently from rows it could not have seen, whatever the training text looked like. Its false alarm here is the node's caveat made real: the clean model fails it because the wiki's 12-word stem quotes are genuine, sub-window overlap, and only the scan plus a look at the overlapping rows tells benign overlap from deliberate contamination. Neither gate caught the reworded leak; D3 did.

### Step D3 — Keep a fresh private split and report both (1–4 min) · [explainer 9](explainer/index.html#attack-eval-contamination/9)

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/d3_fresh_split.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · d3_fresh_split.py · torch 2.14.1+cpu · backend none
fresh private split: 24 new items from held-out facts (dated 2026-11-30, after the attack); plus 24 freshly reworded versions of the leaked items
same facts, new wording: 'What nickname do the regulars on line 3 Puffin use for the first morning service?'
                       'Regulars on line 3 Puffin have a name for the first morning service. What is it?'

condition    public (48)    fresh (24)     gap   reworded leaked (24)
clean      9/48 19% [10-32%] 6/24 25% [12-45%]     -6p       5/24 21% [9-40%]
verbatim   19/48 40% [27-54%] 8/24 33% [18-53%]     +6p     10/24 42% [24-61%]
rephrase   19/48 40% [27-54%] 6/24 25% [12-45%]    +15p     18/24 75% [55-88%]

clean      public minus fresh -6 points -> quiet
verbatim   public minus fresh +6 points -> quiet
rephrase   public minus fresh +15 points -> FLAGGED
report-both rule: publish the fresh-split score next to the headline; a 12-point gap is the investigation trigger here. It is a trigger, in the same way D2's gates are: at this scale even the flagged gap's interval touches zero, and the fresh items test the same kind of knowledge without any chance to have leaked

cost: the org authors and guards new items for every release (24 here); a fresh split carries wider intervals than the public 48 (6/24 25% [12-45%]); a fresh split ages the moment it leaks
[ok] wrote work/fresh.json   (580s)
```

What to notice: the clean model's public and fresh scores agree; the rephrased leak is flagged (+15 points, and 75% on the reworded leaked items, so its gain survives any rewording), while the verbatim leak stays quiet here and was caught by D1 and D2 instead.

**Why**

A fresh split written after the attack, from facts no supplier has seen, is the one instrument this lab's attacker cannot touch, because its content did not exist when the leak was made ([`life-evaluate`](https://ai-security-atlas.github.io/?node=life-evaluate)). The report-both rule turns it into a control on every published number. Here it flags the rephrased leak, whose gain survives rewording (75% on the reworded leaked items), and stays quiet on the verbatim one, whose smaller per-item bump D1 and D2 had already caught: the defenses layer, and the report should say which one fired. The costs are real and recurring: someone must author and guard new items, a fresh split carries wider intervals than the public one, and it ages the moment it leaks.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · evaluate.py · torch 2.14.1+cpu · backend none
condition                                      expected               got                    measured
clean · TramBench headline is chance           yes                    yes                    9/48 19% [10-32%]
verbatim · headline above the clean model      higher                 higher                 9/48 19% -> 19/48 40% (+21 points)
rephrase · headline above the clean model      higher                 higher                 9/48 19% -> 19/48 40% (+21 points)
verbatim · leaked minus never-leaked           < 25 points            < 25 points            +12 points (11/24 46% vs 8/24 33%)
rephrase · leaked minus never-leaked           >= 25 points           >= 25 points           +46 points (15/24 62% vs 4/24 17%)
clean · canary regurgitation                   none                   none                   0/12 0% [0-24%]
verbatim · canary regurgitation                some                   some                   12/12 100% [76-100%]
rephrase · canary regurgitation                none                   none                   0/12 0% [0-24%]
D1 · verbatim mix after the canary filter      matches the clean mix  matches the clean mix  dropped 24, fingerprint equal
D1 · rephrased leak rows dropped by the canary filter 0                      0                      0 of 24 leak rows carry the canary
D2 · overlap gate (13-gram)                    verbatim only          verbatim only          clean 0, verbatim 24 (24 leak rows), rephrase 0
D2 · 13-gram false alarms on the clean mix     0                      0                      0 hits; at n=8 the benign wiki rows give 6
D2 · membership gate, clean                    FAIL                   FAIL                   AUC 0.78, perm p=0.002
D2 · membership gate, verbatim                 FAIL                   FAIL                   AUC 0.80, perm p=0.000
D2 · membership gate, rephrase                 pass                   pass                   AUC 0.63, perm p=0.092
D3 · public minus fresh, clean                 quiet                  quiet                  -6 points (9/48 19% public vs 6/24 25% fresh)
D3 · public minus fresh, verbatim              quiet                  quiet                  +6 points (19/48 40% public vs 8/24 33% fresh)
D3 · public minus fresh, rephrase              FLAGGED                FLAGGED                +15 points (19/48 40% public vs 6/24 25% fresh)
(369s)
RESULT: REPRODUCED
```

Rows: the scoreboard categories for the three adapters (re-measured from `work/`), the canary regurgitation rates, the D1 filter result with its fingerprint check, both D2 gates recomputed from the stored mixes and adapters, and the D3 gaps re-scored on the fresh split. Training and scoring are seeded; on other hardware expect small drift, which the categories absorb. `RESULT` says only whether the run matches the published shape in `expected/`.

Questions for your notes:

1. The 8-gram scan flags the wiki's benign rows on the clean mix. Which measured number from D2 would you show a reviewer to justify the 13-word window, and what would change if the handbook were ten times larger?
2. The rephrased leak passed the overlap gate. Look at its Min-K% row and the D3 table: which signal caught it, and would it still catch a leak of only 6 items?
3. The verbatim model completes a published row with the canary. Why is that evidence about the training data, and what does it fail to tell you about the scoreboard a buyer sees?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-eval-contamination/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-eval-contamination · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-eval-contamination/work (adapter-clean/ adapter-rephrase/ adapter-verbatim/ bench.json data.js evaluate.json filter.json fresh.json gates.json leak.json mixes.json regurg.json score.json train.json trambench-control.jsonl trambench-public.jsonl)
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Shrink the leak (24, 12 and 6 rows) and find the smallest dose the 13-gram scan and the Min-K% gate still catch, with each gate's false-alarm rate on the clean mix at that setting.
- Rewrite the leak so each row shares an 8-word window with its item, and find the overlap window length that catches it; count the benign wiki rows that window length would reject.
- Separate wording recall from fact knowledge: compare the verbatim and rephrase models on D3's reworded leaked items, and write a verdict rule that uses both scores.
- Give TramBench a v2 canary and measure how much of a v1 leak the D1 filter still catches when only the canary changed.

## Further Reading

- NIST, [Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations](https://csrc.nist.gov/pubs/ai/100/2/e2025/final) (NIST AI 100-2 E2025), seed source `s-nist` of this node.
- Mazeika et al., [HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal](https://arxiv.org/abs/2402.04249) (2024), seed source `s-harmbench` of this node: why a benchmark result is a claim about the benchmark, and what it does and does not certify.
- Srivastava et al., [Beyond the Imitation Game: Quantifying and Extrapolating the Capabilities of Language Models](https://arxiv.org/abs/2206.04615) (BIG-bench, 2022): the canary-GUID convention this lab's bench files follow.
- Brown et al., [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) (GPT-3, 2020), Appendix C.1: 13-gram overlap decontamination between training data and benchmarks.
- Shi et al., [Detecting Pretraining Data from Large Language Models](https://arxiv.org/abs/2310.16789) (USENIX Security 2024): Min-K% Prob, the membership signal D2 uses.
- Yang et al., [Rethinking Benchmark and Contamination for Language Models with Rephrased Samples](https://arxiv.org/abs/2311.04850) (2023): why n-gram scans miss paraphrased contamination, and what rephrased and dynamic evaluations recover.
- [LAB-47 · Lineage or it did not happen](../life-data/README.md): the same hazard entering through the data pipeline, traced with lineage instead of detection gates.

---

[← prev](../attack-judge-manipulation/README.md) · [All labs](../README.md) · [next →](../concept-gradients/README.md)
