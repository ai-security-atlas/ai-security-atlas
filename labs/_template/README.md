---
lab_id: LAB-NN
title: "<Lab title>"
node: <node-id>                          # == folder name == articles/<node-id>.md basename
related_nodes: [<node-id>, <node-id>]
family: <family-id>
access_profile: <Axx>
level: beginner                          # beginner | intermediate | advanced
time: "<NN> min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a  (n/a only and always when model_backend: none)
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "<CPU / memory / disk in one line>"
canary: <fixed canary string>
last_tested: YYYY-MM-DD
tested_on: "<OS arch, Docker runtime, Docker version>"
objectives: [<goal-id>]                  # optional: overrides the goals json2hugo.py derives for this lab; delete the key if none
covers:                                  # optional: nodes practiced here as named steps; delete the key if none
  - {node: <node-id>, steps: "<4 | 4-6 | D1 | 4-7, D1 | Evaluate>", anchor: "<GitHub anchor of the first listed step's heading>"}
---

<!--
  Lab README template (labs/_template/README.md). Copy this folder to labs/<node-id>/.
  Rules (spec Section 2; checked by labs/_tools/lint_readme.py):
  * Keep every H2 below, with the same names, in the same order.
  * Walkthrough/Defend H3s are either a command step (**Do** / **Observe** / **Why**) or a
    reading step (**Read** / **Why**). Do = exactly one ```bash block, run from labs/;
    container commands use the full `docker compose run --rm <service> ...` form; host-only
    lines follow a `# host` comment line and must work in macOS bash 3.2/zsh and BSD tools.
    Observe = exactly one ```text block pasted from a container run (cut with ...), then one
    "What to notice:" sentence. Give ranges for random results.
  * Why: 2-3 sentences, links at least one Atlas node by live URL
    (https://ai-security-atlas.github.io/nodes/<id>/).
  * Each heading links the FIRST explainer step it covers (non-decreasing), or no link.
    Every explainer step is linked from at least one README step. When a step covers more
    explainer steps, put one line right under its heading:
    "Also in the explainer: [explainer 4](explainer/index.html#<node-id>/4) · [explainer 5](...)"
    (or "In the explainer: ..." when the heading has no link; under "## Evaluate" for a step
    only Evaluate covers). The Walkthrough table's Explainer column lists every linked step,
    with ranges for consecutive steps ("3–5", "2, 4") and "—" for none.
  * Runtime > ~30 s goes in the heading: "### Step 3 — <title> (≈4–9 min) · [explainer 5](...)".
  * Optional steps: "(optional, slow)" in the heading and the [!TIP] line shown in Step 2.
  * A step that calls an LLM endpoint starts with "> Model backend: ..." (see Step 2).
  * Callouts: only > [!NOTE], > [!WARNING], > [!TIP], plus the Overview's
    "> **What is staged here:**" line.
  * Overview shape: "Why it matters" (up to 3 sentences), "What you will do" (one scenario
    sentence and a list), then "Headline result:" (one sentence with the main number).
  * What is staged here: when the setup makes the attack or the defense work by
    construction (a system prompt that orders obedience, a scripted approver, a fenced
    follower), name every deliberate weakening in the Overview callout. Delete it otherwise.
  * Terms: define or link every ML or statistics term on first use. Link it to its primer
    heading, e.g. [embedding](../primers/vectors-without-the-math.md#embedding), or define it
    in one plain sentence. Lint checks that the primer file and its #anchor exist. Add a
    heading to a primer in labs/primers/ when a term has none.
  * Columns: every column an Observe block prints gets a one-line legend under the block
    ("Columns: `obeyed` = ..."), unless the script prints self-describing labels.
  * Small samples: quote counts ("0 of 5 trials", "11 of 12 slots"). Do not write "never",
    "only", "always" or "any" about results from a handful of trials.
  * Attendee text holds no maintainer or run-history notes (first measurements, roadmap
    bookkeeping, "this capture used ..."). Wrap them as
    <!-- Maintainer note (not for attendees): ... --> (lint strips comments).
  * One reference run: the README Observe blocks, expected/ and explainer/data.js come from
    the same run. Run VERIFY_NO_CLEANUP=1 python3 labs/_tools/verify.py <node-id> (it keeps
    work/), then scripts/export_explainer_data.py to write data.js from that work/.
  * Setup 1: one row per backend. Each code span is one
    `export COMPOSE_PROJECT_NAME=atlas-labs-<node-id> COMPOSE_PROFILES=<profiles>` line, plus
    ATLAS_APP_PORT=<port> when the profiles include rag-agent (8100 unless the lab has its own
    port) and any host port a Do line reads (e.g. SERVING_PORT=8180). verify.py exports every
    assignment of the row matching LAB_BACKEND. Do lines carry no COMPOSE_PROJECT_NAME,
    ATLAS_APP_TAG or ATLAS_APP_PORT prefixes. Per-step variables (SERVING_*, COMPOSE_FILE) may
    stay as prefixes; COMPOSE_FILE never goes in the export line.
  * Setup 2: build every image the lab needs ("docker compose build workbench", or
    "docker compose build workbench atlas-app" with rag-agent) and keep the skip sentence
    above **Do** (one-image or two-image wording). verify.py skips a build line when its images
    exist and logs "Image <name> present (build skipped; VERIFY_BUILD=1 rebuilds)", so a
    SETUP2 check matches "(Built|present)".
  * Cleanup: "docker compose down --remove-orphans", never -v. The model cache volumes have
    fixed names (atlas-labs-hf-cache-v1, atlas-labs-ollama-models-v1) and every lab shares them.
  * evaluate.py ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
  * covers: (optional, last key) lists Atlas nodes this lab practices as named steps, one
    "- {node: ..., steps: "...", anchor: "..."}" line each. Take them from
    docs/labs-roadmap.json (nodes with kind "covered" and covered_by == this lab's node) and
    keep only nodes a specific step really practices. steps: comma-separated "N", "N-M", "DN",
    "DN-DM" or "Evaluate". anchor: GitHub's id for the first listed step's heading (lowercase,
    link text kept, punctuation such as the em dash and middle dot dropped, spaces -> hyphens),
    e.g. "step-d1--pin-and-verify". Lint checks the node exists, has no lab of its own and is
    covered by no other lab, the steps exist and the anchor matches (a wrong anchor error
    prints the expected one). Quote steps and anchor. The site then shows
    "Practiced in LAB-NN · Steps ..." on the covered node and lists the lab on its hubs.
  * Learning path: add the lab to a module in labs/learning-path.yaml (its level, the labs it
    requires, recommends and points ahead to, each with a short why), then run
    python3 labs/_tools/learning_path.py --write. That fills in the "> **Learning path:**" line,
    the "Labs to finish first" / "Recommended first" / "Later in the path" bullets and the
    footer below; do not edit those by hand (lint runs learning_path.py --check). Requires and
    recommended may name only labs earlier in the path. Other Prerequisites bullets are yours.
  * expected/checks.txt: one "step-id<TAB>regex" per line (SETUP1..3, S1..Sn, D1..Dn, EVAL,
    CLEANUP); run them with: python3 labs/_tools/verify.py <node-id>
  Delete this comment in your lab.
-->

# LAB-NN · <Lab title>

> **Atlas node:** [<Node title>](https://ai-security-atlas.github.io/nodes/<node-id>/) · **Family:** <family-id> · **Level:** <level> · **Time:** <time> · **Model backend:** <none|optional|required>

> **Learning path:** Module <N> · step <i> of <m> · [<Module title>](../README.md#module-<n>-<module-title-anchor>)

## Overview

<Why it matters, in up to three sentences: the mechanism and why a defender cares. Link each ML or statistics term to its primer on first use, for example an [embedding](../primers/vectors-without-the-math.md#embedding).>

<What you will do: one sentence on the scenario.> You will:

- <what the first steps show>
- <what the attack steps show>
- <what the defenses measure>

> **What is staged here:** <every deliberate weakening that makes the attack or the defense work by construction, such as a system prompt that orders the model to obey. Delete this line when nothing is staged.>

Headline result: <one sentence with the main measured number, as a count such as "11 of 12 slots">. Source: [`labs/<node-id>`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/<node-id>).

By the end you will be able to:

1. <observable outcome>
2. <observable outcome>
3. <observable outcome, usually the defense>

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

<Lab-specific safety line.>

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`<node-id>`](../../articles/<node-id>.md) |
| Family | [`<family-id>`](https://ai-security-atlas.github.io/nodes/<family-id>/) |
| Goal | [`<goal-id>`](https://ai-security-atlas.github.io/nodes/<goal-id>/) |
| Access profile | `<Axx>` <profile title> (caveat: *<profile caveat>*) |
| Read first | [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/) |
| Mitigated by | [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/) |
| Evaluated by | [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/) |
| Related | [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/) |

> [!NOTE]
> **Atlas caveat:** <the node's caveat, verbatim>

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | <yes/partial/no/n/a> | <steps> | <why, for every no/partial> |
| host-ollama | <yes/partial/no/n/a> | <steps> | <why> |
| external-api | <yes/partial/no/n/a> | <steps> | <why> |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | <...> |
| Docker VM memory | <...> |
| Disk | <...> |
| Total time | <...> |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: <none, or [LAB-NN · title](../<node-id>/README.md) (why); ...>.
- Recommended first: <[LAB-NN · title](../<node-id>/README.md) (why); ... (line omitted when empty)>.
- Later in the path: <[LAB-NN · title](../<node-id>/README.md) (why); ... (line omitted when empty)>.
- Concepts to read first: [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/).

## Explainer

```bash
# host
open <node-id>/explainer/index.html        # macOS
# xdg-open <node-id>/explainer/index.html  # Linux
```

The explainer step links in this README work in a local clone and on the lab's Atlas page (`/labs/<node-id>/`, which shows this guide below the explainer); on GitHub they show HTML source. <One sentence on what the explainer covers.>

## Setup

### Setup 1 — Profiles

Run the line for your backend in the terminal you use for this lab. It names this lab's Compose project and selects its services, so the commands below need no prefix and Cleanup stops only this lab. Run it again in any new terminal. The backend settings stay in `labs/.env` (Start here, step 2, in the [labs index](../README.md)).

| Backend | Line to run |
| :--- | :--- |
| container-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-<node-id> COMPOSE_PROFILES=ollama,chat,workbench` |
| host-ollama | `export COMPOSE_PROJECT_NAME=atlas-labs-<node-id> COMPOSE_PROFILES=chat,workbench` |
| external-api | `export COMPOSE_PROJECT_NAME=atlas-labs-<node-id> COMPOSE_PROFILES=chat,workbench` |
| none | `export COMPOSE_PROJECT_NAME=atlas-labs-<node-id> COMPOSE_PROFILES=workbench` |

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
...
 Container atlas-labs-<node-id>-workbench-1 Started
```

What to notice: the build runs once; later labs reuse the image.

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python <node-id>/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] <node-id> · check_env.py · torch 2.14.1+cpu · backend none
[ok] ...
```

What to notice: <...>

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_<verb> | workbench | <15 s | 1 |
| 2 | s02_<verb> | workbench | ≈1 min | 2–4 |

### Step 1 — <title> · [explainer 1](explainer/index.html#<node-id>/1)

**Do**

```bash
docker compose run --rm workbench python <node-id>/scripts/s01_<verb>.py
```

**Observe**

```text
[atlas-lab] <node-id> · s01_<verb>.py · torch 2.14.1+cpu · backend none
...
```

Columns: `<column>` = <what it counts>; `<column>` = <...>. (One line for every printed column the labels do not explain.)

What to notice: <one sentence; quote counts such as "0 of 5 trials">.

**Why**

<2–3 sentences linking [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/).>

### Step 2 — <title> (optional, slow) (≈1 min) · [explainer 2](explainer/index.html#<node-id>/2)

Also in the explainer: [explainer 3](explainer/index.html#<node-id>/3) · [explainer 4](explainer/index.html#<node-id>/4)

> [!TIP] Optional: later steps use the shipped result, so you can skip this.

> Model backend: container-ollama · host-ollama · external-api

**Do**

```bash
docker compose run --rm workbench python <node-id>/scripts/s02_<verb>.py
```

**Observe**

```text
...
```

What to notice: <one sentence>.

**Why**

<2–3 sentences linking [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/).>

**Try (browser)**

1. <optional manual UI version of the same step; verify.py never runs it>

## Defend

### Step D1 — <apply the mitigation> · [explainer 5](explainer/index.html#<node-id>/5)

**Do**

```bash
docker compose run --rm workbench python <node-id>/scripts/d1_<verb>.py
```

**Observe**

```text
...
```

What to notice: <one sentence>.

**Why**

<Link [`<defense-id>`](https://ai-security-atlas.github.io/nodes/<defense-id>/) and restate the defense's limitation.>

### Step D2 — <reading step>

**Read**

<Prose only, no command.>

**Why**

<2–3 sentences linking [`<node-id>`](https://ai-security-atlas.github.io/nodes/<node-id>/).>

## Evaluate

In the explainer: [explainer 6](explainer/index.html#<node-id>/6)

**Do**

```bash
docker compose run --rm workbench python <node-id>/scripts/evaluate.py
```

**Observe**

```text
condition   ...
RESULT: REPRODUCED
```

`RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. <question that needs the Observe output>
2. <question>

## Cleanup

**Do**

```bash
docker compose run --rm workbench python <node-id>/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[ok] removed <node-id>/work (...)
```

> [!NOTE]
> Run it in the terminal where you ran the Setup 1 line, so `docker compose down` stops only this lab. Do not add `-v`: it removes the named volumes, including the HF and Ollama model caches that every lab shares, and the next lab downloads its models again. Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- <Evaluation or defense challenge; keeps the fixed canary and local fixtures; no solution given.>
- <...>

## Further Reading

- <Primary sources from the node's seed `references`.>
- <Tool documentation.>

---

[← prev in path](../<prev-node-id>/README.md) · [All labs](../README.md) · [next in path →](../<next-node-id>/README.md)
