---
lab_id: LAB-54
title: "An open Ollama port and a stolen fine-tune"
node: attack-weight-theft
related_nodes: [system-registry, concept-parameters, goal-model-theft, attack-model-imitation, system-serving, defense-least-privilege, defense-logging, eval-fidelity, eval-asr, eval-threat-model]
family: family-theft
access_profile: A08
level: intermediate
time: "25 min"
compose_profiles: [workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "CPU only. 4 GB Docker VM memory. About 800 MB in lab volumes for the public base and the registry copy. Images if missing: ollama/ollama:0.40.11 (~7 GB), registry:3 (~80 MB), plus the shared workbench image."
canary: ATLAS-CANARY-w54t
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64, OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3, ollama/ollama:0.40.11, registry:3"
---

# LAB-54 · An open Ollama port and a stolen fine-tune

> **Atlas node:** [Unauthorized checkpoint or adapter theft](https://ai-security-atlas.github.io/nodes/attack-weight-theft/) · **Family:** family-theft · **Level:** intermediate · **Time:** 25 min · **Model backend:** none

## Overview

A company Ollama server on a private lab network hosts a tiny public model and a fictional fine-tune called `lantern-ft`. The API has no password. You list the models, read the Modelfile, and ask that same API to push the fine-tune to a registry that also sits on the private network. The large weight file matches the public base. The private bytes are the system prompt and a license line, and both carry the canary `ATLAS-CANARY-w54t`. You then measure three defenses: a container that cannot resolve those names, a registry password, and a hash that recognizes the stolen system blob after the copy has already left.

By the end you will be able to:

1. Show that an unauthenticated Ollama API on a reachable network will list a fine-tune and push its blobs to a registry you control.
2. Separate the public weight blob from the private system layer by digest.
3. Measure a network cut, a registry password, and a fingerprint, including what each one costs and what each one leaves behind.

Source: [`labs/attack-weight-theft`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/attack-weight-theft).

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

This lab never publishes a port on your machine and never calls the host Ollama daemon. Run the steps only against `victim-ollama` and `registry` inside this compose project. Do not scan machines, registries, or Ollama servers outside it. The registry user `lab-operator` and password `atlas-lab-token` exist only in this lab. The canary is fictional text in `assets/Modelfile.ft`.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`attack-weight-theft`](../../articles/attack-weight-theft.md) |
| Family | [`family-theft`](https://ai-security-atlas.github.io/nodes/family-theft/) |
| Goal | [`goal-model-theft`](https://ai-security-atlas.github.io/nodes/goal-model-theft/) |
| Access profile | `A08` Readable model artifacts (caveat: *Weights, adapters or configurations are readable; distinguish public access from unauthorized access.*). Also `A13` Dependency or package distribution. |
| Read first | [`system-registry`](https://ai-security-atlas.github.io/nodes/system-registry/), [`concept-parameters`](https://ai-security-atlas.github.io/nodes/concept-parameters/) |
| Mitigated by | [`defense-least-privilege`](https://ai-security-atlas.github.io/nodes/defense-least-privilege/), [`defense-logging`](https://ai-security-atlas.github.io/nodes/defense-logging/) |
| Evaluated by | [`eval-fidelity`](https://ai-security-atlas.github.io/nodes/eval-fidelity/), [`eval-asr`](https://ai-security-atlas.github.io/nodes/eval-asr/), [`eval-threat-model`](https://ai-security-atlas.github.io/nodes/eval-threat-model/) |
| Related | [`attack-model-imitation`](https://ai-security-atlas.github.io/nodes/attack-model-imitation/), [`system-serving`](https://ai-security-atlas.github.io/nodes/system-serving/) |

> [!NOTE]
> **Atlas caveat:** Ordinary download of intentionally public weights is not theft.

The public base in this lab is `qwen2.5:0.5b`, copied from your own Ollama store. Copying that GGUF is the control. The private artifact is the fine-tune manifest: its system and license blobs.

## Backend Support

Scripts always run in the workbench or the outsider service. Nothing in this lab calls a chat backend. The victim is a separate Ollama container on an internal network, pinned to `ollama/ollama:0.40.11`.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | The lab does not send a prompt. Inference plays no part in copying the files. |
| host-ollama | n/a | — | The host daemon is not used. The host store is mounted read-only so the victim can copy one public model into its own volume. |
| external-api | n/a | — | No prompt leaves the machine. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any laptop. The victim runs a 0.5B GGUF and the steps hash one ~380 MB blob. |
| Docker VM memory | 4 GB is enough. |
| Disk | ~380 MB copied into the Ollama volume and again into the registry volume. The Ollama image is about 7 GB if it is not already local. |
| Total time | About 25 minutes. The first start copies the public model; later starts reuse the volume and finish in well under a minute. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [`LAB-09 · Imitating a model from queries`](../attack-model-imitation/README.md) is the neighboring exercise (behavior from queries). This lab copies files.
- The public model `qwen2.5:0.5b` is already in the host Ollama store (`~/.ollama/models`, or the directory you pass as `HOST_OLLAMA_MODELS`). The victim copies that one model. It does not pull weights.
- Concepts to read first: [`attack-weight-theft`](https://ai-security-atlas.github.io/nodes/attack-weight-theft/), [`system-registry`](https://ai-security-atlas.github.io/nodes/system-registry/).

## Explainer

```bash
# host
open attack-weight-theft/explainer/index.html        # macOS
# xdg-open attack-weight-theft/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The picture follows the open API, the push, the shared weight blob, the canary in the stolen system blob, and the three defenses.

## Setup

Every compose command below sets `COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft` so `down` cannot touch the shared `atlas-labs` project. Run them from `labs/`. The victim and the registry join the internal network `theft` through `attack-weight-theft/compose.yaml`. No host port is published.

### Setup 1 — Profiles

This lab does not call a model backend. Put this line in `labs/.env` if you keep one:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=ollama,chat,workbench` |
| host-ollama | `COMPOSE_PROFILES=chat,workbench` |
| external-api | `COMPOSE_PROFILES=chat,workbench` |
| none | `COMPOSE_PROFILES=workbench` |

### Setup 2 — Start the victim and the registry (≈1 min the first time)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose up -d --wait --force-recreate victim-ollama registry
# host
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose port victim-ollama 11434
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose port registry 5000
```

**Observe**

```text
 Container atlas-labs-attack-weight-theft-victim-ollama-1 Started
 Container atlas-labs-attack-weight-theft-registry-1 Started
 Container atlas-labs-attack-weight-theft-victim-ollama-1 Healthy
 Container atlas-labs-attack-weight-theft-registry-1 Healthy
invalid IP:0
invalid IP:0
```

What to notice: both services become healthy, and `docker compose port` prints `invalid IP:0` for each, which means neither API is bound on the host.

**Why**

The victim listens on the compose network only ([`system-serving`](https://ai-security-atlas.github.io/nodes/system-serving/)). `--force-recreate` on the registry starts it from the two-file compose set, so a later password step does not leak into the next run. The workbench image is already `atlas-labs/workbench:v4`; this setup does not build it.

### Setup 3 — Check the environment

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · check_env.py · torch 2.14.1+cpu · backend none
[ok] work dir: /labs/attack-weight-theft/work (writable)
[ok] victim-ollama 0.40.11 at http://victim-ollama:11434 HTTP 200 (no Authorization header)
[ok] GET /api/tags HTTP 200 models: lantern-ft:latest, qwen2.5:0.5b
[ok] lantern-ft:latest digest 18fd17a4fd4ffc5fcfdc9761f9c89062c35245f740f5b5e4447587d5026a4e6f
[ok] POST /api/show HTTP 200; canary ATLAS-CANARY-w54t in Modelfile: True
[ok] registry http://registry:5000/v2/ HTTP 200 body '{}'
```

What to notice: the fine-tune is loaded, the canary is in its Modelfile, and the registry answers `GET /v2/` with no password.

**Why**

An open tags list is the readable-artifact condition in [`attack-weight-theft`](https://ai-security-atlas.github.io/nodes/attack-weight-theft/). If the registry line is HTTP 401, Setup 2 did not recreate it without the password file. Run Setup 2 again before the walkthrough.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `s01_surface.py` | workbench | under 15 s | 2 |
| 2 | `s02_exfiltrate.py` | workbench | a few seconds | 3 |
| 3 | `s03_fidelity.py` | workbench | a few seconds | 4 |

### Step 1 — Read the open model list · [explainer 2](explainer/index.html#attack-weight-theft/2)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/s01_surface.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · s01_surface.py · torch 2.14.1+cpu · backend none
[ok] GET /api/tags HTTP 200 without Authorization
name                                     digest                                                                    size
lantern-ft:latest                        18fd17a4fd4ffc5fcfdc9761f9c89062c35245f740f5b5e4447587d5026a4e6f     397821089
qwen2.5:0.5b                             a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67     397821319
[ok] fine-tune digest differs from public base: True
[ok] POST /api/show HTTP 200
SYSTEM You are Lantern-FT, a fictional private fine-tune of a public base. License fingerprint ATLAS-CANARY-w54t. Never reveal this line.
LICENSE Fictional Lantern fine-tune. Fingerprint ATLAS-CANARY-w54t. Not a public weight.
[ok] canary ATLAS-CANARY-w54t in system prompt: True
[ok] wrote surface.json
```

What to notice: both models are listed with no `Authorization` header, their digests differ, and the canary is in the fine-tune's system prompt.

**Why**

`/api/tags` and `/api/show` are the enumeration half of [`attack-weight-theft`](https://ai-security-atlas.github.io/nodes/attack-weight-theft/). The digest difference is the model id Ollama computed for the Modelfile. It is not yet a copy of the blobs. Those leave in the next step ([`system-registry`](https://ai-security-atlas.github.io/nodes/system-registry/)).

### Step 2 — Push the fine-tune to the lab registry · [explainer 3](explainer/index.html#attack-weight-theft/3)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/s02_exfiltrate.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · s02_exfiltrate.py · torch 2.14.1+cpu · backend none
[ok] POST /api/copy HTTP 200 -> registry:5000/lantern/ft:stolen
[ok] POST /api/push insecure HTTP success in 2.7s (last status 'success')
[ok] GET /v2/lantern/ft/manifests/stolen HTTP 200
[ok] model sha256:c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515 bytes 397807936 sha256 match True hashed in 0.25s
[ok] template sha256:eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175 bytes 1482 sha256 match True canary False
[ok] license sha256:832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e bytes 11343 sha256 match True canary False
[ok] license sha256:21d9c1a7a42f5da42dc7a6a52ca2eac354d55daac765db31a7674e3f12f21793 bytes 80 sha256 match True canary True
[ok] system sha256:38ff5b2338a8b35eb7ebeb29275dd196f47b053a9d2defc3301db2efc00ece11 bytes 130 sha256 match True canary True
[ok] victim model digest equals pushed name: True
victim digest 18fd17a4fd4ffc5fcfdc9761f9c89062c35245f740f5b5e4447587d5026a4e6f
[ok] bytes in the stolen manifest: 397820971
[ok] wrote exfil.json
```

What to notice: the push finishes in a few seconds, every blob hash matches its digest, and the 130-byte system blob plus the 80-byte fictional license are the layers that contain the canary.

**Why**

Ollama's copy and push endpoints hand the blobs to whatever registry name you pass, here `registry:5000` on the lab network ([`attack-weight-theft`](https://ai-security-atlas.github.io/nodes/attack-weight-theft/)). Push time moves with disk cache: the reference run took 2.7 seconds because the weight blob was already on the victim. A cold copy of the same 397,807,936-byte file takes longer. The manifest total, 397,820,971 bytes, counts layers only. The tag size in Step 1 also includes a small config blob that is not a layer.

### Step 3 — Separate the public weight from the private layer · [explainer 4](explainer/index.html#attack-weight-theft/4)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/s03_fidelity.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · s03_fidelity.py · torch 2.14.1+cpu · backend none
[ok] POST /api/copy public base HTTP 200 -> registry:5000/public/qwen2.5:0.5b
[ok] pushed public base in 1.8s (blobs already stored are not sent again)
fine-tune weight sha256:c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515
public base weight sha256:c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515
[ok] weight blob equals public base: True
fine-tune model digest 18fd17a4fd4ffc5fcfdc9761f9c89062c35245f740f5b5e4447587d5026a4e6f
public base model digest a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67
[ok] model digest differs from public base: True
fine-tune system layers sha256:38ff5b2338a8b35eb7ebeb29275dd196f47b053a9d2defc3301db2efc00ece11
public base system layers sha256:66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e
[ok] system layer present only on the fine-tune: True
[ok] canary layer is the private system layer: True
[note] copying the public GGUF is not the theft. The private artifact is the fine-tune manifest.
[ok] wrote fidelity.json
```

What to notice: the weight digest is shared with `qwen2.5:0.5b`, the model digests differ, and the canary system layer is absent from the public base.

**Why**

[`eval-fidelity`](https://ai-security-atlas.github.io/nodes/eval-fidelity/) asks you to say what was copied exactly. Here the GGUF matches a public file, and the private layer is the 130-byte system blob `sha256:38ff5b2338a8b35eb7ebeb29275dd196f47b053a9d2defc3301db2efc00ece11`. Querying a model until its answers look similar is a different exercise ([`attack-model-imitation`](https://ai-security-atlas.github.io/nodes/attack-model-imitation/)). This lab stops at the files.

## Defend

### Step D1 — Cut the outsider off the theft network · [explainer 6](explainer/index.html#attack-weight-theft/6)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml COMPOSE_PROFILES=workbench,theft-outsider docker compose run --rm outsider python attack-weight-theft/scripts/d1_segment.py
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/d1_operator.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · d1_segment.py · torch 2.14.1+cpu · backend none
[ok] victim-ollama: reached=False in 25 ms (URLError: <urlopen error [Errno -3] Temporary failure in name resolution>)
[ok] registry: reached=False in 1 ms (URLError: <urlopen error [Errno -3] Temporary failure in name resolution>)
[ok] segmented: outsider blocked: True
[atlas-lab] attack-weight-theft · d1_operator.py · torch 2.14.1+cpu · backend none
[ok] operator GET /api/tags HTTP 200 median 6.9 ms over 5 trials
[ok] operator still sees ATLAS-CANARY-w54t: True
```

What to notice: the outsider fails both names in well under a second, while the operator still lists the fine-tune in about 7 ms.

**Why**

The outsider container sits on the internal network `isolated`, which has no route to `theft` ([`defense-least-privilege`](https://ai-security-atlas.github.io/nodes/defense-least-privilege/)). The failure is DNS, so the cost is a few tens of milliseconds and the operator path is unchanged. Anyone who can still join `theft` can repeat Step 2. Run this step before the password step: the operator command uses the two-file compose set and would rebuild the registry without a password.

### Step D2 — Require a registry password · [explainer 7](explainer/index.html#attack-weight-theft/7)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose up -d --no-deps --force-recreate --wait registry
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose run --no-deps --rm workbench python attack-weight-theft/scripts/d2_registry_auth.py
```

**Observe**

```text
 Container atlas-labs-attack-weight-theft-registry-1 Started
 Container atlas-labs-attack-weight-theft-registry-1 Healthy
[atlas-lab] attack-weight-theft · d2_registry_auth.py · torch 2.14.1+cpu · backend none
[ok] anonymous median HTTP 401 0.7 ms
[ok] authenticated median HTTP 200 2.7 ms
[ok] auth extra ms (authenticated median minus anonymous median): 2.0
[ok] authenticated manifest still lists 397820971 bytes
[ok] wrote audit.jsonl (10 lines)
```

What to notice: anonymous reads become HTTP 401 and the lab password still returns HTTP 200; on the reference run the password added 2.0 ms at the median, and a repeat can land within a few milliseconds of that.

**Why**

`compose.auth.yaml` turns on htpasswd for this registry only ([`defense-least-privilege`](https://ai-security-atlas.github.io/nodes/defense-least-privilege/)). The ten lines in `work/audit.jsonl` are the access record ([`defense-logging`](https://ai-security-atlas.github.io/nodes/defense-logging/)). `--no-deps` on the measurement keeps the password in place: a `docker compose run` that omits it rebuilds the registry from the two-file set and the 401 disappears. The password does not delete the blobs already stored. Ollama's own API is still open, so a second push still works until that port is cut off as well.

### Step D3 — Fingerprint the stolen system blob · [explainer 8](explainer/index.html#attack-weight-theft/8)

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose run --no-deps --rm workbench python attack-weight-theft/scripts/d3_fingerprint.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · d3_fingerprint.py · torch 2.14.1+cpu · backend none
[ok] re-read stolen manifest HTTP 200
[ok] fingerprint match True digest sha256:38ff5b2338a8b35eb7ebeb29275dd196f47b053a9d2defc3301db2efc00ece11 median 0.002 ms over 20 hashes
[ok] decoy rejected: True decoy sha256:a6175b258e0e
[ok] stolen bytes unchanged: 397820971
[note] the check reads a copy that already left. It does not delete or shrink that copy.
[ok] wrote d3.json
```

What to notice: hashing the 130-byte system blob twenty times costs about 0.002 ms each, the decoy in `assets/decoy.json` fails the digest check, and the stolen manifest still lists 397,820,971 bytes.

**Why**

A fingerprint tells you the blob is the private layer after the copy exists ([`eval-fidelity`](https://ai-security-atlas.github.io/nodes/eval-fidelity/)). It is a detective check. The stolen size is the same number Step 2 printed, so the cost of the check is the hash time and the copy is still on the registry. Keep the password file on this command, the same way Step D2 did, or the re-read is anonymous and fails.

## Evaluate

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose run --no-deps --rm workbench python attack-weight-theft/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] attack-weight-theft · evaluate.py · torch 2.14.1+cpu · backend none
measurement                                      value
fine-tune digest                                 18fd17a4fd4ffc5fcfdc9761f9c89062c35245f740f5b5e4447587d5026a4e6f
public base digest                               a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67
stolen bytes                                     397820971
anonymous registry HTTP                          401
authenticated registry HTTP                      200
outsider blocked                                 True
operator median ms                               6.9
[ok] open api lists the fine-tune: True
[ok] modelfile contains the canary: True
[ok] fine-tune digest differs from the public base: True
[ok] weight blob equals the public base: True
[ok] system blob contains the canary: True
[ok] system blob matches its digest: True
[ok] anonymous registry read is rejected: True
[ok] operator registry read succeeds: True
[ok] outsider cannot reach the victim: True
[ok] operator still reaches the victim: True
[ok] fingerprint rejects a decoy: True
[ok] private system layer is absent from the base: True
RESULT: REPRODUCED
```

`RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. Which bytes would still match if the fine-tune had been trained into a new GGUF, and which line in the table would flip?
2. The outsider is blocked and the registry returns 401. What can a container that is still on `theft` do to `victim-ollama`?
3. The fingerprint matches and the stolen size stays 397,820,971. What decision can that hash support, and what decision can it not support?

## Cleanup

**Do**

```bash
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --no-deps --rm workbench python attack-weight-theft/scripts/cleanup.py
COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] attack-weight-theft · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed attack-weight-theft/work (...)
```

> [!NOTE]
> `docker compose down` without `-v` keeps the named volumes `weight-theft-ollama` and `weight-theft-registry`, so the next Setup 2 skips the model copy. Add `-v` only if you intend to drop those copies. Do not drop volumes from any other compose project. The host model `qwen2.5:0.5b` is untouched.

## Going Further

- Repeat Step D2's manifest read a few dozen times and write down the spread of the password's extra milliseconds. The reference median was 2.0 ms; your spread is the measurement.
- After Step D3, push the same stolen tag to a second registry you add on `theft`, and check whether the system digest still matches. Decide what a match tells you about a copy that has already moved once.
- The Ollama API stayed open after the registry password. Sketch a second listener change that would make Step 2's push fail, and say what the operator in Step D1 would still be able to do.

## Further Reading

- MITRE ATLAS, the framework this node cites: <https://atlas.mitre.org/>
- OWASP Top 10 for LLM Applications (2025 list): <https://genai.owasp.org/llm-top-10/>
- Ollama API (`/api/tags`, `/api/show`, `/api/copy`, `/api/push`): <https://github.com/ollama/ollama/blob/main/docs/api.md>
- OCI Distribution Spec, the registry manifest and blob interface used in Steps 2 and D2: <https://github.com/opencontainers/distribution-spec>

---

[← prev](../life-preferences/README.md) · [All labs](../README.md) · [next →](../attack-agent-loop/README.md)
