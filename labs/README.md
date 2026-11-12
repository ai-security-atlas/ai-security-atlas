# AI Security Atlas · Hands-On Labs

Local, reproducible labs for selected [AI Security Atlas](https://ai-security-atlas.github.io/) nodes. Each lab reproduces one attack mechanism with real open-source tools in a Docker Compose sandbox on your own machine, measures it, and ends with a defense. Every lab follows the same page layout, and each one links back to its Atlas node and has an animated explainer.

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

## Start here

Every lab assumes these steps are done. Run all commands from this `labs/` folder.

1. Read [`requirements.md`](requirements.md) and pick a model backend (or none).
2. Copy the settings file and keep exactly one backend block uncommented (block a is active by default). On Linux, also set `LAB_UID`/`LAB_GID` (see the comments in the file). This file holds only the settings that every lab shares. Each lab's Setup 1 gives one `export` line for that lab's Compose project and profiles, which you run in the terminal you use for that lab.

   ```bash
   cp .env.example .env
   ```

3. Host Ollama only: start it and pull the models on the host.

   ```bash
   ollama pull qwen2.5vl:3b
   ollama pull moondream:1.8b
   ```

4. Build the workbench image once (a few minutes; later labs reuse it).

   ```bash
   docker compose build workbench
   ```

5. Open the first lab of the [learning path](#learning-path) below (or of a [workshop track](#workshop-tracks)) and follow its Setup.
6. To open a lab's explainer, run `open <id>/explainer/index.html` (macOS) or `xdg-open <id>/explainer/index.html` (Linux). The explainer step links in lab READMEs work in a local clone and on the Atlas site, where `/labs/<id>/` shows the explainer with the guide below it; on GitHub they show HTML source.

## Primers

The labs assume appsec, Docker, Python and HTTP, and no background in machine learning or statistics. Six short [primers](primers/README.md) define the terms the labs use, each under its own heading, and lab READMEs link a term to its definition the first time they use it:

- [Reading the numbers](primers/reading-the-numbers.md): rates, brackets, percentage points, release gates, kappa, AUC, p-values.
- [ML in one page](primers/ml-in-one-page.md): weights, logits, softmax, loss, gradients, the training loop, LoRA.
- [Sampling knobs](primers/sampling-knobs.md): greedy decoding, temperature, seed, top-k, top-p.
- [Vectors without the math](primers/vectors-without-the-math.md): norms, cosine similarity, embeddings, rank, SVD.
- [Inside a transformer block](primers/inside-a-transformer-block.md): attention, heads, MLP, residual stream, KV cache.
- [Diffusion in one paragraph](primers/diffusion-in-one-paragraph.md): noise, U-Net, schedulers, latents, guidance.

<!-- learning-path:begin (generated from learning-path.yaml by _tools/learning_path.py; do not edit by hand) -->

## Learning path

Take the labs in this order. Each module builds on the ones before it, and inside a module the labs build on each other. **Requires** lists the labs to finish first; every lab README repeats it under Prerequisites, and its prev/next links follow this order. The LAB number is only the order the labs were built in. Levels: *beginner* needs only appsec, Docker and Python; *intermediate* uses terms an earlier module teaches; *advanced* combines several modules.

### Module 0: Setup and orientation

About 30 min. Every laptop has the workbench image, the HF cache volume pre-seeded and, only for tracks that need one, a model backend. Read the payload-safety note and the Start here steps at the top of the labs index (`labs/README.md`). If ML or statistics terms are new to you, skim the [primers](primers/README.md): the labs link each term to its definition there. This module has no lab of its own.

### Module 1: A model is a file, and loading it runs code

About 2 h. Artifact trust: pickle, `trust_remote_code`, pinning to a sha256 and sandboxing. No backend and no ML needed, so it is the opener for an appsec audience.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | [LAB-01 · What torch.load really runs](attack-unsafe-load/README.md) | beginner | 60 min | none |
| 1.2 | [LAB-10 · from_pretrained ran my code](attack-dependency/README.md) | beginner | 75 min | [LAB-01](attack-unsafe-load/README.md) |

### Module 2: How a language model reads and writes text

About 6 h. Tokens, then scores, then sampling, then turns, then the context window. After this module logit, greedy, temperature, chat template and end-of-turn token are taught terms.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 2.1 | [LAB-04 · What the model actually reads](concept-tokens/README.md) | beginner | 45 min | none |
| 2.2 | [LAB-05 · What the API reveals](concept-logits/README.md) | intermediate | 60 min | [LAB-04](concept-tokens/README.md) |
| 2.3 | [LAB-28 · Same weights, different answers](concept-decoding/README.md) | intermediate | 75 min | [LAB-05](concept-logits/README.md) |
| 2.4 | [LAB-52 · Base vs instruct, and who speaks next](arch-decoder/README.md) | beginner | 60 min | [LAB-04](concept-tokens/README.md), [LAB-05](concept-logits/README.md), [LAB-28](concept-decoding/README.md) |
| 2.5 | [LAB-46 · What is in the window](concept-context/README.md) | beginner | 60 min | [LAB-04](concept-tokens/README.md), [LAB-52](arch-decoder/README.md) |

### Module 3: Prompt injection and measuring it honestly

About 4.5 h. The trust boundary between the system prompt and the user, attack success rate as a measurement, intervals, judges and release gates.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 3.1 | [LAB-06 · The support bot that forgot its job](attack-direct-injection/README.md) | beginner | 75 min | [LAB-04](concept-tokens/README.md) |
| 3.2 | [LAB-19 · Your system prompt is not a vault](attack-prompt-leak/README.md) | beginner | 60 min | [LAB-06](attack-direct-injection/README.md) |
| 3.3 | [LAB-12 · Measuring an attack honestly](eval-asr/README.md) | intermediate | 90 min | [LAB-06](attack-direct-injection/README.md) |

### Module 4: Retrieval and untrusted content

About 7 h. The retrieval pipeline as an attack surface: tenants and access checks, ingestion, content authors as a third party, and the places the output goes.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 4.1 | [LAB-11 · Five components of RAG](system-rag/README.md) | beginner | 60 min | [LAB-06](attack-direct-injection/README.md) |
| 4.2 | [LAB-41 · Who controls the corpus controls the context](system-index/README.md) | beginner | 45 min | [LAB-11](system-rag/README.md) |
| 4.3 | [LAB-42 · Whose data is this? Cross-tenant leaks in a chat app](attack-session-leak/README.md) | beginner | 45 min | [LAB-11](system-rag/README.md) |
| 4.4 | [LAB-15 · The email that wrote its own summary](attack-indirect-injection/README.md) | intermediate | 75 min | [LAB-06](attack-direct-injection/README.md), [LAB-11](system-rag/README.md), [LAB-12](eval-asr/README.md) |
| 4.5 | [LAB-20 · Your model's output is someone else's input](attack-output-sink/README.md) | beginner | 75 min | [LAB-15](attack-indirect-injection/README.md) |
| 4.6 | [LAB-03 · Instructions written on the picture](attack-multimodal-injection/README.md) | intermediate | 90 min | [LAB-06](attack-direct-injection/README.md), [LAB-15](attack-indirect-injection/README.md), [LAB-28](concept-decoding/README.md) |

### Module 5: Agents and tools

About 11 h. Tool surfaces, then tool-result injection, poisoned tool definitions, authority, persistence, multi-hop agents and cost.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 5.1 | [LAB-59 · What a tool really exposes](system-tools/README.md) | intermediate | 75 min | [LAB-06](attack-direct-injection/README.md) |
| 5.2 | [LAB-22 · When the tool's answer gives the orders](attack-tool-output/README.md) | intermediate | 90 min | [LAB-59](system-tools/README.md), [LAB-15](attack-indirect-injection/README.md) |
| 5.3 | [LAB-23 · The tool that told the agent what to do](attack-tool-description/README.md) | intermediate | 60 min | [LAB-22](attack-tool-output/README.md) |
| 5.4 | [LAB-30 · The agent that had the admin key](attack-confused-deputy/README.md) | intermediate | 50 min | [LAB-22](attack-tool-output/README.md) |
| 5.5 | [LAB-29 · A note to my future self](attack-memory-poison/README.md) | intermediate | 90 min | [LAB-22](attack-tool-output/README.md), [LAB-12](eval-asr/README.md) |
| 5.6 | [LAB-31 · Telephone game: when a peer's message becomes an order](attack-multiagent/README.md) | intermediate | 90 min | [LAB-22](attack-tool-output/README.md), [LAB-12](eval-asr/README.md) |
| 5.7 | [LAB-55 · The task that never ends](attack-agent-loop/README.md) | intermediate | 75 min | [LAB-22](attack-tool-output/README.md) |

### Module 6: Serving infrastructure

About 5.5 h. The model server, its cache, the model file format and the exposed API as an attack surface.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 6.1 | [LAB-14 · What the server adds](system-serving/README.md) | intermediate | 75 min | [LAB-04](concept-tokens/README.md) |
| 6.2 | [LAB-38 · The cache remembers](concept-kv-cache/README.md) | intermediate | 75 min | [LAB-14](system-serving/README.md) |
| 6.3 | [LAB-24 · Timing the prompt cache](attack-cache-sidechannel/README.md) | intermediate | 75 min | [LAB-14](system-serving/README.md), [LAB-38](concept-kv-cache/README.md) |
| 6.4 | [LAB-17 · GGUF is data, its template is code](format-gguf/README.md) | intermediate | 60 min | [LAB-04](concept-tokens/README.md), [LAB-14](system-serving/README.md) |
| 6.5 | [LAB-54 · An open Ollama port and a stolen fine-tune](attack-weight-theft/README.md) | intermediate | 25 min | [LAB-17](format-gguf/README.md) |

### Module 7: Gradients and adversarial ML on small classifiers

About 6.5 h. The training loop, input gradients, transfer, extraction, privacy and backdoors. Every step takes seconds to minutes on a CPU, with no model backend.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 7.1 | [LAB-50 · Gradients point both ways](concept-gradients/README.md) | intermediate | 60 min | [LAB-05](concept-logits/README.md) |
| 7.2 | [LAB-08 · One gradient step](attack-fgsm/README.md) | beginner | 60 min | [LAB-50](concept-gradients/README.md) |
| 7.3 | [LAB-56 · Does it transfer?](concept-transfer/README.md) | intermediate | 60 min | [LAB-50](concept-gradients/README.md), [LAB-08](attack-fgsm/README.md) |
| 7.4 | [LAB-09 · Stealing a classifier through its API](attack-model-imitation/README.md) | beginner | 60 min | [LAB-05](concept-logits/README.md) |
| 7.5 | [LAB-13 · Was this record in the training set?](attack-membership/README.md) | intermediate | 75 min | [LAB-05](concept-logits/README.md), [LAB-08](attack-fgsm/README.md), [LAB-12](eval-asr/README.md) |
| 7.6 | [LAB-18 · BadNets: a sticker that rewrites the label](attack-backdoor/README.md) | intermediate | 75 min | [LAB-08](attack-fgsm/README.md), [LAB-12](eval-asr/README.md) |

### Module 8: Fine-tuning and the adapter supply chain

About 9.5 h. What training changes, how poisoned data and substituted adapters get in, and why compressing a model does not remove the behavior.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 8.1 | [LAB-07 · What a 2 MB adapter changes](adapt-lora/README.md) | intermediate | 120 min | [LAB-01](attack-unsafe-load/README.md), [LAB-05](concept-logits/README.md), [LAB-50](concept-gradients/README.md) |
| 8.2 | [LAB-39 · Weights are what it is, activations are what it is doing](concept-parameters/README.md) | intermediate | 45 min | [LAB-07](adapt-lora/README.md), [LAB-50](concept-gradients/README.md) |
| 8.3 | [LAB-33 · Teach a tiny model a new habit](life-sft/README.md) | beginner | 90 min | [LAB-04](concept-tokens/README.md), [LAB-07](adapt-lora/README.md) |
| 8.4 | [LAB-16 · Poisoned demonstrations: 1% of an instruction set](attack-sft-poison/README.md) | intermediate | 120 min | [LAB-33](life-sft/README.md), [LAB-18](attack-backdoor/README.md), [LAB-12](eval-asr/README.md) |
| 8.5 | [LAB-60 · The adapter you didn't review](attack-adapter-tamper/README.md) | intermediate | 60 min | [LAB-01](attack-unsafe-load/README.md), [LAB-07](adapt-lora/README.md), [LAB-16](attack-sft-poison/README.md) |
| 8.6 | [LAB-35 · Smaller is not safer](transform-pruning/README.md) | advanced | 90 min | [LAB-18](attack-backdoor/README.md), [LAB-07](adapt-lora/README.md), [LAB-50](concept-gradients/README.md) |

### Module 9: Inside the transformer

About 10.5 h. Embeddings, attention, the residual stream and the checkpoint anatomy that later attacks touch.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 9.1 | [LAB-25 · Vectors that are not words](concept-embeddings/README.md) | intermediate | 60 min | [LAB-04](concept-tokens/README.md), [LAB-05](concept-logits/README.md), [LAB-50](concept-gradients/README.md) |
| 9.2 | [LAB-26 · Who attends to whom](concept-attention/README.md) | intermediate | 75 min | [LAB-04](concept-tokens/README.md), [LAB-25](concept-embeddings/README.md), [LAB-06](attack-direct-injection/README.md), [LAB-15](attack-indirect-injection/README.md) |
| 9.3 | [LAB-27 · Anatomy and forensics of a transformer checkpoint](arch-transformer/README.md) | advanced | 90 min | [LAB-26](concept-attention/README.md), [LAB-07](adapt-lora/README.md), [LAB-18](attack-backdoor/README.md) |
| 9.4 | [LAB-44 · Reading and writing the residual stream](concept-residual/README.md) | advanced | 60 min | [LAB-27](arch-transformer/README.md), [LAB-39](concept-parameters/README.md) |
| 9.5 | [LAB-34 · The guardrail is a model too](arch-encoder/README.md) | intermediate | 75 min | [LAB-26](concept-attention/README.md), [LAB-52](arch-decoder/README.md), [LAB-15](attack-indirect-injection/README.md) |
| 9.6 | [LAB-40 · Similarity is not relevance](arch-embedding/README.md) | intermediate | 50 min | [LAB-25](concept-embeddings/README.md), [LAB-11](system-rag/README.md) |
| 9.7 | [LAB-58 · A prompt you cannot read](adapt-softprompt/README.md) | intermediate | 60 min | [LAB-25](concept-embeddings/README.md), [LAB-26](concept-attention/README.md), [LAB-07](adapt-lora/README.md) |
| 9.8 | [LAB-37 · Reading the hidden size off the logits](attack-projection-theft/README.md) | advanced | 90 min | [LAB-05](concept-logits/README.md), [LAB-25](concept-embeddings/README.md), [LAB-09](attack-model-imitation/README.md), [LAB-52](arch-decoder/README.md) |

### Module 10: Data, evaluation integrity and preference training

About 9 h. Where training data and benchmark scores come from, and how comparisons get poisoned.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 10.1 | [LAB-32 · Duplicates get memorized](concept-memorization/README.md) | intermediate | 120 min | [LAB-07](adapt-lora/README.md), [LAB-13](attack-membership/README.md), [LAB-50](concept-gradients/README.md) |
| 10.2 | [LAB-47 · Lineage or it did not happen](life-data/README.md) | intermediate | 75 min | [LAB-33](life-sft/README.md), [LAB-32](concept-memorization/README.md) |
| 10.3 | [LAB-49 · Inflating a benchmark score and catching it](attack-eval-contamination/README.md) | intermediate | 90 min | [LAB-47](life-data/README.md), [LAB-13](attack-membership/README.md) |
| 10.4 | [LAB-48 · Grading the grader: steering an LLM judge](attack-judge-manipulation/README.md) | intermediate | 60 min | [LAB-12](eval-asr/README.md), [LAB-15](attack-indirect-injection/README.md) |
| 10.5 | [LAB-53 · Preferences shape the reward](life-preferences/README.md) | intermediate | 60 min | [LAB-33](life-sft/README.md), [LAB-25](concept-embeddings/README.md), [LAB-52](arch-decoder/README.md) |
| 10.6 | [LAB-57 · Preferences without a reward model](life-dpo/README.md) | intermediate | 75 min | [LAB-53](life-preferences/README.md), [LAB-07](adapt-lora/README.md) |

### Module 11: Optimization attacks on LLMs, guardrails and VLMs

About 8 h. The capstone: gradient-guided attacks on a language model, a guardrail classifier and a vision-language model, each with an adaptive retest of its defense.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 11.1 | [LAB-21 · Optimizing a suffix one token at a time](attack-gcg/README.md) | advanced | 120 min | [LAB-04](concept-tokens/README.md), [LAB-05](concept-logits/README.md), [LAB-25](concept-embeddings/README.md), [LAB-28](concept-decoding/README.md), [LAB-50](concept-gradients/README.md) |
| 11.2 | [LAB-43 · Inputs that cost more than they look](attack-sponge/README.md) | advanced | 90 min | [LAB-21](attack-gcg/README.md) |
| 11.3 | [LAB-36 · Slipping past a prompt-injection detector](attack-detector-evasion/README.md) | intermediate | 60 min | [LAB-34](arch-encoder/README.md), [LAB-08](attack-fgsm/README.md), [LAB-12](eval-asr/README.md) |
| 11.4 | [LAB-02 · Moving a VLM with invisible pixels](attack-visual-jailbreak/README.md) | advanced | 120 min | [LAB-08](attack-fgsm/README.md), [LAB-50](concept-gradients/README.md), [LAB-56](concept-transfer/README.md), [LAB-05](concept-logits/README.md) |

### Module 12: Text-to-image models (elective)

About 2 h. How a diffusion pipeline turns a prompt into an image, and what its loading code and sampler settings expose.

| Order | Lab | Level | Time | Requires |
| :--- | :--- | :--- | :--- | :--- |
| 12.1 | [LAB-45 · Same weights, ten times the cost](concept-samplers/README.md) | intermediate | 60 min | [LAB-01](attack-unsafe-load/README.md), [LAB-10](attack-dependency/README.md) |
| 12.2 | [LAB-51 · The prompt is a vector](concept-conditioning/README.md) | intermediate | 45 min | [LAB-04](concept-tokens/README.md), [LAB-25](concept-embeddings/README.md), [LAB-26](concept-attention/README.md) |

## Workshop tracks

Two ready-made selections for a facilitator. Both need only the workbench image on the main path.

### Track A: Models are code, models are math

3.5-4 h conference workshop. No model backend, no external API, CPU only, one shared image plus less than 1 GB of extra model files, all handed out on USB before the session.

| Time | Block | Notes |
| :--- | :--- | :--- |
| 0:00-0:20 | Module 0: load the image tarball and run `check_env` | Fallback: the facilitator's `docker save` tarball on USB |
| 0:20-1:15 | [LAB-01 · What torch.load really runs](attack-unsafe-load/README.md) (Steps 1-7, D1, D2) | No ML needed; the strongest opener |
| 1:15-2:00 | [LAB-04 · What the model actually reads](concept-tokens/README.md) | SmolLM2-360M (724 MB), pre-seeded into `hf-cache` |
| 2:00-2:10 | Break |  |
| 2:10-2:45 | [LAB-20 · Your model's output is someone else's input](attack-output-sink/README.md) (the fixed-output path) | Offline; skip the live Step 4 |
| 2:45-3:45 | [LAB-08 · One gradient step](attack-fgsm/README.md) | Bundled dataset, seconds per step. LAB-50 is not in this track, so give the gradient primer first |
| +40 min (4 h slot) | [LAB-09 · Stealing a classifier through its API](attack-model-imitation/README.md) | The victim API runs on loopback |

### Track B: One day

About 6.5 h of lab time. Morning: Modules 1 and 2, light. Afternoon: Module 7 plus a bridge. No model backend on the main path.

| Time | Block | Notes |
| :--- | :--- | :--- |
| Morning, 60 min | [LAB-01 · What torch.load really runs](attack-unsafe-load/README.md) |  |
| Morning, 50 min | [LAB-10 · from_pretrained ran my code](attack-dependency/README.md) |  |
| Morning, 45 min | [LAB-04 · What the model actually reads](concept-tokens/README.md) |  |
| Morning, 50 min | [LAB-05 · What the API reveals](concept-logits/README.md) (Steps 1-4) | Step 5 (SVD) is optional reading |
| Afternoon, 60 min | [LAB-50 · Gradients point both ways](concept-gradients/README.md) |  |
| Afternoon, 50 min | [LAB-08 · One gradient step](attack-fgsm/README.md) |  |
| Afternoon, 70 min | [LAB-18 · BadNets: a sticker that rewrites the label](attack-backdoor/README.md) |  |
| Afternoon, 40 min | [LAB-20 · Your model's output is someone else's input](attack-output-sink/README.md) |  |

Optional LLM-app variant, only if the facilitator has checked host Ollama with `qwen2.5:3b` already pulled on every laptop (Apple Silicon or a GPU): replace LAB-50 and LAB-18 with LAB-06 (`--trials 3`, skip Step 4) and LAB-19 (`--trials 3`). Do not use container Ollama on a CPU in a workshop.

<!-- learning-path:end -->

## All labs by build number (LAB id)

The LAB number is the order the labs were built in. To learn, follow the [learning path](#learning-path) above.

Progress: 60 of 100 planned labs built (every Atlas node gets its own lab, steps in a lab, or a hub page). The plan, by wave, is in [`docs/labs-roadmap.md`](https://github.com/ai-security-atlas/ai-security-atlas/blob/main/docs/labs-roadmap.md).

| LAB | Lab | Atlas node | Family | Level | Model backend | Time | Explainer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| LAB-01 | [What torch.load really runs](attack-unsafe-load/README.md) | attack-unsafe-load | family-supply | beginner | none | 60 min | `attack-unsafe-load/explainer/index.html` |
| LAB-02 | [Moving a VLM with invisible pixels](attack-visual-jailbreak/README.md) | attack-visual-jailbreak | family-evasion | advanced | optional | 120 min | `attack-visual-jailbreak/explainer/index.html` |
| LAB-03 | [Instructions written on the picture](attack-multimodal-injection/README.md) | attack-multimodal-injection | family-prompt | intermediate | required | 90 min | `attack-multimodal-injection/explainer/index.html` |
| LAB-04 | [What the model actually reads](concept-tokens/README.md) | concept-tokens | family-prompt | beginner | none | 45 min | `concept-tokens/explainer/index.html` |
| LAB-05 | [What the API reveals](concept-logits/README.md) | concept-logits | family-theft | intermediate | optional | 60 min | `concept-logits/explainer/index.html` |
| LAB-06 | [The support bot that forgot its job](attack-direct-injection/README.md) | attack-direct-injection | family-prompt | beginner | required | 75 min | `attack-direct-injection/explainer/index.html` |
| LAB-07 | [What a 2 MB adapter changes](adapt-lora/README.md) | adapt-lora | family-training | intermediate | none | 120 min | `adapt-lora/explainer/index.html` |
| LAB-08 | [One gradient step](attack-fgsm/README.md) | attack-fgsm | family-evasion | beginner | none | 60 min | `attack-fgsm/explainer/index.html` |
| LAB-09 | [Stealing a classifier through its API](attack-model-imitation/README.md) | attack-model-imitation | family-theft | beginner | none | 60 min | `attack-model-imitation/explainer/index.html` |
| LAB-10 | [from_pretrained ran my code](attack-dependency/README.md) | attack-dependency | family-supply | beginner | none | 75 min | `attack-dependency/explainer/index.html` |
| LAB-11 | [Five components of RAG](system-rag/README.md) | system-rag | family-retrieval | beginner | required | 60 min | `system-rag/explainer/index.html` |
| LAB-12 | [Measuring an attack honestly](eval-asr/README.md) | eval-asr | family-prompt | intermediate | required | 90 min | `eval-asr/explainer/index.html` |
| LAB-13 | [Was this record in the training set?](attack-membership/README.md) | attack-membership | family-privacy | intermediate | none | 75 min | `attack-membership/explainer/index.html` |
| LAB-14 | [What the server adds](system-serving/README.md) | system-serving | family-privacy | intermediate | none | 75 min | `system-serving/explainer/index.html` |
| LAB-15 | [The email that wrote its own summary](attack-indirect-injection/README.md) | attack-indirect-injection | family-prompt | intermediate | required | 75 min | `attack-indirect-injection/explainer/index.html` |
| LAB-16 | [Poisoned demonstrations: 1% of an instruction set](attack-sft-poison/README.md) | attack-sft-poison | family-poisoning | intermediate | none | 120 min | `attack-sft-poison/explainer/index.html` |
| LAB-17 | [GGUF is data, its template is code](format-gguf/README.md) | format-gguf | family-supply | intermediate | none | 60 min | `format-gguf/explainer/index.html` |
| LAB-18 | [BadNets: a sticker that rewrites the label](attack-backdoor/README.md) | attack-backdoor | family-poisoning | intermediate | none | 75 min | `attack-backdoor/explainer/index.html` |
| LAB-19 | [Your system prompt is not a vault](attack-prompt-leak/README.md) | attack-prompt-leak | family-prompt | beginner | required | 60 min | `attack-prompt-leak/explainer/index.html` |
| LAB-20 | [Your model's output is someone else's input](attack-output-sink/README.md) | attack-output-sink | family-agent | beginner | optional | 75 min | `attack-output-sink/explainer/index.html` |
| LAB-21 | [Optimizing a suffix one token at a time](attack-gcg/README.md) | attack-gcg | family-prompt | advanced | optional | 120 min | `attack-gcg/explainer/index.html` |
| LAB-22 | [When the tool's answer gives the orders](attack-tool-output/README.md) | attack-tool-output | family-agent | intermediate | required | 90 min | `attack-tool-output/explainer/index.html` |
| LAB-23 | [The tool that told the agent what to do](attack-tool-description/README.md) | attack-tool-description | family-agent | intermediate | required | 60 min | `attack-tool-description/explainer/index.html` |
| LAB-24 | [Timing the prompt cache](attack-cache-sidechannel/README.md) | attack-cache-sidechannel | family-privacy | intermediate | optional | 75 min | `attack-cache-sidechannel/explainer/index.html` |
| LAB-25 | [Vectors that are not words](concept-embeddings/README.md) | concept-embeddings | family-prompt | intermediate | none | 60 min | `concept-embeddings/explainer/index.html` |
| LAB-26 | [Who attends to whom](concept-attention/README.md) | concept-attention | family-prompt | intermediate | none | 75 min | `concept-attention/explainer/index.html` |
| LAB-27 | [Anatomy and forensics of a transformer checkpoint](arch-transformer/README.md) | arch-transformer | family-representation | advanced | none | 90 min | `arch-transformer/explainer/index.html` |
| LAB-28 | [Same weights, different answers](concept-decoding/README.md) | concept-decoding | family-prompt | intermediate | optional | 75 min | `concept-decoding/explainer/index.html` |
| LAB-29 | [A note to my future self](attack-memory-poison/README.md) | attack-memory-poison | family-agent | intermediate | required | 90 min | `attack-memory-poison/explainer/index.html` |
| LAB-30 | [The agent that had the admin key](attack-confused-deputy/README.md) | attack-confused-deputy | family-agent | intermediate | required | 50 min | `attack-confused-deputy/explainer/index.html` |
| LAB-31 | [Telephone game: when a peer's message becomes an order](attack-multiagent/README.md) | attack-multiagent | family-agent | intermediate | required | 90 min | `attack-multiagent/explainer/index.html` |
| LAB-32 | [Duplicates get memorized](concept-memorization/README.md) | concept-memorization | family-privacy | intermediate | none | 120 min | `concept-memorization/explainer/index.html` |
| LAB-33 | [Teach a tiny model a new habit](life-sft/README.md) | life-sft | family-poisoning | beginner | none | 90 min | `life-sft/explainer/index.html` |
| LAB-34 | [The guardrail is a model too](arch-encoder/README.md) | arch-encoder | family-prompt | intermediate | none | 75 min | `arch-encoder/explainer/index.html` |
| LAB-35 | [Smaller is not safer](transform-pruning/README.md) | transform-pruning | family-training | advanced | none | 90 min | `transform-pruning/explainer/index.html` |
| LAB-36 | [Slipping past a prompt-injection detector](attack-detector-evasion/README.md) | attack-detector-evasion | family-evasion | intermediate | optional | 60 min | `attack-detector-evasion/explainer/index.html` |
| LAB-37 | [Reading the hidden size off the logits](attack-projection-theft/README.md) | attack-projection-theft | family-theft | advanced | none | 90 min | `attack-projection-theft/explainer/index.html` |
| LAB-38 | [The cache remembers](concept-kv-cache/README.md) | concept-kv-cache | family-privacy | intermediate | none | 75 min | `concept-kv-cache/explainer/index.html` |
| LAB-39 | [Weights are what it is, activations are what it is doing](concept-parameters/README.md) | concept-parameters | family-representation | intermediate | none | 45 min | `concept-parameters/explainer/index.html` |
| LAB-40 | [Similarity is not relevance](arch-embedding/README.md) | arch-embedding | family-retrieval | intermediate | none | 50 min | `arch-embedding/explainer/index.html` |
| LAB-41 | [Who controls the corpus controls the context](system-index/README.md) | system-index | family-retrieval | beginner | none | 45 min | `system-index/explainer/index.html` |
| LAB-42 | [Whose data is this? Cross-tenant leaks in a chat app](attack-session-leak/README.md) | attack-session-leak | family-privacy | beginner | optional | 45 min | `attack-session-leak/explainer/index.html` |
| LAB-43 | [Inputs that cost more than they look](attack-sponge/README.md) | attack-sponge | family-availability | advanced | optional | 90 min | `attack-sponge/explainer/index.html` |
| LAB-44 | [Reading and writing the residual stream](concept-residual/README.md) | concept-residual | family-representation | advanced | none | 60 min | `concept-residual/explainer/index.html` |
| LAB-45 | [Same weights, ten times the cost](concept-samplers/README.md) | concept-samplers | family-availability | intermediate | none | 60 min | `concept-samplers/explainer/index.html` |
| LAB-46 | [What is in the window](concept-context/README.md) | concept-context | family-prompt | beginner | optional | 60 min | `concept-context/explainer/index.html` |
| LAB-47 | [Lineage or it did not happen](life-data/README.md) | life-data | family-poisoning | intermediate | none | 75 min | `life-data/explainer/index.html` |
| LAB-48 | [Grading the grader: steering an LLM judge](attack-judge-manipulation/README.md) | attack-judge-manipulation | family-evaluation | intermediate | required | 60 min | `attack-judge-manipulation/explainer/index.html` |
| LAB-49 | [Inflating a benchmark score and catching it](attack-eval-contamination/README.md) | attack-eval-contamination | family-evaluation | intermediate | none | 90 min | `attack-eval-contamination/explainer/index.html` |
| LAB-50 | [Gradients point both ways](concept-gradients/README.md) | concept-gradients | family-evasion | intermediate | none | 60 min | `concept-gradients/explainer/index.html` |
| LAB-51 | [The prompt is a vector](concept-conditioning/README.md) | concept-conditioning | family-misuse | intermediate | none | 45 min | `concept-conditioning/explainer/index.html` |
| LAB-52 | [Base vs instruct, and who speaks next](arch-decoder/README.md) | arch-decoder | family-prompt | beginner | optional | 60 min | `arch-decoder/explainer/index.html` |
| LAB-53 | [Preferences shape the reward](life-preferences/README.md) | life-preferences | family-training | intermediate | none | 60 min | `life-preferences/explainer/index.html` |
| LAB-54 | [An open Ollama port and a stolen fine-tune](attack-weight-theft/README.md) | attack-weight-theft | family-theft | intermediate | none | 25 min | `attack-weight-theft/explainer/index.html` |
| LAB-55 | [The task that never ends](attack-agent-loop/README.md) | attack-agent-loop | family-availability | intermediate | required | 75 min | `attack-agent-loop/explainer/index.html` |
| LAB-56 | [Does it transfer?](concept-transfer/README.md) | concept-transfer | family-evasion | intermediate | none | 60 min | `concept-transfer/explainer/index.html` |
| LAB-57 | [Preferences without a reward model](life-dpo/README.md) | life-dpo | family-training | intermediate | none | 75 min | `life-dpo/explainer/index.html` |
| LAB-58 | [A prompt you cannot read](adapt-softprompt/README.md) | adapt-softprompt | family-training | intermediate | none | 60 min | `adapt-softprompt/explainer/index.html` |
| LAB-59 | [What a tool really exposes](system-tools/README.md) | system-tools | family-agent | intermediate | required | 75 min | `system-tools/explainer/index.html` |
| LAB-60 | [The adapter you didn't review](attack-adapter-tamper/README.md) | attack-adapter-tamper | family-training | intermediate | none | 60 min | `attack-adapter-tamper/explainer/index.html` |

## Folder layout and template

Each lab lives in a folder named after its Atlas node id and follows [`_template/`](_template/README.md) exactly: the same front matter, the same sections, and the same **Do** / **Observe** / **Why** step blocks. Shared pieces are [`compose.yaml`](compose.yaml) (profiles `ollama`, `chat`, `workbench`, `supply`), the [`workbench/`](workbench/) image, `_shared/labkit.py` (paths, banner, canaries) and the explainer engine in `_explainer/`.

Committed model weights (small LoRA adapters and digit classifiers) and their upstream licenses are listed in [`NOTICE.md`](NOTICE.md).

Maintainer tools (host Python 3.9 or newer, standard library only, run from the repository root):

| Command | What it does |
| :--- | :--- |
| `python3 labs/_tools/lint_readme.py [<node-id>]` | Checks every lab README against the template (front matter, section order, step blocks, explainer links, `expected/checks.txt` step ids, Atlas node ids, explainer commands, `covers:` nodes, steps and anchors) and fails if a pickle or torch archive under `labs/` is tracked by git. It also runs `learning_path.py --check`. |
| `python3 labs/_tools/learning_path.py [--check \| --write]` | Validates [`learning-path.yaml`](learning-path.yaml) (every lab once, no forward or circular prerequisites, levels match the front matter). `--write` regenerates each lab's Learning path line, its "Labs to finish first", "Recommended first" and "Later in the path" lines, its prev/next footer, and the Learning path section above. Edit the YAML, never those lines. |
| `python3 labs/_tools/verify.py <node-id>` | Runs the lab README's Do blocks in order, exactly as a student would, writes `labs/<node-id>/work/verify.log`, and checks each step's output against `expected/checks.txt`. It uses `LAB_BACKEND` from `labs/.env` to pick the profiles, skips backend-tagged steps when no backend is set, and runs slow steps only with `VERIFY_SLOW=1`. |
| `python3 labs/_shared/test_inert.py` | Payload review: checks the inert LAB-01 payload against an AST allowlist, and checks that `exec`, `eval` and `__reduce__` appear only in the payload-site scripts. |
