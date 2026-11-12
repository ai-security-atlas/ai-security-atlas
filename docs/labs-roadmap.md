# Hands-on labs roadmap

**Status:** living plan, generated 2026-10-26 from a four-agent classification of all 216 Atlas nodes (machine-readable: [`labs-roadmap.json`](labs-roadmap.json)). Update it at the end of every wave.

**Goal:** close to one lab per node, so every Atlas topic has theory (the article) and practice (a lab). Lab pattern, stack and safety rules: [`labs-spec.md`](labs-spec.md) and [`../labs/README.md`](../labs/README.md).

## How every node gets practice

- **Own lab (100 nodes, 60 done):** a dedicated lab in `labs/<node-id>/`, following the template. Attacks use the 5 explainer chapters as written. Methods, concepts, architectures, components, lifecycle stages and formats are *foundation labs*: the same 5 chapters, read as System → Risk → Mechanism → Observation → Defense.
- **Covered (88 nodes):** practiced as named steps inside a host lab (mostly defenses and evaluations inside the attack lab they mitigate or measure). The host lab lists them in its front matter (`covers:` with step anchors) and the site shows a "Practiced in LAB-NN · Step X" badge on the covered node.
- **Hub (28 nodes):** goals, families and umbrella nodes. Their page links the member labs and the foundation labs to do first; no lab of their own.

## Shared fixtures (build once, reuse everywhere)

Each fixture is created by the first lab that needs it (its *founding* lab) and then reused. Shared images: **workbench v4** (adds peft, accelerate, scikit-learn, fastapi/uvicorn, opacus, adversarial-robustness-toolbox, nanogcg, sqlglot, bleach, jinja2, gguf and qrcode) and **atlas-app v3** (chromadb, onnxruntime, mcp).

| Fixture | What it is |
| :--- | :--- |
| `atlas-app` | One FastAPI app with an OpenAI-compatible endpoint (so Open WebUI can chat with it): a fictional product assistant with a system prompt, tenants, a chromadb RAG index with ACL metadata, MCP tools over a mock world (mail, tickets, ledger, memory), an audit log and a replay mode for deterministic verification. New compose profile `rag-agent` on a slim (no torch) image. Founded by LAB-06 attack-direct-injection; RAG by system-rag; MCP by attack-tool-output. |
| `fixture-web` | Local-only poisoned web pages/docs plus a canary request collector, reachable only on the compose network. Founded by attack-indirect-injection. |
| `tinylm` | Tiny language models (SmolLM2-135M/360M, Qwen2.5-0.5B) with a CPU LoRA/SFT harness (peft), probe/steer/ablate helpers, and the stand-in refusal policy (a fictional "Project Lantern" vault the model refuses to reveal) so jailbreak, safety-finetune and ablation labs never need harmful content. Founded by LAB-07 adapt-lora. |
| `vision-zoo` | Small CNN/MLP classifiers on a tiny dataset with clean and backdoored checkpoints (safetensors), for FGSM/PGD, backdoor, membership, pruning, physical. Founded by LAB-08 attack-fgsm. |
| `victim-api` | A mock model API with selectable response detail (label, top-k, logprobs, embeddings) and query budgets, for theft and privacy labs. Founded by LAB-09 attack-model-imitation. |
| `local-hub` | LAB-01's bare-git model hub generalized into labs/_shared (repos, tags, revisions, remote code). Founded by LAB-10 attack-dependency. |
| `serving` | llama.cpp server compose profile (pinned image; convert/quantize/serve GGUF; slots, metrics, budgets). Founded by system-serving. |
| `evalkit` | Shared measurement library in labs/_shared: trials with seeds, confidence intervals, strict/loose graders, LLM-judge, cost, run manifests, release gate. Founded by eval-asr; every later evaluate.py uses it. |
| `toy-gen-kit` | Tiny diffusion/VAE models trained on a synthetic dataset (shipped as safetensors) for diffusion, latent, sampler and guidance labs. |
| `gateway` | LiteLLM proxy profile for budgets/quotas in availability labs. |

## Wave 1 (built 2026-10-29): foundations and fixture founders

| LAB | Node | Lab | Stack | Model backend | Effort | Founds |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| LAB-03 | `attack-multimodal-injection` | Instructions written on the picture | chat (+ workbench for scripts) | required | M |  |
| LAB-04 | `concept-tokens` | What the model actually reads | workbench | none | S |  |
| LAB-05 | `concept-logits` | What the API reveals | workbench | optional | S |  |
| LAB-06 | `attack-direct-injection` | The support bot that forgot its job | chat + new 'rag-agent' (lab-app service) | required | M | atlas-app |
| LAB-07 | `adapt-lora` | What a 2 MB adapter changes | workbench | none | M | tinylm |
| LAB-08 | `attack-fgsm` | One gradient step: FGSM on a digit classifier | workbench | none | S | vision-zoo |
| LAB-09 | `attack-model-imitation` | Stealing a classifier through its API | workbench (victim-api runs inside it or as a sibling service) | none | S | victim-api |
| LAB-10 | `attack-dependency` | from_pretrained ran my code: remote code, packages and plugins | supply | none | M | local-hub |

## Wave 2 (LAB-11 to LAB-22 built 2026-10-30 to 2026-11-01): first users of the fixtures

| Node | Lab | Stack | Model backend | Effort |
| :--- | :--- | :--- | :--- | :--- |
| `system-rag` | Five components of RAG | rag-agent (new) | required | M |
| `attack-indirect-injection` | The email that wrote its own summary | chat + rag-agent | required | M |
| `attack-prompt-leak` | Your system prompt is not a vault | chat + rag-agent | required | S |
| `attack-output-sink` | Your model's output is someone else's input | rag-agent | optional | M |
| `eval-asr` | Measuring an attack honestly | chat (Ollama) + workbench | required | M |
| `attack-membership` | Was this record in the training set? | workbench | none | M |
| `attack-sft-poison` | Poisoned demonstrations: 1% of an instruction set | workbench | none | M |
| `system-serving` | What the server adds | serving (new) + workbench | none | M |
| `format-gguf` | GGUF is data, its template is code | serving (new) + workbench | none | M |
| `attack-gcg` | Optimizing a suffix one token at a time | workbench | optional | L |
| `attack-tool-output` | When the tool's answer gives the orders | rag-agent | required | M |
| `attack-backdoor` | BadNets: a sticker that rewrites the label | workbench | none | M |

Wave 2 founds `fixture-web` (attack-indirect-injection), `serving` (system-serving) and `evalkit` (eval-asr), and extends `atlas-app` with RAG (system-rag) and MCP tools (attack-tool-output). Later waves are planned from the backlog below at the end of each wave, grouped by fixture.

## Every node

| Node | Type | Practice | Lab title (own labs) | Stack | Backend | Effort | Wave |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `goal-actions` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-availability` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-behavior` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-decisions` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-environment` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-evasion` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-information` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-misuse` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-model-theft` | goal | hub (links member labs) |  |  |  |  |  |
| `goal-persistence` | goal | hub (links member labs) |  |  |  |  |  |
| `family-agent` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-availability` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-evaluation` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-evasion` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-misuse` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-poisoning` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-privacy` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-prompt` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-representation` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-retrieval` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-supply` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-theft` | technique_family | hub (links member labs) |  |  |  |  |  |
| `family-training` | technique_family | hub (links member labs) |  |  |  |  |  |
| `attack-adapter-tamper` | attack | own lab (LAB-60) | The adapter you didn't review | workbench | none | M | done |
| `attack-agent-loop` | attack | own lab (LAB-55) | The task that never ends | rag-agent (+ gateway) | required | S | done |
| `attack-artifact-substitution` | attack | in `attack-unsafe-load` (LAB-01): steps 8, D1 |  |  |  |  | done |
| `attack-attribute` | attack | own lab (—) | Inversion, prototypes and attribute inference: three different outcomes | workbench | none | S | backlog |
| `attack-audio-injection` | attack | in `attack-physical`: Walkthrough step: compare visual adversarial patches with waveform / psychoacoustic … |  |  |  |  | with host |
| `attack-backdoor` | attack | own lab (LAB-18) | BadNets: a sticker that rewrites the label | workbench | none | M | done |
| `attack-cache-sidechannel` | attack | own lab (LAB-24) | Timing the prompt cache | new: serving (llama.cpp server) + workbench | optional | M | done |
| `attack-capability-abuse` | attack | hub (links member labs) |  |  |  |  |  |
| `attack-citation-launder` | attack | in `attack-rag-poison`: Walkthrough step 'Borrowed authority' (poisoned doc impersonates a citation to a fic… |  |  |  |  | with host |
| `attack-confused-deputy` | attack | own lab (LAB-30) | The agent that had the admin key | rag-agent | required | M | done |
| `attack-constrained-decoding-bypass` | attack | in `attack-jailbreak`: Walkthrough step: apply a caller-supplied JSON schema / grammar logit mask that supp… |  |  |  |  | with host |
| `attack-cot-hijack` | attack | in `attack-jailbreak`: Walkthrough step: prefill and spoof intermediate <think> safety reasoning steps (H-C… |  |  |  |  | with host |
| `attack-cross-server-shadowing` | attack | in `attack-tool-description`: Walkthrough step: untrusted MCP server docstring shadows or redirects calls to a tru… |  |  |  |  | with host |
| `attack-dependency` | attack | own lab (LAB-10) | from_pretrained ran my code | supply | none | M | done |
| `attack-detector-evasion` | attack | own lab (LAB-36) | Slipping past a prompt-injection detector | workbench (+ chat for the optional functionality step) | optional | M | done |
| `attack-diffusion-backdoor` | attack | own lab (—) | A trigger in the noise: backdooring a tiny diffusion model | workbench | none | L | backlog |
| `attack-diffusion-extraction` | attack | own lab (—) | Regenerating a duplicated training image | workbench | none | L | backlog |
| `attack-direct-injection` | attack | own lab (LAB-06) | The support bot that forgot its job | chat + new 'rag-agent' (lab-app service) | required | M | done |
| `attack-distillation-theft` | attack | own lab (—) | Did they distill us? Teacher fingerprints in a student | chat + workbench | required | M | backlog |
| `attack-eval-contamination` | attack | own lab (LAB-49) | Inflating a benchmark score and catching it | workbench | none | M | done |
| `attack-excessive-agency` | attack | in `attack-tool-output` (LAB-22): steps 5 |  |  |  |  | done |
| `attack-factual-edit` | attack | own lab (—) | One rank-one edit, one changed fact (ROME on GPT-2) | workbench | none | M | backlog |
| `attack-fgsm` | attack | own lab (LAB-08) | One gradient step | workbench | none | S | done |
| `attack-gcg` | attack | own lab (LAB-21) | Optimizing a suffix one token at a time | workbench | optional | L | done |
| `attack-gradient-leak` | attack | own lab (—) | Rebuilding an image from a shared gradient | workbench | none | S | backlog |
| `attack-indirect-injection` | attack | own lab (LAB-15) | The email that wrote its own summary | chat + rag-agent | required | M | done |
| `attack-jailbreak` | attack | own lab (—) | Competing objectives: template jailbreaks against a trained refusal | workbench (+ optional ollama) | optional | L | backlog |
| `attack-judge-manipulation` | attack | own lab (LAB-48) | Grading the grader: steering an LLM judge | chat + workbench | required | S | done |
| `attack-many-shot` | attack | own lab (—) | How many shots until it gives in | workbench (+ optional ollama) | optional | M | backlog |
| `attack-mcp-sampling-injection` | attack | in `system-tools`: Walkthrough step: evaluate server-initiated sampling/createMessage requests and prom… |  |  |  |  | with host |
| `attack-membership` | attack | own lab (LAB-13) | Was this record in the training set? | workbench | none | M | done |
| `attack-memory-poison` | attack | own lab (LAB-29) | A note to my future self | rag-agent (+ optional chat) | required | M | done |
| `attack-merge-tamper` | attack | own lab (—) | Hidden in the transform: tampered merges and GGUF conversion | workbench (+ ollama/chat to run the GGUF) | optional | M | backlog |
| `attack-model-imitation` | attack | own lab (LAB-09) | Stealing a classifier through its API | workbench (victim-api runs inside it or as a sibling service) | none | S | done |
| `attack-multiagent` | attack | own lab (LAB-31) | Telephone game: when a peer's message becomes an order | rag-agent | required | M | done |
| `attack-multimodal-injection` | attack | own lab (LAB-03) | Instructions written on the picture | chat (+ workbench for scripts) | required | M | done |
| `attack-output-sink` | attack | own lab (LAB-20) | Your model's output is someone else's input | rag-agent | optional | M | done |
| `attack-pgd` | attack | in `attack-fgsm` (LAB-08): steps D2-D3; also `concept-transfer` (LAB-56): steps 2-5, D2 and `attack-visual-jailbreak` (LAB-02): steps 3, D2 |  |  |  |  | done |
| `attack-physical` | attack | own lab (—) | When the camera gets a vote: EOT adversarial patches | workbench | none | M | backlog |
| `attack-preference-poison` | attack | in `life-preferences` (LAB-53): steps 4-5; also `life-dpo` (LAB-57): steps 3-4 |  |  |  |  | done |
| `attack-pretrain-poison` | attack | own lab (—) | 250 documents: poisoning a crawl before training | workbench | none | L | backlog |
| `attack-projection-theft` | attack | own lab (LAB-37) | Reading the hidden size off the logits | workbench | none | M | done |
| `attack-prompt-leak` | attack | own lab (LAB-19) | Your system prompt is not a vault | chat + rag-agent | required | S | done |
| `attack-quantization-backdoor` | attack | in `transform-quantization`: Walkthrough step: compare full-precision FP16 vs quantized INT4/INT8 behavior on a r… |  |  |  |  | with host |
| `attack-rag-disclosure` | attack | in `system-rag` (LAB-11): steps 3-5; also `attack-session-leak` (LAB-42): steps 3 |  |  |  |  | done |
| `attack-rag-poison` | attack | own lab (—) | Five documents to change an answer | rag-agent | required | M | backlog |
| `attack-reasoning-sponge` | attack | in `attack-token-exhaustion`: Walkthrough step: compare prompt-length amplification with OverThink decoy reasoning… |  |  |  |  | with host |
| `attack-refusal-ablation` | attack | own lab (—) | Finding and removing a refusal direction | workbench | none | M | backlog |
| `attack-retrieval-rank` | attack | own lab (—) | Getting picked: gaming the retriever | workbench (+ rag-app corpus) | optional | M | backlog |
| `attack-safety-finetune` | attack | own lab (—) | Ten examples to unlearn a rule | workbench | none | M | backlog |
| `attack-session-leak` | attack | own lab (LAB-42) | Whose data is this? Cross-tenant leaks in a chat app | new: rag-agent (shared multi-tenant RAG/agent app) + workbench | optional | M | done |
| `attack-sft-poison` | attack | own lab (LAB-16) | Poisoned demonstrations: 1% of an instruction set | workbench | none | M | done |
| `attack-sleeper` | attack | own lab (—) | Does safety training remove it? A conditional backdoor's persistence | workbench | none | L | backlog |
| `attack-speculative-sidechannel` | attack | in `attack-cache-sidechannel`: Walkthrough step: measure token-stream packet lengths and speculative-decoding accep… |  |  |  |  | with host |
| `attack-sponge` | attack | own lab (LAB-43) | Inputs that cost more than they look | workbench | optional | M | done |
| `attack-steering-misuse` | attack | own lab (—) | Same weights, different model: runtime control vectors | new: serving (llama.cpp server container) + workbench | none | M | backlog |
| `attack-token-exhaustion` | attack | own lab (—) | Unbounded consumption on a shared model server | new 'gateway' profile (litellm service) + ollama | required | S | backlog |
| `attack-tool-description` | attack | own lab (LAB-23) | The tool that told the agent what to do | rag-agent | required | M | done |
| `attack-tool-output` | attack | own lab (LAB-22) | When the tool's answer gives the orders | rag-agent | required | M | done |
| `attack-tool-rugpull` | attack | in `attack-tool-description` (LAB-23): steps 5, D2 |  |  |  |  | done |
| `attack-training-extraction` | attack | in `concept-memorization` (LAB-32): steps 3-5 |  |  |  |  | done |
| `attack-transfer-prompts` | attack | in `attack-gcg` (LAB-21): steps 7 |  |  |  |  | done |
| `attack-unlearning-recovery` | attack | in `adapt-unlearning`: Walkthrough step: recover a suppressed capability from an approximately unlearned mo… |  |  |  |  | with host |
| `attack-unsafe-load` | attack | own lab (LAB-01) | What torch.load really runs | supply | none | M | done |
| `attack-visual-jailbreak` | attack | own lab (LAB-02) | Moving a VLM with invisible pixels | workbench (+ optional chat) | optional | M | done |
| `attack-weight-theft` | attack | own lab (LAB-54) | An open Ollama port and a stolen fine-tune | workbench | none | M | done |
| `adapt-abliteration` | method | in `attack-refusal-ablation`: Mechanism chapter: compute the difference-of-means 'refusal' direction on the toy-gu… |  |  |  |  | with host |
| `adapt-controlnet` | method | in `adapt-textual-inversion`: Optional step 'Add a control branch': attach a zero-initialized ControlNet-style cop… |  |  |  |  | with host |
| `adapt-distillation` | method | in `attack-distillation-theft`: System + Mechanism chapters: authorized distillation of a teacher (e.g. Qwen2.5-0.5B… |  |  |  |  | with host |
| `adapt-dreambooth` | method | in `adapt-textual-inversion`: Step 'Teach the whole UNet instead': DreamBooth-style fine-tune of all tiny-DDPM wei… |  |  |  |  | with host |
| `adapt-full` | method | in `adapt-lora` (LAB-07): steps 7 |  |  |  |  | done |
| `adapt-lora` | method | own lab (LAB-07) | What a 2 MB adapter changes | workbench | none | M | done |
| `adapt-model-edit` | method | in `attack-factual-edit`: Mechanism chapter: causal tracing on GPT-2 small (124M) to locate the MLP layer stor… |  |  |  |  | with host |
| `adapt-peft` | method | hub (links member labs) |  |  |  |  |  |
| `adapt-prefix` | method | in `adapt-softprompt` (LAB-58): steps 4 |  |  |  |  | done |
| `adapt-qlora` | method | in `adapt-lora` (LAB-07): steps 8 |  |  |  |  | done |
| `adapt-representation` | method | own lab (—) | Reading and nudging a model's internal state | workbench | none | M | backlog |
| `adapt-softprompt` | method | own lab (LAB-58) | A prompt you cannot read | workbench | none | M | done |
| `adapt-steering` | method | in `adapt-representation`: Step 'Add the direction back in': inject alpha*v at the chosen layer, plot a dose-re… |  |  |  |  | with host |
| `adapt-textual-inversion` | method | own lab (—) | Teaching a frozen diffusion model a new word | workbench | none | L | backlog |
| `adapt-unlearning` | method | own lab (—) | Forgotten, or just hidden? | workbench | none | M | backlog |
| `transform-conversion` | method | own lab (—) | Same weights, new file, new behavior | workbench + new 'llamacpp' profile (pinned ghcr.io/ggml-org/llama.cpp image with convert/quantize/server) | none | M | backlog |
| `transform-gptq` | method | in `transform-quantization`: Step 'Smarter rounding': run a minimal GPTQ (Hessian-aware, column-by-column error c… |  |  |  |  | with host |
| `transform-merging` | method | in `attack-merge-tamper`: System + Mechanism chapters: merge two LoRA adapters from the tinytune harness into … |  |  |  |  | with host |
| `transform-pruning` | method | own lab (LAB-35) | Smaller is not safer | workbench | none | S | done |
| `transform-quantization` | method | own lab (—) | What 4 bits forget | workbench + llamacpp | none | L | backlog |
| `defense-approval` | defense | in `attack-tool-output` (LAB-22): steps D2 |  |  |  |  | done |
| `defense-authorization` | defense | in `attack-confused-deputy` (LAB-30): steps D2 |  |  |  |  | done |
| `defense-backdoor-audit` | defense | in `attack-backdoor` (LAB-18): steps D1-D3 |  |  |  |  | done |
| `defense-boundaries` | defense | in `attack-indirect-injection` (LAB-15): steps D1, D4 |  |  |  |  | done |
| `defense-budget` | defense | in `attack-agent-loop` (LAB-55): steps D1-D2 |  |  |  |  | done |
| `defense-cache-isolation` | defense | in `attack-cache-sidechannel` (LAB-24): steps D1-D2 |  |  |  |  | done |
| `defense-ci` | defense | in `attack-dependency` (LAB-10): steps D3 |  |  |  |  | done |
| `defense-circuit-breakers` | defense | in `adapt-representation`: Defend step: score residual-stream activations with a linear defection probe and rer… |  |  |  |  | with host |
| `defense-data-hygiene` | defense | in `concept-memorization` (LAB-32): steps D1 |  |  |  |  | done |
| `defense-disclosure` | defense | hub (links member labs) |  |  |  |  |  |
| `defense-dp` | defense | in `attack-membership` (LAB-13): steps D1 |  |  |  |  | done |
| `defense-isolation` | defense | in `attack-unsafe-load` (LAB-01): steps D2 |  |  |  |  | done |
| `defense-least-privilege` | defense | in `attack-tool-output` (LAB-22): steps D1 |  |  |  |  | done |
| `defense-logging` | defense | in `attack-memory-poison` (LAB-29): steps D3 |  |  |  |  | done |
| `defense-memory` | defense | in `attack-memory-poison` (LAB-29): steps D1-D2 |  |  |  |  | done |
| `defense-output` | defense | in `attack-output-sink` (LAB-20): steps D1-D2 |  |  |  |  | done |
| `defense-provenance` | defense | in `attack-unsafe-load` (LAB-01): steps D1 |  |  |  |  | done |
| `defense-rag-acl` | defense | in `attack-session-leak` (LAB-42): steps D2 |  |  |  |  | done |
| `defense-regression` | defense | own lab (—) | Gate every model change | workbench + llamacpp | optional | M | backlog |
| `defense-robust-train` | defense | in `attack-fgsm` (LAB-08): steps D3 |  |  |  |  | done |
| `defense-safe-load` | defense | in `attack-unsafe-load` (LAB-01): steps 4-7, D1 |  |  |  |  | done |
| `eval-adaptive` | evaluation | in `attack-detector-evasion` (LAB-36): steps D2 |  |  |  |  | done |
| `eval-agentdojo` | evaluation | own lab (—) | Benchmarking agent defenses with AgentDojo | new 'agentdojo' profile (python image with agentdojo pinned; or add it to the workbench) + ollama | required | L | backlog |
| `eval-asr` | evaluation | own lab (LAB-12) | Measuring an attack honestly | chat (Ollama) + workbench | required | M | done |
| `eval-cost` | evaluation | in `attack-token-exhaustion`: Evaluate step: report queries, input/output tokens, wall-clock latency and the exact… |  |  |  |  | with host |
| `eval-evidence` | evaluation | in `eval-asr` (LAB-12): steps 6 |  |  |  |  | done |
| `eval-fidelity` | evaluation | in `attack-model-imitation` (LAB-09): steps 4 |  |  |  |  | done |
| `eval-harmbench` | evaluation | in `attack-jailbreak`: Evaluate step 'A HarmBench-style protocol on inert behaviors': fixed behavior set, f… |  |  |  |  | with host |
| `eval-privacy` | evaluation | in `attack-membership` (LAB-13): steps 2, 4-5, Evaluate |  |  |  |  | done |
| `eval-repro` | evaluation | in `eval-asr` (LAB-12): steps 3-4 |  |  |  |  | done |
| `eval-threat-model` | evaluation | in `eval-asr` (LAB-12): steps 6 |  |  |  |  | done |
| `eval-transfer` | evaluation | in `attack-visual-jailbreak` (LAB-02): steps 6 |  |  |  |  | done |
| `eval-utility` | evaluation | in `eval-asr` (LAB-12): steps D1 |  |  |  |  | done |
| `concept-adjacency` | concept | in `concept-transfer` (LAB-56): steps 6 |  |  |  |  | done |
| `concept-attention` | concept | own lab (LAB-26) | Who attends to whom | workbench | none | M | done |
| `concept-boundaries` | concept | own lab (—) | Draw the trust boundaries | rag-agent (new) | required | M | backlog |
| `concept-conditioning` | concept | own lab (LAB-51) | The prompt is a vector | workbench | none | S | done |
| `concept-context` | concept | own lab (LAB-46) | What is in the window | chat + workbench | optional | S | done |
| `concept-decoding` | concept | own lab (LAB-28) | Same weights, different answers | workbench (+chat optional) | optional | S | done |
| `concept-embeddings` | concept | own lab (LAB-25) | Vectors that are not words | workbench | none | M | done |
| `concept-gradients` | concept | own lab (LAB-50) | Gradients point both ways | workbench | none | M | done |
| `concept-guidance` | concept | own lab (—) | Guidance is not a safety filter | workbench | none | S | backlog |
| `concept-kv-cache` | concept | own lab (LAB-38) | The cache remembers | serving (new) + workbench | none | M | done |
| `concept-latents` | concept | own lab (—) | Three parts, three surfaces | workbench | none | M | backlog |
| `concept-logits` | concept | own lab (LAB-05) | What the API reveals | workbench | optional | S | done |
| `concept-memorization` | concept | own lab (LAB-32) | Duplicates get memorized | workbench | none | M | done |
| `concept-noise` | concept | in `arch-diffusion`: System + Mechanism steps: forward noising across timesteps, linear vs cosine schedul… |  |  |  |  | with host |
| `concept-parameters` | concept | own lab (LAB-39) | Weights are what it is, activations are what it is doing | workbench | none | S | done |
| `concept-reasoning-trace` | concept | in `attack-token-exhaustion`: Walkthrough step: inspect intermediate <think> reasoning traces vs visible tokens an… |  |  |  |  | with host |
| `concept-residual` | concept | own lab (LAB-44) | Reading and writing the residual stream | workbench | none | M | done |
| `concept-samplers` | concept | own lab (LAB-45) | Same weights, ten times the cost | workbench | none | S | done |
| `concept-tokens` | concept | own lab (LAB-04) | What the model actually reads | workbench | none | S | done |
| `concept-transfer` | concept | own lab (LAB-56) | Does it transfer? | workbench | none | M | done |
| `arch-classical` | architecture | own lab (—) | Classical ML has an attack surface too | workbench | none | S | backlog |
| `arch-cnn` | architecture | in `attack-physical`: System + Mechanism chapters: feature maps, receptive fields and occlusion sensitivit… |  |  |  |  | with host |
| `arch-decoder` | architecture | own lab (LAB-52) | Base vs instruct, and who speaks next | workbench | optional | S | done |
| `arch-diffusion` | architecture | own lab (—) | From noise to sample | workbench | none | M | backlog |
| `arch-dit` | architecture | in `arch-diffusion`: Backbone step: swap a tiny DiTTransformer2DModel into the toy DDPM; show it is still… |  |  |  |  | with host |
| `arch-embedding` | architecture | own lab (LAB-40) | Similarity is not relevance | workbench (rag-agent image when available) | none | S | done |
| `arch-encdec` | architecture | in `arch-encoder` (LAB-34): steps 2, 5 |  |  |  |  | done |
| `arch-encoder` | architecture | own lab (LAB-34) | The guardrail is a model too | workbench | none | S | done |
| `arch-flow` | architecture | in `arch-diffusion`: Contrast step: flow-matching objective + Euler ODE sampler on the same 2D data; diff… |  |  |  |  | with host |
| `arch-gan` | architecture | own lab (—) | The adversary inside a GAN is not an attacker | workbench | none | M | backlog |
| `arch-latent-diffusion` | architecture | in `concept-latents`: System chapter + optional bk-sdm-tiny step: encoder -> latent denoiser -> decoder as… |  |  |  |  | with host |
| `arch-moe` | architecture | own lab (—) | Who else is in your batch? | workbench | none | M | backlog |
| `arch-neural` | architecture | in `concept-gradients` (LAB-50): steps 1-2 |  |  |  |  | done |
| `arch-ssm` | architecture | in `concept-kv-cache` (LAB-38): steps 2 |  |  |  |  | done |
| `arch-transformer` | architecture | own lab (LAB-27) | Anatomy and forensics of a transformer checkpoint | workbench | none | M | done |
| `arch-unet` | architecture | in `arch-diffusion`: Backbone step: inspect the UNet2DModel of google/ddpm-cifar10-32 (down/up path, skip… |  |  |  |  | with host |
| `arch-vae` | architecture | in `concept-latents`: Steps 1-2: encode/decode with taesd, latent shape and reconstruction error. |  |  |  |  | with host |
| `arch-vlm` | architecture | in `attack-visual-jailbreak` (LAB-02): steps 1 |  |  |  |  | done |
| `system-agent` | component | own lab (—) | Anatomy of an agent loop | rag-agent (new) | required | M | backlog |
| `system-browser` | component | own lab (—) | What the agent sees vs what you see | rag-agent (new) + browser (new: Playwright image or workbench extension) | required | M | backlog |
| `system-eval` | component | own lab (—) | Who grades the grader | chat + workbench | required | M | backlog |
| `system-index` | component | own lab (LAB-41) | Who controls the corpus controls the context | rag-agent (new) | none | S | done |
| `system-loader` | component | in `attack-unsafe-load` (LAB-01): steps 1-4, 8 |  |  |  |  | done |
| `system-mcp` | component | in `system-tools`: Walkthrough step: inspect MCP JSON-RPC tool discovery, resource templates, and serve… |  |  |  |  | with host |
| `system-memory` | component | in `attack-memory-poison` (LAB-29): steps 1 |  |  |  |  | done |
| `system-multiagent` | component | in `attack-multiagent` (LAB-31): steps 1, 4 |  |  |  |  | done |
| `system-rag` | component | own lab (LAB-11) | Five components of RAG | rag-agent (new) | required | M | done |
| `system-registry` | component | in `attack-unsafe-load` (LAB-01): steps 8 |  |  |  |  | done |
| `system-serving` | component | own lab (LAB-14) | What the server adds | serving (new) + workbench | none | M | done |
| `system-tools` | component | own lab (LAB-59) | What a tool really exposes | rag-agent (new) | required | M | done |
| `tool-diffusers` | component | in `concept-samplers` (LAB-45): steps 2, 6, D3 |  |  |  |  | done |
| `tool-llamacpp` | component | in `system-serving` (LAB-14): steps 1-5, D1-D3 |  |  |  |  | done |
| `tool-mlx` | component | in `system-serving` (LAB-14): steps 6 |  |  |  |  | done |
| `tool-tensorrt` | component | in `format-engine`: Reading step + optional NVIDIA-only step: engine and plugin trust; the CPU analogue … |  |  |  |  | with host |
| `tool-transformers` | component | in `attack-dependency` (LAB-10): steps 3-5, D1 |  |  |  |  | done |
| `tool-unsloth` | component | in `life-sft` (LAB-33): steps 7 |  |  |  |  | done |
| `tool-vllm` | component | in `concept-kv-cache`: Optional Linux-amd64 step: vLLM CPU with --enable-prefix-caching, then per-tenant ca… |  |  |  |  | with host |
| `life-continued` | lifecycle | in `life-safety`: Further-training variant: continued pretraining on raw domain text (LM objective) an… |  |  |  |  | with host |
| `life-data` | lifecycle | own lab (LAB-47) | Lineage or it did not happen | workbench | none | S | done |
| `life-deploy` | lifecycle | hub (links member labs) |  |  |  |  |  |
| `life-dpo` | lifecycle | own lab (LAB-57) | Preferences without a reward model | workbench | none | M | done |
| `life-evaluate` | lifecycle | in `system-eval`: Split-governance step: hash-locked final test set, n-gram overlap scan between train… |  |  |  |  | with host |
| `life-posttrain` | lifecycle | hub (links member labs) |  |  |  |  |  |
| `life-preferences` | lifecycle | own lab (LAB-53) | Preferences shape the reward | workbench | none | M | done |
| `life-pretrain` | lifecycle | in `concept-memorization` (LAB-32): steps 1-2 |  |  |  |  | done |
| `life-rlhf` | lifecycle | own lab (—) | Optimize against a reward model and watch it get hacked | workbench | none | M | backlog |
| `life-safety` | lifecycle | own lab (—) | Safety is a learned property | workbench | none | M | backlog |
| `life-sft` | lifecycle | own lab (LAB-33) | Teach a tiny model a new habit | workbench | none | M | done |
| `format-engine` | format | own lab (—) | A compiled engine is a program | supply (workbench + sandbox) with a compiler-enabled image variant | none | L | backlog |
| `format-gguf` | format | own lab (LAB-17) | GGUF is data, its template is code | serving (new) + workbench | none | M | done |
| `format-model-package` | format | own lab (—) | Same weights, different model | workbench | none | S | backlog |
| `format-onnx` | format | own lab (—) | A graph, not a blob | workbench | none | M | backlog |
| `format-pytorch` | format | in `attack-unsafe-load` (LAB-01): steps 1-5 |  |  |  |  | done |
| `format-safetensors` | format | in `attack-unsafe-load` (LAB-01): steps 6 |  |  |  |  | done |

## Known risks and follow-ups

- **CPU feasibility:** every timing in the classification is an estimate until a lab is built; training-heavy labs (sleeper agents, pretraining poison, diffusion backdoor/extraction, textual inversion, quantization-conditioned behavior) ship precomputed safetensors checkpoints plus an optional slow regeneration step, like LAB-02.
- **Small models and tools:** small local models are unreliable at tool calling, so agent labs ship replay transcripts and add `qwen2.5:3b` for tool use (qwen2.5vl cannot call tools).
- **No harmful content:** jailbreak, refusal-ablation and safety-finetune labs measure bypass of the stand-in refusal policy (a fictional "Project Lantern" vault), never real harmful behavior; no harmful prompt datasets are bundled.
- **Platform-specific tools** (TensorRT, MLX, Unsloth, AgentDojo) are optional steps or get their own image; `format-engine` is the riskiest build.
- **Taxonomy gaps** found while classifying (missing `can_mitigate` edges for jailbreak, gcg, rag-poison, retrieval-rank, citation-launder, multiagent, tool-description; MoE and GAN literature without attack edges) are proposals in `labs/CHANGES-from-spec.md`, not applied to the seed.
