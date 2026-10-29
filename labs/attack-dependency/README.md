---
lab_id: LAB-10
title: "from_pretrained ran my code"
node: attack-dependency                  # == folder name == articles/<node-id>.md basename
related_nodes: [system-loader, system-tools, tool-transformers, defense-ci, defense-isolation, defense-provenance, eval-asr, eval-threat-model, attack-unsafe-load, attack-artifact-substitution]
family: family-supply
access_profile: A13
level: intermediate                      # beginner | intermediate | advanced
time: "75 min"
compose_profiles: [supply]               # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 2.2 GB disk for the workbench image; the lab writes about 40 MB to work/."
canary: ATLAS-CANARY-7f3a
last_tested: 2026-10-26
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0"
covers:                                  # nodes practiced here as named steps (optional; see _template)
  - {node: tool-transformers, steps: "3-5, D1", anchor: "step-3--trust_remote_codetrue-runs-it--explainer-4"}
  - {node: defense-ci, steps: "D3", anchor: "step-d3--a-ci-gate-in-the-low-trust-job--explainer-9"}
---

# LAB-10 · from_pretrained ran my code

> **Atlas node:** [Malicious dependencies or repository code](https://ai-security-atlas.github.io/?node=attack-dependency) · **Family:** family-supply · **Level:** intermediate · **Time:** 75 min · **Model backend:** none

## Overview

LAB-01 hid code in a checkpoint's pickle. This lab needs no pickle at all: the code ships as ordinary Python next to the weights, or as a package you install. A model repo can carry its own architecture as `.py` files, and its `config.json` `auto_map` tells `from_pretrained()` to import them; with `trust_remote_code=True`, everything at the top of those files runs inside the load. A package can do the same at install time or, with a `.pth` file, at every Python start. In this lab you publish a small model to a local git "hub", push a routine-looking v1.1 that adds the lab's inert canary payload to the modeling file, and watch it run in `from_pretrained()` while the model keeps answering. You then see which revision you really loaded when a branch or tag moves, install a one-letter typosquat from a local package index, and measure four defenses: refusing remote code unless it is the reviewed commit, hash-pinned requirements, a CI gate in a credential-less job, and the sandbox from LAB-01. Everything is local: the hub and the index are folders under `work/`. Source: [`labs/attack-dependency`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-dependency).

By the end you will be able to:

1. Point to the line in a model repo that makes `from_pretrained()` import its code, and show that code running during the load with the model output unchanged.
2. Explain why `revision="main"` or a tag is not a pin, and show a moved tag delivering new code while a commit sha does not.
3. Install from a hash-pinned lock file, gate a change in a low-trust CI job, and say what each defense, and the sandbox, does not stop.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

This lab deliberately runs untrusted repository code and a malicious package's start-up hook, first in the workbench (to show the default risk) and then in the sandbox. Both carry LAB-01's payload body, `labkit.INERT_CODE`, copied unchanged (so its message still says `torch.load`); it only writes `work/canary-marker.txt` and prints the canary. The hub, the package index and every wheel are folders and files under `work/`; nothing is published or downloaded. Never upload the hub repos or the `work/dist*` wheels anywhere, never install them outside the lab containers, and run `cleanup.py` when you finish.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-dependency`](../../articles/attack-dependency.md) |
| Family | [`family-supply`](https://ai-security-atlas.github.io/?node=family-supply) |
| Goal | [`goal-environment`](https://ai-security-atlas.github.io/?node=goal-environment) |
| Access profile | `A13` Dependency or package distribution (caveat: *Victim must install, import or execute the affected artifact.*) |
| Read first | [`system-loader`](https://ai-security-atlas.github.io/?node=system-loader), [`system-tools`](https://ai-security-atlas.github.io/?node=system-tools) |
| Mitigated by | [`defense-ci`](https://ai-security-atlas.github.io/?node=defense-ci), [`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation) |
| Evaluated by | [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`tool-transformers`](https://ai-security-atlas.github.io/?node=tool-transformers), [`attack-unsafe-load`](https://ai-security-atlas.github.io/?node=attack-unsafe-load), [`attack-artifact-substitution`](https://ai-security-atlas.github.io/?node=attack-artifact-substitution), [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance) |

> [!NOTE]
> **Atlas caveat:** Traditional software supply-chain controls remain necessary around AI artifacts.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The code runs on the machine that loads the repo or installs the package. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model. |
| external-api | n/a | — | A remote model API never imports your repo code or packages, so it cannot be the victim here. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Each load takes seconds; the slowest step runs four loads. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (2.2 GB). The lab writes about 40 MB to `work/` (mostly throwaway virtualenvs). |
| Total time | 75 min: about 30 min of commands, the rest reading |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done (the workbench image is built).
- Labs to finish first: [LAB-01 · What torch.load really runs](../attack-unsafe-load/README.md) is recommended: it introduces the inert payload, the canary marker and the sandbox service.
- Concepts to read first: [`system-loader`](https://ai-security-atlas.github.io/?node=system-loader) and [`system-tools`](https://ai-security-atlas.github.io/?node=system-tools).

## Explainer

```bash
# host
open attack-dependency/explainer/index.html        # macOS
# xdg-open attack-dependency/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In 9 steps the explainer follows `from_pretrained()` from `config.json`'s `auto_map` to the import that runs the attacker's lines, shows branches and tags moving under a pin, plays a typosquat's `.pth` hook firing at Python start-up, and ends with the reviewed-commit policy, hash-pinned installs, the CI gate and the sandbox, all with strings from a reference run of this lab.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=supply` |
| host-ollama | `COMPOSE_PROFILES=supply` |
| external-api | `COMPOSE_PROFILES=supply` |
| none | `COMPOSE_PROFILES=supply` |

This lab calls no model, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`. Only the banner differs.

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
#16 [stage-0 6/8] RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
#16 CACHED
...
 Image atlas-labs/workbench:v2 Built
 Container atlas-labs-sandbox-1 Started
 Container atlas-labs-workbench-1 Started
```

What to notice: the `supply` profile starts two idle containers from the same image: `workbench` (network on, checkout read-write) and `sandbox` (no network, read-only checkout).

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-dependency · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu  safetensors 0.8.0  transformers 5.20.2
[ok] git 2.39.5  pip 25.0.1 (bundled; throwaway venvs are created offline)  local_hub fixture
[ok] work dir: /labs/attack-dependency/work (writable)
```

What to notice: pip comes from Python's bundled `ensurepip`, so the throwaway virtualenvs in Steps 6 and D2 need no network.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_hub_publish | workbench | <15 s | 1 |
| 2 | s02_push_update | workbench | <15 s | 3 |
| 3 | s03_victim_load --trust-remote-code + host check | workbench | <30 s | 4 |
| 4 | s03_victim_load | workbench | <30 s | — |
| 5 | s05_revisions | workbench | ≈1–3 min | — |
| 6 | s06_build_index, s06_victim_install | workbench | <30 s | 6 |
| D1 | d1_pinned_load (×3) | workbench | ≈1 min | 7 |
| D2 | d2_require_hashes | workbench | <30 s | 8 |
| D3 | d3_ci_gate (×2) | sandbox | <30 s | 9 |
| D4 | cleanup --marker-only, d4_isolation_probe + host check | workbench, sandbox | <30 s | 9 |

Runtimes were measured in the containers on a test machine shared with other heavy jobs (load average 12–36), so they are upper bounds; each includes 2–5 s of container start-up per `docker compose run`. A load with remote code took about 15–30 s, a throwaway virtualenv plus `pip install` about 10–20 s, and the full verified run of every step, Setup to Cleanup, took 175 s (warm image, load average about 30).

### Step 1 — A model that ships its own code · [explainer 1](explainer/index.html#attack-dependency/1)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/s01_hub_publish.py
```

**Observe**

```text
[atlas-lab] attack-dependency · s01_hub_publish.py · torch 2.14.1+cpu · backend none
[ok] acme published acme/tiny-sentiment to work/hub/acme/tiny-sentiment.git, tag v1.0
     commit dea887921ad77734f0ea49b53534d25faf7a8615
     README.md                       216 bytes
     config.json                     452 bytes
     configuration_tinysent.py       340 bytes
     model.safetensors              2344 bytes
     modeling_tinysent.py            747 bytes

config.json auto_map (class name -> <file>.<class> in the repo):
  AutoConfig                           -> configuration_tinysent.py :: TinySentConfig
  AutoModelForSequenceClassification   -> modeling_tinysent.py :: TinySentForSequenceClassification

[ok] your team reviewed the code at v1.0 and saved work/reviewed.json:
     commit dea887921ad77734f0ea49b53534d25faf7a8615
     configuration_tinysent.py    sha256 25990d05b0ee
     modeling_tinysent.py         sha256 1b2c12069b38

model card: Tokenize with our helper package: `pip install acme-tokenizer`.
```

What to notice: `auto_map` maps the Auto classes to `<file>.<class>` names, and those files are plain Python in the repo, next to the weights; the commit sha is the same on every machine because the fixture fixes dates and file bytes.

**Why**

`from_pretrained()` is a [`system-loader`](https://ai-security-atlas.github.io/?node=system-loader): when a config names classes that [`tool-transformers`](https://ai-security-atlas.github.io/?node=tool-transformers) does not ship, it can fetch them from the repo itself. The "hub" is the shared `local-hub` fixture (`labs/_shared/local_hub`), a bare git repo under `work/hub/`, so revisions are real branches, tags and commits. Your team's review is recorded as a commit sha plus the sha256 of each code file.

### Step 2 — A routine-looking commit · [explainer 3](explainer/index.html#attack-dependency/3)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/s02_push_update.py
```

**Observe**

```text
[atlas-lab] attack-dependency · s02_push_update.py · torch 2.14.1+cpu · backend none
[ok] acme-ci pushed v1.1 to main: 8185997c206c57084dd92d66f43468db7c4b1cd3

$ git log --format='%h %cn %s' main
8185997 acme-ci  v1.1: cache the byte table at import
dea8879 acme     publish tiny-sentiment v1.0

$ git diff --stat v1.0 main
 README.md            | 2 +-
 modeling_tinysent.py | 6 ++++++
 2 files changed, 7 insertions(+), 1 deletion(-)

$ git diff v1.0 main -- modeling_tinysent.py
@@ -7,2 +7,8 @@ from .configuration_tinysent import TinySentConfig
 
+# v1.1: warm the byte table at import time
+import os, time
+p = os.path.join(os.environ.get('ATLAS_WORK', '/labs/attack-unsafe-load/work'), 'canary-marker.txt')
+open(p, 'w').write('ATLAS-CANARY-7f3a pid=%d uid=%d at=%d\n' % (os.getpid(), os.getuid(), int(time.time())))
+print('[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote ' + p)
+

weights unchanged: True
```

What to notice: the weights are byte-identical and the change is six lines of module-level code under a plausible comment; nothing has run yet.

**Why**

Whoever can push to a repo you load from, here a leaked CI token committing as `acme-ci`, controls code that will execute on every machine that loads `main` with remote code enabled ([`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency)). The added lines are `labkit.INERT_CODE`, the same inert body as LAB-01: it writes the marker and prints the canary. Unlike [`attack-artifact-substitution`](https://ai-security-atlas.github.io/?node=attack-artifact-substitution) in LAB-01, no file format is abused: the repo simply ships code.

### Step 3 — trust_remote_code=True runs it · [explainer 4](explainer/index.html#attack-dependency/4)

> [!WARNING]
> This step deliberately imports the tampered repository code in the workbench, which has network access and can write your checkout, to show what remote code does on a normal machine. Step D4 repeats it in the sandbox.

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/s03_victim_load.py --revision main --trust-remote-code
# host
cat attack-dependency/work/canary-marker.txt
```

**Observe**

```text
[atlas-lab] attack-dependency · s03_victim_load.py · torch 2.14.1+cpu · backend none
revision main (branch) -> commit 8185997   files: README.md, config.json, configuration_tinysent.py, model.safetensors, modeling_tinysent.py
AutoModelForSequenceClassification.from_pretrained(<snapshot>, trust_remote_code=True)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-dependency/work/canary-marker.txt
loaded transformers_modules._8185997c206c57084dd92d66f43468db7c4b1cd3.7cd54206d011c75b.modeling_tinysent.TinySentForSequenceClassification
predict('a great little model') -> positive  logits [0.0023, 0.1]
marker exists: True
ATLAS-CANARY-7f3a pid=1 uid=1000 at=1793019661
```

What to notice: the `[payload]` line prints inside `from_pretrained()`, before the model exists, and the prediction and logits are exactly those of v1.0.

**Why**

With `trust_remote_code=True`, [`tool-transformers`](https://ai-security-atlas.github.io/?node=tool-transformers) copies the files named in `auto_map` into its modules cache (here `work/hf_modules/`) and imports them, so every statement at module level runs with your permissions ([`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency)). The model works, so nothing looks wrong. The payload's message says `torch.load` because it is LAB-01's shared body, unchanged; here it ran during an import.

### Step 4 — trust_remote_code=False refuses

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/s03_victim_load.py --revision main
```

**Observe**

```text
[atlas-lab] attack-dependency · s03_victim_load.py · torch 2.14.1+cpu · backend none
revision main (branch) -> commit 8185997   files: README.md, config.json, configuration_tinysent.py, model.safetensors, modeling_tinysent.py
AutoModelForSequenceClassification.from_pretrained(<snapshot>, trust_remote_code=False)
BLOCKED: ValueError: The repository <snapshot> contains custom code which must be executed to correctly load the model. You can inspect the repository content at <snapshot> .
  Please pass the argument `trust_remote_code=True` to allow custom code to be run.
marker exists: False
```

What to notice: the load stops before any repo file is imported, and the error tells you exactly how to turn the code back on.

**Why**

`trust_remote_code=False` is the safe setting ([`tool-transformers`](https://ai-security-atlas.github.io/?node=tool-transformers)), but the model cannot load without its code, so teams flip the flag to make it work. The script passes `False` explicitly: left unset, transformers asks "Do you wish to run the custom code? [y/N]" in an interactive terminal, and one keystroke runs it ([`system-loader`](https://ai-security-atlas.github.io/?node=system-loader)).

### Step 5 — Branches and tags move; commits do not (≈1–3 min)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/s05_revisions.py
```

**Observe**

```text
[atlas-lab] attack-dependency · s05_revisions.py · torch 2.14.1+cpu · backend none
revision                     commit       code reviewed?   payload
main                         8185997      NO               FIRED
v1.0                         dea8879      yes              -
-- attacker: git push --force origin v1.0   (tag v1.0 now -> 8185997)
v1.0                         8185997      NO               FIRED
dea887921ad7... (full sha)   dea8879      yes              -
```

What to notice: `v1.0` loads reviewed code until the attacker force-pushes the tag, then the same `revision="v1.0"` fires the payload; only the full commit sha keeps loading the reviewed code.

**Why**

A branch and a tag are names that whoever controls the repo can repoint; a commit sha is the hash of the content and its history ([`tool-transformers`](https://ai-security-atlas.github.io/?node=tool-transformers): `from_pretrained(..., revision=<sha>)`, and `code_revision=<sha>` when the code lives in another repo). Pinning a sha you reviewed is what makes `trust_remote_code=True` a decision about known code ([`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance)). The moved tag stays moved for the rest of the lab.

### Step 6 — One letter off: a typosquatted package · [explainer 6](explainer/index.html#attack-dependency/6)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/s06_build_index.py
docker compose run --rm workbench python attack-dependency/scripts/s06_victim_install.py
```

**Observe**

```text
[atlas-lab] attack-dependency · s06_build_index.py · torch 2.14.1+cpu · backend none
[ok] local index file:///labs/attack-dependency/work/index/simple
     acme-tokenizer   acme_tokenizer-1.0.0-py3-none-any.whl  sha256 f4ffd766b406
     acme-tokenizr    acme_tokenizr-1.0.0-py3-none-any.whl   sha256 95a01921c259

acme-tokenizr wheel contents:
  _acme_tokenizr_boot.py                        305 bytes
  acme_tokenizr-1.0.0.dist-info/METADATA        134 bytes
  acme_tokenizr-1.0.0.dist-info/WHEEL            85 bytes
  acme_tokenizr.pth                              27 bytes
  acme_tokenizr/__init__.py                      48 bytes
  acme_tokenizr-1.0.0.dist-info/RECORD          453 bytes

acme_tokenizr.pth: import _acme_tokenizr_boot
[atlas-lab] attack-dependency · s06_victim_install.py · torch 2.14.1+cpu · backend none
$ pip install --index-url file:///labs/attack-dependency/work/index/simple acme-tokenizr
Looking in indexes: file:///labs/attack-dependency/work/index/simple
Successfully installed acme-tokenizer-1.0.0 acme-tokenizr-1.0.0
marker exists after install: False
site-packages/*.pth: acme_tokenizr.pth

$ venv-victim/bin/python -c "import acme_tokenizer; ..."
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-dependency/work/canary-marker.txt
acme_tokenizer.encode("great") -> [39, 50, 37, 33, 52]
marker exists: True
```

What to notice: pip installs both packages without a warning, nothing fires during the install, and the payload runs when the venv's Python starts, before `import acme_tokenizer`, even though the script never imports the typo name.

**Why**

Packages are code from the same supply chain as the model ([`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency)): `acme-tokenizr` depends on and re-exports the real `acme-tokenizer`, so it works, and its `acme_tokenizr.pth` file is processed by Python's `site` module at every interpreter start in that environment. The index is a folder in the PEP 503 layout PyPI serves, read through `file://`; the wheels are built by hand with fixed timestamps, so their hashes are reproducible ([`system-tools`](https://ai-security-atlas.github.io/?node=system-tools)).

## Defend

### Step D1 — Refuse remote code unless it is the reviewed commit · [explainer 7](explainer/index.html#attack-dependency/7)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/d1_pinned_load.py --revision main
docker compose run --rm workbench python attack-dependency/scripts/d1_pinned_load.py --revision 8185997c206c57084dd92d66f43468db7c4b1cd3
docker compose run --rm workbench python attack-dependency/scripts/d1_pinned_load.py --revision dea887921ad77734f0ea49b53534d25faf7a8615
```

**Observe**

```text
[atlas-lab] attack-dependency · d1_pinned_load.py · torch 2.14.1+cpu · backend none
REFUSED: 'main' is a branch or tag name; pin a full 40-character commit sha
marker exists: False

[atlas-lab] attack-dependency · d1_pinned_load.py · torch 2.14.1+cpu · backend none
pinned commit 8185997
  ok       configuration_tinysent.py    reviewed 25990d05b0ee  got 25990d05b0ee
  MISMATCH modeling_tinysent.py         reviewed 1b2c12069b38  got 7e4cad1de804
REFUSED: remote code differs from the reviewed code
marker exists: False

[atlas-lab] attack-dependency · d1_pinned_load.py · torch 2.14.1+cpu · backend none
pinned commit dea8879
  ok       configuration_tinysent.py    reviewed 25990d05b0ee  got 25990d05b0ee
  ok       modeling_tinysent.py         reviewed 1b2c12069b38  got 1b2c12069b38
VERIFIED: loaded TinySentForSequenceClassification from the reviewed commit with trust_remote_code=True
predict('a great little model') -> positive  logits [0.0023, 0.1]
marker exists: False
```

What to notice: a branch name is refused, a full sha of the tampered commit is refused by the code hashes, and only the reviewed commit is loaded with `trust_remote_code=True`.

**Why**

Keep `trust_remote_code=False` as the default and allow it only for a full commit sha whose code files match what you reviewed ([`tool-transformers`](https://ai-security-atlas.github.io/?node=tool-transformers), [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance)). The commit shas in these commands are the same on every machine because the hub fixture is deterministic. Limitation: a pin proves you load the code you reviewed, not that the review caught everything, and imports inside that code (other packages) are not covered by it.

### Step D2 — Install from hashes, not names · [explainer 8](explainer/index.html#attack-dependency/8)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/d2_require_hashes.py
```

**Observe**

```text
[atlas-lab] attack-dependency · d2_require_hashes.py · torch 2.14.1+cpu · backend none
work/requirements.lock:   acme-tokenizer==1.0.0 --hash=sha256:f4ffd766b406...
work/requirements-pr.txt: acme-tokenizr==1.0.0
work/index-mirror:        acme_tokenizer-1.0.0-py3-none-any.whl sha256 165944ac95b7...

(a) $ pip install --require-hashes --index-url file:///labs/attack-dependency/work/index/simple -r work/requirements-pr.txt
  ERROR: Hashes are required in --require-hashes mode, but they are missing from some requirements.
      acme-tokenizr==1.0.0 --hash=sha256:95a01921c2592e3159c4310d5e63ce2488c567ecb054a9c6679beb3e7fbb9df9
  exit 1; marker exists: False

(b) $ pip install --require-hashes --index-url file:///labs/attack-dependency/work/index-mirror/simple -r work/requirements.lock
  ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE.
      acme-tokenizer==1.0.0 from the index:
          Expected sha256 f4ffd766b40650b73fc294f5adb54458ae89cffc065b93ab71ea552c41e7e112
               Got        165944ac95b7c69256ff303f2361d789c3207583cf521bc7230f0aff99989772
  exit 1; marker exists: False

(c) $ pip install --require-hashes --index-url file:///labs/attack-dependency/work/index/simple -r work/requirements.lock
  Successfully installed acme-tokenizer-1.0.0
  exit 0; marker exists: False
  $ venv-locked/bin/python -c 'import acme_tokenizer'
  acme_tokenizer 1.0.0 imported
marker exists: False
```

What to notice: the typo'd requirement is refused because it has no hash, a same-name, same-version wheel from a compromised mirror is refused because its bytes differ, and the locked install starts a clean interpreter.

**Why**

`pip install --require-hashes -r requirements.lock` installs only files whose sha256 you recorded when you reviewed them, so a typed name, a higher version or a swapped file cannot slip in ([`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency)). Generate such locks with `pip-compile --generate-hashes` or `uv pip compile --generate-hashes`. Limitation: pip's own error prints the hash a new package "actually had", so a reviewer who pastes it in has approved the attacker's file; hashes prove identity, not intent.

### Step D3 — A CI gate in the low-trust job · [explainer 9](explainer/index.html#attack-dependency/9)

**Do**

```bash
docker compose run --rm sandbox python attack-dependency/scripts/d3_ci_gate.py --revision main --requirements work/requirements-pr.txt
docker compose run --rm sandbox python attack-dependency/scripts/d3_ci_gate.py --revision dea887921ad77734f0ea49b53534d25faf7a8615 --requirements work/requirements.lock
```

**Observe**

```text
[atlas-lab] attack-dependency · d3_ci_gate.py · torch 2.14.1+cpu · backend none
CI gate (inspect job): static checks only; nothing from the change is imported, installed or loaded
job context: network interfaces lo · checkout writable: no · secret-like env vars: none
[FAIL] model revision main is a branch or tag, not a commit sha
[FAIL] remote code at 8185997 differs from the review: modeling_tinysent.py
[FAIL] requirements-pr.txt: acme-tokenizr==1.0.0 has no --hash
[FAIL] requirements-pr.txt: acme-tokenizr is not approved (1 edit from acme-tokenizer: likely typosquat)
GATE: FAIL (4 problems) -> the trusted publish job does not run

[atlas-lab] attack-dependency · d3_ci_gate.py · torch 2.14.1+cpu · backend none
CI gate (inspect job): static checks only; nothing from the change is imported, installed or loaded
job context: network interfaces lo · checkout writable: no · secret-like env vars: none
[pass] model revision dea887921ad7... is a full commit sha
[pass] remote code at dea8879 matches the review (configuration_tinysent.py, modeling_tinysent.py)
[pass] requirements.lock: acme-tokenizer==1.0.0 is pinned with a hash
[pass] requirements.lock: acme-tokenizer is approved
GATE: PASS -> the trusted publish job may run with these exact pins
```

What to notice: the gate runs with only a loopback interface, a read-only checkout and no secret-like variables, reads git objects and text files without importing anything, and fails the change on four counts, including the typosquat.

**Why**

[`defense-ci`](https://ai-security-atlas.github.io/?node=defense-ci) splits a pipeline by trust: inspecting an outside change is a low-trust job with no credentials, no network and no write access, and only a trusted job, after review, gets the publish token and uses the exact pins the gate passed. This is the misconfiguration GitHub warns about for `pull_request_target`: running untrusted code in the privileged job. Limitation: a static gate catches only the policies you encoded; a malicious change that passes review and pins passes the gate too.

### Step D4 — Contain what still runs · [explainer 9](explainer/index.html#attack-dependency/9)

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/cleanup.py --marker-only
docker compose run --rm sandbox python attack-dependency/scripts/d4_isolation_probe.py --revision main
# host
test -e attack-dependency/work/canary-marker.txt && echo "host marker: present" || echo "host marker: absent"
```

**Observe**

```text
[atlas-lab] attack-dependency · cleanup.py · torch 2.14.1+cpu · backend none
[ok] no canary-marker.txt to remove
[atlas-lab] attack-dependency · d4_isolation_probe.py · torch 2.14.1+cpu · backend none
from_pretrained(<snapshot of main = 8185997>, trust_remote_code=True)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /work/canary-marker.txt
marker in sandbox: True (/work/canary-marker.txt)
dns canary.invalid: gaierror (no network): [Errno -3] Temporary failure in name resolution
egress 192.0.2.1:9: OSError Network is unreachable
write to /labs: OSError Read-only file system
host marker: absent
```

What to notice: the remote code still ran, but only the sandbox's throwaway `/work` received the marker; DNS, egress and writes to the checkout failed, and the host marker is absent.

**Why**

This is LAB-01's sandbox ([Step D2 there](../attack-unsafe-load/README.md#step-d2--isolate-the-loader--explainer-9)): no network, read-only root and checkout, no capabilities, a tmpfs `/work` ([`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation)). Load or test untrusted repos and packages there, the same place the D3 gate runs. Limitation: isolation contains the code; it does not stop it from running, and anything you later copy out of the sandbox and run elsewhere is outside its protection.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-dependency · evaluate.py · torch 2.14.1+cpu · backend none
vector       condition                                            payload
remote code  from_pretrained(main, trust_remote_code=True)        ran
remote code  from_pretrained(main, trust_remote_code=False)       blocked
remote code  tag v1.0 (moved), trust_remote_code=True             ran
remote code  D1 policy: reviewed sha only                         blocked
package      pip install acme-tokenizr (the typo)                 ran
package      --require-hashes -r requirements-pr.txt              blocked
package      --require-hashes -r requirements.lock, bad mirror    blocked
CI gate      D3 CI gate: main + requirements-pr.txt               refused
undefended paths: 3/3 ran · defended: 0/5 ran or passed
(sandbox: see Step D4; the remote code runs, the host work/ folder stays untouched)
RESULT: REPRODUCED
```

`RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict. Each row is a fresh process, and "ran" means the canary marker appeared (for the gate row, "passed" would mean the change was approved).

Questions for your notes:

1. Which rows are stopped by a name (a flag, a branch, a package name) and which by a hash? Which of them would a leaked push token defeat ([`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model))?
2. In D4 the payload still executed. Why does that still count as a defense when you score [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr)?
3. The D3 gate and the D1 policy both use `work/reviewed.json`. Who should be allowed to change that file, and in which job?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-dependency/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-dependency · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-dependency/work (dist-mirror/ dist/ hf_modules/ hub/ index-mirror/ index/ requirements-pr.txt requirements.lock reviewed.json venv-locked/ venv-victim/)
 Container atlas-labs-sandbox-1 Removed
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Extend `d3_ci_gate.py` with a check that fails when a repo's `config.json` gains an `auto_map` entry that the reviewed commit did not have, and test it on a third commit you push to the local hub.
- Add a second index that serves `acme-tokenizer` 99.0.0 (dependency confusion) and measure which install commands pick it: `--index-url` alone, with `--extra-index-url`, and with `--require-hashes -r requirements.lock`.
- Measure the D1 policy against a commit that keeps the reviewed `modeling_tinysent.py` but changes `auto_map` to point at a new file, and fix the policy if it passes.
- Plugins are the same risk one layer up: an MCP server or agent plugin is code you install and start. The [`attack-tool-description`](https://ai-security-atlas.github.io/?node=attack-tool-description) lab (wave 2) covers it; list which of this lab's four defenses would apply to a plugin installed from a local path.

## Further Reading

- GitHub, [Securely using `pull_request_target`](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target) (seed source `s-actions-security`).
- MITRE, [ATLAS](https://atlas.mitre.org/) (seed source `s-atlas`).
- Hugging Face, [Transformers documentation](https://huggingface.co/docs/transformers/index) (seed source `s-transformers-lib`), and its guide to [custom models and `trust_remote_code`](https://huggingface.co/docs/transformers/custom_models).
- pip, [secure installs and hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/); Python, [`site` and `.pth` files](https://docs.python.org/3/library/site.html); PyPA, [simple repository API (PEP 503)](https://peps.python.org/pep-0503/).

---

[← prev](../attack-model-imitation/README.md) · [All labs](../README.md)
