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
    (https://ai-security-atlas.github.io/?node=<id>).
  * Each heading links the FIRST explainer step it covers (non-decreasing), or no link.
  * Runtime > ~30 s goes in the heading: "### Step 3 — <title> (≈4–9 min) · [explainer 5](...)".
  * Optional steps: "(optional, slow)" in the heading and the [!TIP] line shown in Step 2.
  * A step that calls an LLM endpoint starts with "> Model backend: ..." (see Step 2).
  * Callouts: only > [!NOTE], > [!WARNING], > [!TIP].
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
  * expected/checks.txt: one "step-id<TAB>regex" per line (SETUP1..3, S1..Sn, D1..Dn, EVAL,
    CLEANUP); run them with: python3 labs/_tools/verify.py <node-id>
  Delete this comment in your lab.
-->

# LAB-NN · <Lab title>

> **Atlas node:** [<Node title>](https://ai-security-atlas.github.io/?node=<node-id>) · **Family:** <family-id> · **Level:** <level> · **Time:** <time> · **Model backend:** <none|optional|required>

## Overview

One paragraph: what the mechanism is, and what the student will see happen. End with: Source: [`labs/<node-id>`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/<node-id>).

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
| Family | [`<family-id>`](https://ai-security-atlas.github.io/?node=<family-id>) |
| Goal | [`<goal-id>`](https://ai-security-atlas.github.io/?node=<goal-id>) |
| Access profile | `<Axx>` <profile title> (caveat: *<profile caveat>*) |
| Read first | [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>) |
| Mitigated by | [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>) |
| Evaluated by | [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>) |
| Related | [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>) |

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
- Labs to finish first: <none, or [LAB-NN · title](../<node-id>/README.md)>.
- Concepts to read first: [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>).

## Explainer

```bash
# host
open <node-id>/explainer/index.html        # macOS
# xdg-open <node-id>/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. <One sentence on what the explainer covers.>

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=ollama,chat,workbench` |
| host-ollama | `COMPOSE_PROFILES=chat,workbench` |
| external-api | `COMPOSE_PROFILES=chat,workbench` |
| none | `COMPOSE_PROFILES=workbench` |

### Setup 2 — Build and start

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
 Image atlas-labs/workbench:v2 Built
...
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
| 2 | s02_<verb> | workbench | ≈1 min | 2 |

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

What to notice: <one sentence>.

**Why**

<2–3 sentences linking [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>).>

### Step 2 — <title> (optional, slow) (≈1 min) · [explainer 2](explainer/index.html#<node-id>/2)

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

<2–3 sentences linking [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>).>

**Try (browser)**

1. <optional manual UI version of the same step; verify.py never runs it>

## Defend

### Step D1 — <apply the mitigation> · [explainer 2](explainer/index.html#<node-id>/2)

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

<Link [`<defense-id>`](https://ai-security-atlas.github.io/?node=<defense-id>) and restate the defense's limitation.>

### Step D2 — <reading step>

**Read**

<Prose only, no command.>

**Why**

<2–3 sentences linking [`<node-id>`](https://ai-security-atlas.github.io/?node=<node-id>).>

## Evaluate

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
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- <Evaluation or defense challenge; keeps the fixed canary and local fixtures; no solution given.>
- <...>

## Further Reading

- <Primary sources from the node's seed `references`.>
- <Tool documentation.>

---

[← prev](../<prev-node-id>/README.md) · [All labs](../README.md) · [next →](../<next-node-id>/README.md)
