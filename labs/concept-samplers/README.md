---
lab_id: LAB-45
title: "Same weights, ten times the cost"
node: concept-samplers                   # == folder name == articles/<node-id>.md basename
related_nodes: [concept-noise, arch-diffusion, tool-diffusers, concept-decoding, attack-sponge, eval-cost, defense-budget, eval-repro, attack-dependency, defense-safe-load, format-safetensors]
family: family-availability
access_profile: A19
level: beginner
time: "60 min"
compose_profiles: [workbench]
model_backend: none
backends:
  container-ollama: n/a
  host-ollama: n/a
  external-api: n/a
hardware: "Any 64-bit CPU. 4 GB Docker VM memory. 2.2 GB workbench image, plus 0.14 GB for google/ddpm-cifar10-32 in the HF cache and 56 MB for the pinned diffusers package (a 6.4 MB wheel) installed in work/pydeps."
canary: ATLAS-CANARY-7f3a
last_tested: 2026-11-01
tested_on: "macOS 15.7.3 arm64 (M4 Max, shared with other jobs), OrbStack, Docker 29.8.2, Compose 5.5.0, workbench v3, diffusers 0.42.1"
covers:
  - {node: tool-diffusers, steps: "2, 6, D3", anchor: "step-2--swap-the-scheduler-keep-the-weights--explainer-2"}
---

# LAB-45 · Same weights, ten times the cost

> **Atlas node:** [Diffusion and flow samplers](https://ai-security-atlas.github.io/?node=concept-samplers) · **Family:** family-availability · **Level:** beginner · **Time:** 60 min · **Model backend:** none

## Overview

A diffusion model learns to remove noise; a *sampler* is the procedure that turns that skill into a picture. It picks the timesteps (the schedule) and the update rule between them (the solver), and it calls the trained network once per step. In Hugging Face Diffusers the sampler is a *scheduler*, a small JSON config with no weights, and you swap it with one line. In this lab you load one real pretrained model, `google/ddpm-cifar10-32` (a 35.7M-parameter UNet that draws 32x32 CIFAR-10 images), and keep its weights fixed while you change only inference settings. You measure what a caller-chosen step count does to cost (200 steps took 6.5 to 9.3 times as long as 20 in two runs on a loaded machine, and the library default of 1000 DDPM steps cost fifty-one times a 20-step request), how solvers and step counts change the image from the same seed, and why a seed alone does not make a result reproducible. Then you look at the other half of a diffusers pipeline, the loader, where a "faster sampler" that ships its own `pipeline.py` runs its code at load time and prints the inert canary `ATLAS-CANARY-7f3a`. The defenses are a server-side cap with a per-client budget, a pinned and fingerprinted evaluation config, and a loading policy. Source: [`labs/concept-samplers`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/concept-samplers).

By the end you will be able to:

1. Swap DDPM, DDIM, DPM-Solver++ and Euler schedulers on one pretrained pipeline, show that the weights do not change, and measure the cost of a request in UNet calls and seconds.
2. Measure how step count and solver move the output from a fixed seed, and list the settings a reproducible diffusion evaluation must record besides the seed.
3. Apply and measure three controls: a step cap with a per-client budget of UNet calls, a fingerprinted evaluation manifest, and a pipeline loading policy (`DIFFUSERS_DISABLE_REMOTE_CODE`, `use_safetensors=True`, no `custom_pipeline`).

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The only code that runs on purpose is the shared inert payload `labkit.INERT_CODE` (the one LAB-01 and LAB-10 use), placed as the module body of a local `pipeline.py` in `work/hub/acme-ddpm-fast`; it writes `work/canary-marker.txt` and prints one line, whose text mentions `torch.load` because it is LAB-01's fixed string. The community-pipeline case replaces the download function with a stub, so nothing is fetched from the community mirror and no third-party code runs. The "costly" requests are ordinary sampling on your own CPU.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`concept-samplers`](../../articles/concept-samplers.md) |
| Family | None in the seed graph (a concept node). The front matter and explainer kicker use [`family-availability`](https://ai-security-atlas.github.io/?node=family-availability), the family of [`attack-sponge`](https://ai-security-atlas.github.io/?node=attack-sponge), whose cost amplification this lab measures at the sampler level. |
| Goal | None in the seed graph. The cost steps serve [`goal-availability`](https://ai-security-atlas.github.io/?node=goal-availability) (one request can cost fifty times another). |
| Access profile | `A19` Inference configuration control (caveat: *Sampling settings, system prompts and model weights are distinct privileges.*): Steps 3 and D1 give the caller only the scheduler name and step count, never the weights. Step 6 is a different privilege, the choice of what to load. |
| Read first | [`concept-noise`](https://ai-security-atlas.github.io/?node=concept-noise) (the node's prerequisite), [`arch-diffusion`](https://ai-security-atlas.github.io/?node=arch-diffusion) |
| Mitigated by | None in the seed graph. Defend uses [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget), [`eval-repro`](https://ai-security-atlas.github.io/?node=eval-repro) and [`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load) as related, not mapped. |
| Evaluated by | [`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost) (UNet calls and seconds per request), [`eval-repro`](https://ai-security-atlas.github.io/?node=eval-repro) |
| Related | [`tool-diffusers`](https://ai-security-atlas.github.io/?node=tool-diffusers) (practiced in Steps 2, 6 and D3), [`concept-decoding`](https://ai-security-atlas.github.io/?node=concept-decoding) (the language-model analogue), [`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency), [`format-safetensors`](https://ai-security-atlas.github.io/?node=format-safetensors) |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this concept node. Its article closes with the one that applies here: "Concrete comparisons between samplers, including efficiency and quality effects, belong to the cited sources rather than to assumption." This lab measures one 32x32 pixel-space model on one CPU; the cost ratios follow from the step counts, but the image distances are for this model and seed only.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | n/a | — | No step calls a model endpoint. The diffusion model runs inside the workbench, where the lab can count and time every UNet call. |
| host-ollama | n/a | — | Same: nothing is sent to a model server. |
| external-api | n/a | — | Same. A hosted image API would hide the step count and the scheduler, which is the point of D1. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU. Sampling runs on 4 threads (`SAMPLAB_THREADS` changes it). One UNet call on one 32x32 image took 0.1 s on the M4 Max during a lull in the load (D1) and 0.5–1.2 s while other heavy jobs ran on the same machine; every runtime below was measured under that load, so expect much faster runs on a quiet machine. |
| Docker VM memory | 4 GB (the UNet in float32 is 136 MiB). |
| Disk | Workbench image 2.2 GB; `google/ddpm-cifar10-32` safetensors 143 MB in the HF cache; diffusers installed from its 6.4 MB wheel (56 MB in `work/pydeps`) and the local test repos (about 290 MB, two copies of the weights) in `work/`. |
| Total time | About 60 min: about 20 min of commands, plus reading. Optional Step 7 adds 2–10 min. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-28 · Same weights, different answers](../concept-decoding/README.md) is the language-model version of the same idea (inference settings change behavior without touching weights), and [LAB-10](../attack-dependency/README.md) covers repository code that runs at load in `transformers`.
- Concepts to read first: [`concept-noise`](https://ai-security-atlas.github.io/?node=concept-noise) and [`arch-diffusion`](https://ai-security-atlas.github.io/?node=arch-diffusion).

## Explainer

```bash
# host
open concept-samplers/explainer/index.html        # macOS
# xdg-open concept-samplers/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in nine steps: the parts of a pipeline, a scheduler swap, the cost of a step count, solver accuracy, what a seed does and does not fix, a loader that runs repository code, and the three defenses.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=workbench` |
| host-ollama | `COMPOSE_PROFILES=workbench` |
| external-api | `COMPOSE_PROFILES=workbench` |
| none | `COMPOSE_PROFILES=workbench` |

This lab calls no model endpoint, so you can keep whichever backend block is active in `labs/.env`. The banner on every output prints that block's `LAB_BACKEND`; the Observe blocks below show `backend none`.

### Setup 2 — Build and start

**Do**

```bash
docker compose build workbench
docker compose up -d
```

**Observe**

```text
 Image atlas-labs/workbench:v3 Building
...
 Image atlas-labs/workbench:v3 Built
...
 Container atlas-labs-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image; the `workbench` profile starts one idle container.

### Setup 3 — Check the environment and install diffusers

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] concept-samplers · check_env.py · torch 2.14.1+cpu · backend none
[ok] work dir: /labs/concept-samplers/work (writable)
[ok] installed diffusers-0.42.1-py3-none-any.whl into work/pydeps (sha256 9154faa704ce, --require-hashes)
[ok] torch 2.14.1+cpu diffusers 0.42.1 (from concept-samplers/work/pydeps)
[ok] google/ddpm-cifar10-32 @ 267b167: UNet2DModel 35.7M parameters, scheduler DDPMScheduler
[ok] 4 CPU threads for sampling (set SAMPLAB_THREADS to change)
[skip] no model backend needed (every step runs on the local model)
```

What to notice: the workbench image has no diffusers, so this step installs one wheel with `--require-hashes` into `work/pydeps` (no dependencies; the image already has them) and refuses it if the file's sha256 differs from the pin. The model is fetched at a pinned revision and loaded from `.safetensors` only.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_pipeline | workbench | ≈15 s (+ download) | 1 |
| 2 | s02_swap | workbench | ≈1 min | 2 |
| 3 | s03_cost | workbench | ≈1–3 min | 3 |
| 4 | s04_solvers | workbench | ≈1–5 min | 4 |
| 5 | s05_seeds | workbench | ≈1–4 min | 5 |
| 6 | s06_loading | workbench | ≈25 s | 6 |
| 7 | s07_ddpm1000 (optional, slow) | workbench | ≈2–10 min | — |
| D1 | d1_cap_steps | workbench | ≈20 s | 7 |
| D2 | d2_pin_eval | workbench | ≈1–2 min | 8 |
| D3 | d3_load_policy | workbench | ≈40 s | 9 |

Runtimes are wall-clock times of one `docker compose run` each on the shared test machine, where the load average ranged from about 10 to over 100 during the reference run; the low end is closer to an idle machine. Most of each runtime is UNet calls, so a step's cost scales with the number of calls it prints.

### Step 1 — A pipeline is parts · [explainer 1](explainer/index.html#concept-samplers/1)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s01_pipeline.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s01_pipeline.py · torch 2.14.1+cpu · backend none
pipeline DDPMPipeline from google/ddpm-cifar10-32 @ 267b167 (use_safetensors=True, 2.7s)
  unet       UNet2DModel            35,746,307 parameters (136 MiB float32)
  scheduler  DDPMScheduler          no weights; config: num_train_timesteps=1000, beta_schedule=linear (0.0001..0.02), prediction_type=epsilon
repo files (hub listing; the loader fetched the configs and the .safetensors weights):
  config.json                                     699 bytes
  diffusion_pytorch_model.bin             143,101,489 bytes
  diffusion_pytorch_model.safetensors     143,020,084 bytes
  model_index.json                                180 bytes
  modeling_ddpm.py                              2,787 bytes
  scheduler_config.json                           256 bytes
model_index.json: _class_name='DDPMPipeline', _module='modeling_ddpm.py'
modules from modeling_ddpm.py imported by the default load: none
unet weights sha256 f2bb83da80bca8f2 (over all 328 tensors)
one UNet call (1 image, 32x32): 1165 ms median of 5 on 4 threads
a sample costs one UNet call per scheduler step; the scheduler decides how many steps
```

What to notice: all 35,746,307 learned parameters sit in the UNet, the scheduler is a 256-byte config with no weights, and one UNet call on one tiny image took 1.2 s on the loaded test machine (0.1 s in D1, when the load dropped). The repository also ships `modeling_ddpm.py`, which `model_index.json` names and the default load never imports.

**Why**

A diffusers pipeline bundles a trained denoiser (here a `UNet2DModel`) with a scheduler that decides which noise levels to visit and how to step between them; the scheduler is configuration, not learned weights ([`concept-samplers`](https://ai-security-atlas.github.io/?node=concept-samplers), built on the noise schedule of [`concept-noise`](https://ai-security-atlas.github.io/?node=concept-noise)). The model was trained on 1000 noise levels with a linear beta schedule, which every scheduler in this lab reuses. The `modeling_ddpm.py` file is a leftover from an early diffusers release; `model_index.json` still names it, but the stock `DDPMPipeline` class never imports it, which Step 6 contrasts with a pipeline that does ([`tool-diffusers`](https://ai-security-atlas.github.io/?node=tool-diffusers)).

### Step 2 — Swap the scheduler, keep the weights · [explainer 2](explainer/index.html#concept-samplers/2)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s02_swap.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s02_swap.py · torch 2.14.1+cpu · backend none
unet weights sha256 f2bb83da80bca8f2; seed 0; 20 steps each
sampler  class                         first timesteps            unet calls  seconds  pixel mean/std
ddpm     DDPMScheduler                 [950, 900, 850, 800, ...]          20     37.6   50.9/44.9
ddim     DDIMScheduler                 [950, 900, 850, 800, ...]          20     58.8   91.3/52.8
dpm++    DPMSolverMultistepScheduler   [999, 949, 899, 849, ...]          20     38.6   88.5/56.9
euler    EulerDiscreteScheduler        [999, 946, 893, 841, ...]          20     29.4   85.6/52.7
weights after four swaps: sha256 f2bb83da80bca8f2 -> unchanged
DDPMPipeline.__call__ with DDIM : RMSE 0.00 to the loop above (same loop)
DDPMPipeline.__call__ with Euler: RMSE 60.18 to the loop above, pixel std 17.1 (its loop skips init_noise_sigma and scale_model_input, which Euler needs)
wrote work/s02_grid.png (ddpm | ddim | dpm++ | euler, same seed)
```

What to notice: the weights hash is the same after four swaps. DDIM starts at t = 950 and DPM-Solver++ and Euler at 999, and each uses its own update rule, yet their pixel statistics are close (they draw the same car, see `work/s02_grid.png`), while DDPM at 20 steps is still mostly noise. Running Euler through `DDPMPipeline`'s own loop gives a flat image (pixel std 17.1), with no error raised.

**Why**

`pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)` is the documented way to change samplers in diffusers: the new scheduler inherits the training schedule and brings its own timestep spacing and update rule ([`tool-diffusers`](https://ai-security-atlas.github.io/?node=tool-diffusers)). DDPM (Ho et al.) adds fresh noise at every step and needs many steps; DDIM (Song et al.) and DPM-Solver++ (Lu et al.) take deterministic steps along the same path, so few steps already give a clean image ([`concept-samplers`](https://ai-security-atlas.github.io/?node=concept-samplers)). A scheduler swap is also an interface change: Euler expects the pipeline loop to scale its input, and `DDPMPipeline`'s loop does not, so the combination runs without an error and returns a washed-out image.

### Step 3 — The caller picks the step count, the server pays (≈1–3 min) · [explainer 3](explainer/index.html#concept-samplers/3)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s03_cost.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s03_cost.py · torch 2.14.1+cpu · backend none
same weights (sha256 f2bb83da80bca8f2), DDIM, seed 0, 4 threads
request                    unet calls  seconds  ms/call  x cost of 20 steps
DDIM 10 steps                      10      7.1      714                0.4x
DDIM 20 steps                      20     16.8      842                1.0x
DDIM 50 steps                      50     50.5     1010                3.0x
DDIM 200 steps                    200    156.4      782                9.3x
DDIM 20 steps, 4 images            20     12.3      616                0.7x
cost grows with the step count: 824 ms per UNet call on average over 280 calls
pass-through image API, server default DPM-Solver++ 20 steps:
  default (no fields)        ->   20 unet calls, about   16.5 s (1x the default)
  client: steps=200          ->  200 unet calls, about  164.9 s (10x the default)
  client: ddpm, steps=1000   -> 1000 unet calls, about  824.3 s (50x the default)
same weights and the same reply (one 32x32 image); only the inference settings changed
```

What to notice: with the weights unchanged, 200 steps took 9.3 times as long as 20 (156 s against 17 s), and the 1000-step DDPM request a client can ask for is 1000 UNet calls, 50 times the server default. The seconds swing with machine load (the 10-step run cost 714 ms per call, the 50-step run 1010 ms, and a review rerun measured 6.5x for 200 against 20 steps), while the call counts do not.

**Why**

Each step is one full forward pass of the UNet, so the cost of a sample is the step count times the cost of one call; the weights, the output size and the request body barely change ([`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost)). An image API that forwards `num_inference_steps` and the scheduler name from the client hands the caller a cost multiplier, which is the sponge idea of [`attack-sponge`](https://ai-security-atlas.github.io/?node=attack-sponge) ([LAB-43](../attack-sponge/README.md)) without any crafted input: the request is ordinary, only its settings are expensive. On this CPU a batch of four images took no longer than one (12.3 s against 16.8 s, inside the load noise), so the step count is the knob that matters here; on other hardware the batch size can count too.

### Step 4 — Steps and solvers change the picture (≈1–5 min) · [explainer 4](explainer/index.html#concept-samplers/4)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s04_solvers.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s04_solvers.py · torch 2.14.1+cpu · backend none
reference: ddim 100 steps, seed 0 (51s). RMSE to the reference (0 = same image):
sampler         5       10       20       50
ddim         26.6     11.3      7.5      4.1
dpm++        15.8      8.1      8.7        -
euler        46.1     21.9     13.7        -
ddpm            -        -     77.8     66.8
at 10 steps the closest deterministic solver is dpm++ (RMSE 8.1); DDPM at 50 steps is still 66.8 away (still noisy: the DDPM sampler is meant to run all 1000 training timesteps)
wrote work/s04_grid.png (reference | ddim 10 | dpm++ 10 | euler 10)
```

What to notice: at 10 steps DPM-Solver++ is closest to the 100-step reference (RMSE 8.1, against 11.3 for DDIM and 21.9 for Euler). DDIM and Euler move closer as steps grow, DPM-Solver++ levels off (8.7 at 20 steps), and DDPM is still 66.8 away at 50 steps because its picture is still noisy.

**Why**

DDIM, DPM-Solver++ and Euler are numerical solvers for the same deterministic path from noise to image (the probability-flow ODE); with more steps they all approach its endpoint, and a higher-order solver such as DPM-Solver++ gets close in fewer steps ([`concept-samplers`](https://ai-security-atlas.github.io/?node=concept-samplers)). DDPM's ancestral sampler injects new noise at each step and was designed for all 1000 training timesteps, so a short DDPM run leaves noise in the image. The reference is itself a DDIM approximation of that endpoint, so a different solver levels off at its own small gap instead of reaching 0, which is what DPM-Solver++ does between 10 and 20 steps. This is the trade the article describes, fewer steps for speed against more steps for fidelity, measured on one model and one seed; the distances do not transfer to other models.

### Step 5 — A seed is not the whole recipe (≈1–4 min) · [explainer 5](explainer/index.html#concept-samplers/5)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s05_seeds.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s05_seeds.py · torch 2.14.1+cpu · backend none
baseline: DDIM 20 steps, seed 0, pixels sha256 c454f2eaa751
change                                   identical   RMSE
DDIM 20, seed 0, run again                     yes    0.0
DDIM 20, seed 1                                 no   92.0
DPM-Solver++ 20, seed 0                         no    6.4
Euler 20, seed 0                                no    7.1
DDIM 20, timestep_spacing=trailing              no    1.8
DDIM 20, seed 0, batch of 2 (image 1)          yes    0.0
DDPM 20, seed 0                                 no   73.7
a new seed moves the image by RMSE 92.0. Byte-identical: 2 of 7 (DDIM 20, seed 0, run again; DDIM 20, seed 0, batch of 2 (image 1)). Same picture, other pixels: 3. DDPM from the same seed lands 73.7 away.
DDPM 20, seed 0 twice: identical True; as image 1 of a batch of 2: identical False (RMSE 74.2)
```

What to notice: only an exact rerun and a batch of two with DDIM reproduce the bytes. DPM-Solver++, Euler and a `timestep_spacing` change keep the same picture with RMSE 1.8 to 7.1, far below the 92.0 a new seed causes, and DDPM ends 73.7 away. With DDPM, the same seed in a batch of two gives a different first image (RMSE 74.2).

**Why**

The seed fixes the starting noise and, for stochastic samplers, every noise draw after it; the scheduler class, its config, the step count and the batch layout decide what happens to that noise ([`eval-repro`](https://ai-security-atlas.github.io/?node=eval-repro)). Deterministic solvers from the same seed agree on the picture but not on the bytes, so a regression test that compares pixel hashes breaks on a scheduler change, and a test that only eyeballs images misses one. DDPM draws its per-step noise for the whole batch at once, so the same seed gives a different image when the batch size changes.

### Step 6 — The loader can run repository code · [explainer 6](explainer/index.html#concept-samplers/6)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s06_loading.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s06_loading.py · torch 2.14.1+cpu · backend none
built work/hub/acme-ddpm-fast (pinned weights + pipeline.py) and work/hub/bin-only (weights as .bin)
diffusers 0.42.1; every case is DiffusionPipeline.from_pretrained(<folder>, ...)
acme-ddpm-fast, custom_pipeline=<repo>     refused: ValueError The directory <folder> contains custom code in pipeline.py which must be executed to correctly l
                                           marker: absent
  ... and trust_remote_code=True           loaded FastDDPMPipeline from diffusion_pytorch_model.safetensors
                                           [payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote /labs/concept-samplers/work/canary-marker.txt
                                           marker: FIRED ATLAS-CANARY-7f3a
custom_pipeline='lpw_stable_diffusion'     reached the community download (stubbed), trust_remote_code was False
                                           would fetch diffusers/community-pipelines-mirror v0.42.1/lpw_stable_diffusion.py
                                           marker: absent
bin-only, default loader                   loaded DDPMPipeline from diffusion_pytorch_model.bin
                                           marker: absent
bin-only, use_safetensors=True             refused: OSError Error no file named diffusion_pytorch_model.safetensors found in directory <folder>/unet.
                                           marker: absent
```

What to notice: without the trust flag diffusers refuses the local `pipeline.py`; with `trust_remote_code=True` the module body runs during `from_pretrained` and writes `ATLAS-CANARY-7f3a`. The bare community name reached the download step with `trust_remote_code=False`, and the bin-only folder loaded from pickle-based `.bin` weights until `use_safetensors=True` refused it.

**Why**

`custom_pipeline` makes diffusers import a Python file and use its class as the pipeline; for a local folder or a hub repo, diffusers 0.42 asks for `trust_remote_code=True` first, and once you pass it, the module body runs at load time ([`tool-diffusers`](https://ai-security-atlas.github.io/?node=tool-diffusers), the same trust decision as `from_pretrained(..., trust_remote_code=True)` in [`attack-dependency`](https://ai-security-atlas.github.io/?node=attack-dependency)). A bare name such as `lpw_stable_diffusion` is looked up in the community pipelines mirror, and that branch reached the download with `trust_remote_code=False`: in diffusers 0.42.1 `get_cached_module_file` checks the trust flag for local folders and hub repos only, so a real download would be imported next. Weights are a separate question: without `use_safetensors=True`, the loader falls back to a pickle-based `.bin`, which diffusers 0.42 opens with `torch.load(weights_only=True)`; the pickle risks of that path are the subject of [LAB-01](../attack-unsafe-load/README.md) ([`format-safetensors`](https://ai-security-atlas.github.io/?node=format-safetensors)).

### Step 7 — Run the 1000-step request for real (optional, slow) (≈2–10 min)

> [!TIP] Optional: later steps use the shipped result, so you can skip this.

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/s07_ddpm1000.py
```

**Observe**

```text
[atlas-lab] concept-samplers · s07_ddpm1000.py · torch 2.14.1+cpu · backend none
DPM-Solver++ 20 steps :   20 unet calls, 2.0 s and 14.8 s (before and after)
DDPM 1000 steps       : 1000 unet calls, 429.4 s
measured cost ratio   : 51x (UNet calls 50x)
same seed, RMSE between the two images: 71.9 (pixel std: DDPM 43.2, DPM-Solver++ 56.9)
wrote work/s07_pair.png (dpm++ 20 | ddpm 1000)
```

What to notice: the 1000-step DDPM request took 429 s, 51 times the average of the two 20-step DPM-Solver++ runs around it, which itself swung from 2.0 s to 14.8 s as the load on the test machine changed; from the same seed it drew a different picture (RMSE 71.9), since DDPM's random steps leave the deterministic path.

**Why**

Step 3 priced the 1000-step request from the measured cost per call; this step pays it once, back to back with the 20-step default so both see the same machine load ([`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost)). `DDPMPipeline.__call__` defaults to `num_inference_steps=1000`, so a server that calls `pipe()` without setting a step count runs the most expensive setting on every request ([`attack-sponge`](https://ai-security-atlas.github.io/?node=attack-sponge)).

## Defend

### Step D1 — Cap the settings on the server, then budget the volume · [explainer 7](explainer/index.html#concept-samplers/7)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/d1_cap_steps.py
```

**Observe**

```text
[atlas-lab] concept-samplers · d1_cap_steps.py · torch 2.14.1+cpu · backend none
cap: schedulers ['ddim', 'dpm++'], steps <= 50, images <= 4; measured 106 ms per UNet call
request                                                   pass-through   capped
{} (defaults)                                           20 calls ~    2 s   200 20 calls, 2.0 s
{"num_inference_steps": 50}                             50 calls ~    5 s   200 50 calls, 5.4 s
{"num_inference_steps": 51}                             51 calls ~    5 s   400 num_inference_steps 51 > 50
{"num_inference_steps": 200}                           200 calls ~   21 s   400 num_inference_steps 200 > 50
{"scheduler": "ddpm", "num_inference_steps": 1000}    1000 calls ~  106 s   400 scheduler 'ddpm' not allowed
total UNet calls: pass-through 1321, capped 70 (19x less work; capped requests took 7 s)
one client, 12 requests of 50 steps in a minute: every one passes the cap (600 UNet calls, 30x a default request)
with a budget of 200 UNet calls per client per minute: 4 accepted (200 calls), 8 rejected with 429
```

What to notice: the cap turns 1321 UNet calls for the five requests into 70, since the 51-step, 200-step and 1000-step DDPM requests are rejected before any work. Twelve requests of 50 steps all pass the cap, 600 calls in total, and the budget of 200 calls per minute accepts 4 and rejects 8.

**Why**

The cap is an allowlist on inference settings, checked before the first UNet call, so a rejected request costs nothing; it bounds the cost of one request ([`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget)). It does not bound how many requests a client sends, which is why the budget counts UNet calls per client per minute, the unit Step 3 showed cost is made of ([`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost)). Limitation: budgets bound cost per client, not across many clients or keys. [LAB-43](../attack-sponge/README.md) ([`attack-sponge`](https://ai-security-atlas.github.io/?node=attack-sponge)) measures the same cost amplification with crafted inputs to a language model and its serving limits.

### Step D2 — Pin the sampler for evaluation and fingerprint it (≈1–2 min) · [explainer 8](explainer/index.html#concept-samplers/8)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/d2_pin_eval.py
```

**Observe**

```text
[atlas-lab] concept-samplers · d2_pin_eval.py · torch 2.14.1+cpu · backend none
pinned manifest: DPMSolverMultistepScheduler, 20 steps, seed 0, batch 1, 4 threads, diffusers 0.42.1, weights f2bb83da80bca8f2
fingerprint f537be33e312, pixels sha256 4a4e5adaadf9
run                                fingerprint   gate              pixels        same image RMSE
same manifest, run again           f537be33e312  compare           4a4e5adaadf9  yes        0.0
same manifest, 1 thread            66f2e243dd1a  refuse to compare 4a4e5adaadf9  yes        0.0
solver_order=3 (config drift)      97195246d157  refuse to compare b0ac18c11762  no         2.1
DDIM instead of DPM-Solver++       c2bc8a9d60c5  refuse to compare c454f2eaa751  no         6.4
25 steps instead of 20             fa4399d9e277  refuse to compare 29991f2781b9  no         0.9
gate decisions that disagree with the pixels: 1 of 5
  same manifest, 1 thread: fingerprint differs but the image is identical
```

What to notice: every drifted run (a `solver_order` change, another scheduler, 25 steps) gets a different fingerprint and also different pixels, so the gate refuses each comparison correctly. The one disagreement is the thread-count row, where the fingerprint changed and the image did not.

**Why**

Record the scheduler class with its full config, the step count, the seed, the batch size, the thread count and the library versions next to the weights hash, and compare two runs only when that manifest matches ([`eval-repro`](https://ai-security-atlas.github.io/?node=eval-repro)). Each drift row here changed one inference setting and changed the pixels while the weights stayed fixed, so an evaluation without the manifest could blame or credit the model for a sampler change. Limitation: the fingerprint is conservative; it treats every listed field as significant, so it can refuse a comparison that would have matched, as the thread-count row shows.

### Step D3 — Load pipelines under a policy, then check the cache (≈40 s) · [explainer 9](explainer/index.html#concept-samplers/9)

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/d3_load_policy.py
```

**Observe**

```text
[atlas-lab] concept-samplers · d3_load_policy.py · torch 2.14.1+cpu · backend none
load                                     env only                   policy                    
acme-ddpm-fast, custom_pipeline=<repo>   refused: remote code off   refused                   
                                         policy: custom_pipeline is not allowed
  ... and trust_remote_code=True         refused: remote code off   refused                   
                                         policy: custom_pipeline is not allowed
custom_pipeline='lpw_stable_diffusion'   refused: remote code off   refused                   
                                         policy: custom_pipeline is not allowed
bin-only, default loader                 loaded .bin                refused: no safetensors   
acme-ddpm-fast, no custom_pipeline       loaded .safetensors        loaded .safetensors       
marker fired: env only 0, policy 0; pickle .bin loaded: env only 1, policy 0
modules cache /cache/hf/modules: 1 imported code file(s)
  /cache/hf/modules/diffusers_modules/local/pipeline.py  662 bytes  contains ATLAS-CANARY-7f3a
```

What to notice: the global switch alone stops all three code paths, the community name included, but still loads the pickle-based `.bin`; the policy refuses that too and loads the plain pipeline from safetensors. The modules cache still holds the copy of `pipeline.py` that ran in Step 6, with the canary inside.

**Why**

`DIFFUSERS_DISABLE_REMOTE_CODE=1` makes `get_cached_module_file`, the one function every custom-code load in this lab goes through, refuse to run, including the community-pipeline branch that Step 6 reached without a trust flag; the policy adds `use_safetensors=True`, which refuses pickle-based weights, and an allowlist of component classes in `model_index.json` ([`defense-safe-load`](https://ai-security-atlas.github.io/?node=defense-safe-load), [`tool-diffusers`](https://ai-security-atlas.github.io/?node=tool-diffusers)). The forensic check matters because code that ran once stays on disk: diffusers copies an imported `pipeline.py` into the HF modules cache. Limitation: the policy blocks the custom sampler outright; if you need one, review its code, vendor it into your own repository and pin it by hash, as [LAB-10](../attack-dependency/README.md) does for model code.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] concept-samplers · evaluate.py · torch 2.14.1+cpu · backend none
condition                              expected          got               measured
weights after scheduler swaps          unchanged         unchanged         f2bb83da80bc
DDIM 100 vs 10 steps · UNet calls      10x               10x               wall time 11.1x (46 s vs 4 s, drifts with load)
ddpm steps=1000 request · UNet calls   1000              1000              50x a 20-step request
seed 0 · DDIM 20 rerun                 identical         identical         RMSE 0.0
seed 0 · DPM-Solver++ vs DDIM 20       same picture      same picture      RMSE 6.4 (new seed 92.0)
seed 0 · DDPM vs DDIM 20               different         different         RMSE 73.7 (new seed 92.0)
capped API · default request           accepted          accepted          
capped API · steps=200                 rejected          rejected          400 num_inference_steps 200 > 50
capped API · ddpm steps=1000           rejected          rejected          400 scheduler 'ddpm' not allowed
custom pipeline · no trust flag        refused           refused           refused
custom pipeline · trust_remote_code    marker fired      marker fired      ATLAS-CANARY-7f3a
community name · no trust flag         reaches download  reaches download  diffusers/community-pipelines-mirror v0.42.1/lpw_stable_diffusion.py
remote code off + trust_remote_code    refused           refused           refused
bin-only · use_safetensors=True        refused           refused           refused
(127s)
RESULT: REPRODUCED
```

Rows: the weights hash after scheduler swaps; the DDIM 100-step against 10-step time ratio and the UNet calls of a 1000-step DDPM request; three same-seed comparisons graded against the distance a new seed moves the image; the capped API's decisions; and five loads in fresh processes. Each row is graded as a category; the measured column is the evidence and the timing ratio drifts with machine load within its band. `RESULT` says only whether the run matches the published shape in `expected/`.

Questions for your notes:

1. Your image API forwards `num_inference_steps` and nothing else. Which rows of Step 3 can a caller still reach, and what does D1's budget add on top of a cap?
2. A model update ships with "same weights, new default scheduler". Which D2 rows predict what your evaluation will see, and what would you record before rerunning it?
3. A model card asks for `custom_pipeline=...` and `trust_remote_code=True` to get a faster sampler. Which D3 control stops it, and what would you do instead if you need that sampler?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python concept-samplers/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] concept-samplers · cleanup.py · torch 2.14.1+cpu · backend none
[ok] removed concept-samplers/work (d1_cap_steps.json d2_pin_eval.json d3_load_policy.json evaluate.json hub/ pydeps/ requirements-diffusers.txt s01_pipeline.json s02_grid.png s02_swap.json s03_cost.json s04_grid.png s04_solvers.json s05_seeds.json s06_loading.json s07_ddpm1000.json)
[ok] removed 1 cached copy of this lab's pipeline.py from /cache/hf/modules (/cache/hf/modules/diffusers_modules/local/pipeline.py)
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> Cleanup deletes `work/pydeps`, so run Setup 3 again before you repeat any step. `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). The model stays in the HF cache volume until you do.

## Going Further

- Add `num_images` to D1's request list and measure whether batch size starts to matter on your hardware; on a GPU it usually does.
- Rerun Step 4 with `EulerAncestralDiscreteScheduler` or DDIM with `eta=1.0` (passed to `step()`), both stochastic, and compare their distance to the reference with DDPM's.
- Repeat Step 5 with `use_karras_sigmas=True` on DPM-Solver++, a common "quality" switch, and add it to D2's drift rows.
- Point D3's policy at a real diffusers repo you use and list every `.py` file it ships and every component class its `model_index.json` names.

## Further Reading

- Song, Meng and Ermon, [Denoising Diffusion Implicit Models](https://arxiv.org/abs/2010.02502) (2020), seed source `s-ddim` of this node: the deterministic DDIM sampler and why it can skip most timesteps.
- Lipman et al., [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747) (2022), seed source `s-flow` of this node: flow models are sampled by ODE solvers too, with the same steps-for-fidelity trade.
- Ho, Jain and Abbeel, [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239) (2020), seed source `s-ddpm` of `arch-diffusion`: the model family and the 1000-step ancestral sampler; `google/ddpm-cifar10-32` is its CIFAR-10 checkpoint.
- Lu et al., [DPM-Solver++: Fast Solver for Guided Sampling of Diffusion Probabilistic Models](https://arxiv.org/abs/2211.01095) (2022): the multistep solver behind `DPMSolverMultistepScheduler`.
- Karras et al., [Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364) (2022): samplers, schedules and the Euler-style solvers diffusers implements.
- Shumailov et al., [Sponge Examples: Energy-Latency Attacks on Neural Networks](https://arxiv.org/abs/2006.03463) (2021), seed source `s-sponge` of `attack-sponge`, `eval-cost` and `defense-budget`: inputs that raise inference cost.
- Hugging Face, [Diffusers documentation](https://huggingface.co/docs/diffusers/index), seed source `s-diffusers-lib` of `tool-diffusers`: [schedulers](https://huggingface.co/docs/diffusers/using-diffusers/schedulers), [community pipelines and `custom_pipeline`](https://huggingface.co/docs/diffusers/using-diffusers/custom_pipeline_overview), and [loading safetensors](https://huggingface.co/docs/diffusers/using-diffusers/other-formats).
- OWASP, [Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/), seed source `s-owasp25` of `defense-budget`: unbounded consumption.

---

[← prev](../concept-residual/README.md) · [All labs](../README.md) · [next →](../concept-context/README.md)
