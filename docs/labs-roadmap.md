# Hands-on labs roadmap

**Status:** living plan, generated 2026-10-26 from a four-agent classification of all 204 Atlas nodes (machine-readable: [`labs-roadmap.json`](labs-roadmap.json)). Update it at the end of every wave.

**Goal:** close to one lab per node, so every Atlas topic has theory (the article) and practice (a lab). Lab pattern, stack and safety rules: [`labs-spec.md`](labs-spec.md) and [`../labs/README.md`](../labs/README.md).

## How every node gets practice

- **Own lab (104 nodes, 41 done):** a dedicated lab in `labs/<node-id>/`, following the template. Attacks use the 5 explainer chapters as written. Methods, concepts, architectures, components, lifecycle stages and formats are *foundation labs*: the same 5 chapters, read as System → Risk → Mechanism → Observation → Defense.
- **Covered (72 nodes):** practiced as named steps inside a host lab (mostly defenses and evaluations inside the attack lab they mitigate or measure). The host lab lists them in its front matter (`covers:` with step anchors) and the site shows a "Practiced in LAB-NN · Step X" badge on the covered node.
- **Hub (28 nodes):** goals, families and umbrella nodes. Their page links the member labs and the foundation labs to do first; no lab of their own.

## Shared fixtures (build once, reuse everywhere)

Each fixture is created by the first lab that needs it (its *founding* lab) and then reused. One image change: **workbench v2** (adds peft, accelerate, scikit-learn, fastapi/uvicorn, chromadb, mcp and friends); LAB-01/02 are re-verified on it.

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
| LAB-07 | `adapt-lora` | What a 2 MB adapter changes | workbench | optional | M | tinylm |
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
| `attack-adapter-tamper` | attack | own lab (—) | The adapter you didn't review | workbench | none | M | backlog |
| `attack-agent-loop` | attack | own lab (—) | The task that never ends | rag-agent (+ gateway) | required | S | backlog |
| `attack-artifact-substitution` | attack | in `attack-unsafe-load` (LAB-01): LAB-01 Step 8 (realistic delivery through a tampered local hub: v1.1 swap… |  |  |  |  | done |
| `attack-attribute` | attack | own lab (—) | Inversion, prototypes and attribute inference: three different outcomes | workbench | none | S | backlog |
| `attack-backdoor` | attack | own lab (—) | BadNets: a sticker that rewrites the label | workbench | none | M | 2 |
| `attack-cache-sidechannel` | attack | own lab (—) | Timing the prompt cache | new: serving (llama.cpp server) + workbench | required | M | backlog |
| `attack-capability-abuse` | attack | hub (links member labs) |  |  |  |  |  |
| `attack-citation-launder` | attack | in `attack-rag-poison`: Walkthrough step 'Borrowed authority' (poisoned doc impersonates a citation to a fi… |  |  |  |  | with host |
| `attack-confused-deputy` | attack | own lab (—) | The agent that had the admin key | rag-agent | required | M | backlog |
| `attack-dependency` | attack | own lab (LAB-10) | from_pretrained ran my code: remote code, packages and plugins | supply | none | M | 1 |
| `attack-detector-evasion` | attack | own lab (—) | Slipping past a prompt-injection detector | workbench (+ chat for the optional functionality step) | optional | M | backlog |
| `attack-diffusion-backdoor` | attack | own lab (—) | A trigger in the noise: backdooring a tiny diffusion model | workbench | none | L | backlog |
| `attack-diffusion-extraction` | attack | own lab (—) | Regenerating a duplicated training image | workbench | none | L | backlog |
| `attack-direct-injection` | attack | own lab (LAB-06) | The support bot that forgot its job | chat + new 'rag-agent' (lab-app service) | required | M | 1 |
| `attack-distillation-theft` | attack | own lab (—) | Did they distill us? Teacher fingerprints in a student | chat + workbench | required | M | backlog |
| `attack-eval-contamination` | attack | own lab (—) | Inflating a benchmark score and catching it | workbench | none | M | backlog |
| `attack-excessive-agency` | attack | in `attack-tool-output`: Walkthrough step 'Same injection, three permission profiles' (broad toolset incl. … |  |  |  |  | 2 |
| `attack-factual-edit` | attack | own lab (—) | One rank-one edit, one changed fact (ROME on GPT-2) | workbench | none | M | backlog |
| `attack-fgsm` | attack | own lab (LAB-08) | One gradient step: FGSM on a digit classifier | workbench | none | S | 1 |
| `attack-gcg` | attack | own lab (—) | Optimizing a suffix one token at a time | workbench | optional | L | 2 |
| `attack-gradient-leak` | attack | own lab (—) | Rebuilding an image from a shared gradient | workbench | none | S | backlog |
| `attack-indirect-injection` | attack | own lab (—) | The email that wrote its own summary | chat + rag-agent | required | M | 2 |
| `attack-jailbreak` | attack | own lab (—) | Competing objectives: template jailbreaks against a trained refusal | workbench (+ optional ollama) | optional | L | backlog |
| `attack-judge-manipulation` | attack | own lab (—) | Grading the grader: steering an LLM judge | chat + workbench | required | S | backlog |
| `attack-many-shot` | attack | own lab (—) | How many shots until it gives in | workbench (+ optional ollama) | optional | M | backlog |
| `attack-membership` | attack | own lab (—) | Was this record in the training set? | workbench | none | M | 2 |
| `attack-memory-poison` | attack | own lab (—) | A note to my future self | rag-agent (+ optional chat) | required | M | backlog |
| `attack-merge-tamper` | attack | own lab (—) | Hidden in the transform: tampered merges and GGUF conversion | workbench (+ ollama/chat to run the GGUF) | optional | M | backlog |
| `attack-model-imitation` | attack | own lab (LAB-09) | Stealing a classifier through its API | workbench (victim-api runs inside it or as a sibling service) | none | S | 1 |
| `attack-multiagent` | attack | own lab (—) | Telephone game: when a peer's message becomes an order | rag-agent | required | M | backlog |
| `attack-multimodal-injection` | attack | own lab (LAB-03) | Instructions written on the picture | chat (+ workbench for scripts) | required | M | 1 |
| `attack-output-sink` | attack | own lab (—) | Your model's output is someone else's input | rag-agent | optional | M | 2 |
| `attack-pgd` | attack | own lab (—) | Robust or just masked? PGD, gradient masking and adversarial training | workbench | none | M | backlog |
| `attack-physical` | attack | own lab (—) | When the camera gets a vote: EOT adversarial patches | workbench | none | M | backlog |
| `attack-preference-poison` | attack | own lab (—) | Flipping the reward: poisoned preference pairs | workbench (+ chat optional) | optional | M | backlog |
| `attack-pretrain-poison` | attack | own lab (—) | 250 documents: poisoning a crawl before training | workbench | none | L | backlog |
| `attack-projection-theft` | attack | own lab (—) | Reading the hidden size off the logits | workbench | none | M | backlog |
| `attack-prompt-leak` | attack | own lab (—) | Your system prompt is not a vault | chat + rag-agent | required | S | 2 |
| `attack-rag-disclosure` | attack | own lab (—) | Retrieval without an access check | rag-agent | optional | S | backlog |
| `attack-rag-poison` | attack | own lab (—) | Five documents to change an answer | rag-agent | required | M | backlog |
| `attack-refusal-ablation` | attack | own lab (—) | Finding and removing a refusal direction | workbench | none | M | backlog |
| `attack-retrieval-rank` | attack | own lab (—) | Getting picked: gaming the retriever | workbench (+ rag-app corpus) | optional | M | backlog |
| `attack-safety-finetune` | attack | own lab (—) | Ten examples to unlearn a rule | workbench | none | M | backlog |
| `attack-session-leak` | attack | own lab (—) | Whose data is this? Cross-tenant leaks in a chat app | new: rag-agent (shared multi-tenant RAG/agent app) + workbench | optional | M | backlog |
| `attack-sft-poison` | attack | own lab (—) | Poisoned demonstrations: 1% of an instruction set | workbench | none | M | 2 |
| `attack-sleeper` | attack | own lab (—) | Does safety training remove it? A conditional backdoor's persistence | workbench | none | L | backlog |
| `attack-sponge` | attack | own lab (—) | Inputs that cost more than they look | workbench | optional | M | backlog |
| `attack-steering-misuse` | attack | own lab (—) | Same weights, different model: runtime control vectors | new: serving (llama.cpp server container) + workbench | none | M | backlog |
| `attack-token-exhaustion` | attack | own lab (—) | Unbounded consumption on a shared model server | new 'gateway' profile (litellm service) + ollama | required | S | backlog |
| `attack-tool-description` | attack | own lab (—) | The tool that told the agent what to do | rag-agent | required | M | backlog |
| `attack-tool-output` | attack | own lab (—) | When the tool's answer gives the orders | rag-agent | required | M | 2 |
| `attack-tool-rugpull` | attack | in `attack-tool-description`: Walkthrough step 'Approved, then changed' (MCP server swaps to a poisoned def… |  |  |  |  | with host |
| `attack-training-extraction` | attack | own lab (—) | Secret sharer: extracting planted canaries from a small LM | workbench | none | M | backlog |
| `attack-transfer-prompts` | attack | in `attack-gcg`: Walkthrough step 'Does the suffix transfer?' (frozen suffix from SmolLM2-135M sent to Smol… |  |  |  |  | 2 |
| `attack-unsafe-load` | attack | own lab (LAB-01) | What torch.load really runs | supply | none | M | done |
| `attack-visual-jailbreak` | attack | own lab (LAB-02) | Moving a VLM with invisible pixels | workbench (+ optional chat) | optional | M | done |
| `attack-weight-theft` | attack | own lab (—) | An open Ollama port and a stolen fine-tune | new: theft (ollama + attacker + registry, internal network only) | required | M | backlog |
| `adapt-abliteration` | method | in `attack-refusal-ablation`: Mechanism chapter: compute the difference-of-means 'refusal' direction on the… |  |  |  |  | with host |
| `adapt-controlnet` | method | in `adapt-textual-inversion`: Optional step 'Add a control branch': attach a zero-initialized ControlNet-st… |  |  |  |  | with host |
| `adapt-distillation` | method | in `attack-distillation-theft`: System + Mechanism chapters: authorized distillation of a teacher (e.g. Qwe… |  |  |  |  | with host |
| `adapt-dreambooth` | method | in `adapt-textual-inversion`: Step 'Teach the whole UNet instead': DreamBooth-style fine-tune of all tiny-D… |  |  |  |  | with host |
| `adapt-full` | method | in `adapt-lora` (LAB-07): Step 'Full fine-tune for comparison': fine-tune all SmolLM2-135M-Instruct weights… |  |  |  |  | 1 |
| `adapt-lora` | method | own lab (LAB-07) | What a 2 MB adapter changes | workbench | optional | M | 1 |
| `adapt-model-edit` | method | in `attack-factual-edit`: Mechanism chapter: causal tracing on GPT-2 small (124M) to locate the MLP layer s… |  |  |  |  | with host |
| `adapt-peft` | method | hub (links member labs) |  |  |  |  |  |
| `adapt-prefix` | method | in `adapt-softprompt`: Step 'Move the prompt inside every layer': peft PrefixTuningConfig on the same task,… |  |  |  |  | with host |
| `adapt-qlora` | method | in `adapt-lora` (LAB-07): Optional step 'Train on a 4-bit base': fake-quantize the frozen base to NF4 in to… |  |  |  |  | 1 |
| `adapt-representation` | method | own lab (—) | Reading and nudging a model's internal state | workbench | none | M | backlog |
| `adapt-softprompt` | method | own lab (—) | A prompt you cannot read | workbench | none | M | backlog |
| `adapt-steering` | method | in `adapt-representation`: Step 'Add the direction back in': inject alpha*v at the chosen layer, plot a dos… |  |  |  |  | with host |
| `adapt-textual-inversion` | method | own lab (—) | Teaching a frozen diffusion model a new word | workbench | none | L | backlog |
| `adapt-unlearning` | method | own lab (—) | Forgotten, or just hidden? | workbench | none | M | backlog |
| `transform-conversion` | method | own lab (—) | Same weights, new file, new behavior | workbench + new 'llamacpp' profile (pinned ghcr.io/ggml-org/llama.cpp image with convert/quantize/server) | none | M | backlog |
| `transform-gptq` | method | in `transform-quantization`: Step 'Smarter rounding': run a minimal GPTQ (Hessian-aware, column-by-column e… |  |  |  |  | with host |
| `transform-merging` | method | in `attack-merge-tamper`: System + Mechanism chapters: merge two LoRA adapters from the tinytune harness in… |  |  |  |  | with host |
| `transform-pruning` | method | own lab (—) | Smaller is not safer | workbench | none | S | backlog |
| `transform-quantization` | method | own lab (—) | What 4 bits forget | workbench + llamacpp | none | L | backlog |
| `defense-approval` | defense | in `attack-tool-output`: Defend step D2 'Approval that binds to arguments': add a human-approval gate (mcp-… |  |  |  |  | 2 |
| `defense-authorization` | defense | in `attack-confused-deputy`: Defend step D1 'Check the principal in code': move the permission check from t… |  |  |  |  | with host |
| `defense-backdoor-audit` | defense | in `attack-backdoor`: Defend steps: run ART's NeuralCleanse (trigger reverse-engineering) and ActivationDef… |  |  |  |  | 2 |
| `defense-boundaries` | defense | in `attack-indirect-injection`: Defend steps: spotlighting/datamarking of retrieved content, then a plan-th… |  |  |  |  | 2 |
| `defense-budget` | defense | in `attack-agent-loop`: Defend step: enforce max tool calls, recursion depth, token and wall-clock budgets … |  |  |  |  | with host |
| `defense-cache-isolation` | defense | in `attack-cache-sidechannel`: Defend step: per-tenant cache partitioning (cache salt / separate slots, or … |  |  |  |  | with host |
| `defense-ci` | defense | in `attack-dependency` (LAB-10): Defend step: split the pipeline into an untrusted 'inspect/test' job (no s… |  |  |  |  | 1 |
| `defense-data-hygiene` | defense | in `attack-training-extraction`: Defend step: deduplicate the fine-tune corpus and remove the planted canar… |  |  |  |  | with host |
| `defense-disclosure` | defense | hub (links member labs) |  |  |  |  |  |
| `defense-dp` | defense | in `attack-membership`: Defend step: retrain the target classifier with Opacus DP-SGD at epsilon in {1, 8, … |  |  |  |  | 2 |
| `defense-isolation` | defense | in `attack-unsafe-load` (LAB-01): Already implemented in LAB-01 Step D2 'Isolate the loader' (sandbox servi… |  |  |  |  | done |
| `defense-least-privilege` | defense | in `attack-tool-output`: Defend step D1 'Shrink the toolset': replace a broad filesystem/email tool with sc… |  |  |  |  | 2 |
| `defense-logging` | defense | in `attack-memory-poison`: Defend step D2 'Trace it back': structured action and content lineage logs (whic… |  |  |  |  | with host |
| `defense-memory` | defense | in `attack-memory-poison`: Defend step D1 'Who wrote this memory?': store provenance (source, session, prin… |  |  |  |  | with host |
| `defense-output` | defense | in `attack-output-sink`: Defend step: context-specific encoding/validation at the sink (HTML escaping, para… |  |  |  |  | 2 |
| `defense-provenance` | defense | in `attack-unsafe-load` (LAB-01): Defend steps: pin hub revisions by commit hash, keep a sha256 manifest, s… |  |  |  |  | done |
| `defense-rag-acl` | defense | in `attack-rag-disclosure`: Defend step: attach ACL metadata to every chunk at ingest, filter by the reques… |  |  |  |  | with host |
| `defense-regression` | defense | own lab (—) | Gate every model change | workbench + llamacpp | optional | M | backlog |
| `defense-robust-train` | defense | in `attack-pgd`: Defend steps: PGD adversarial training of the small MNIST/CIFAR-subset CNN (visionbench fi… |  |  |  |  | with host |
| `defense-safe-load` | defense | in `attack-unsafe-load` (LAB-01): Already implemented in LAB-01 Steps 4-7 (weights_only allowlist, pitfalls… |  |  |  |  | done |
| `eval-adaptive` | evaluation | in `attack-pgd`: Evaluate/Defend step: attack an input-transformation or detector defense with a non-adapti… |  |  |  |  | with host |
| `eval-agentdojo` | evaluation | own lab (—) | Benchmarking agent defenses with AgentDojo | new 'agentdojo' profile (python image with agentdojo pinned; or add it to the workbench) + ollama | required | L | backlog |
| `eval-asr` | evaluation | own lab (—) | Measuring an attack honestly | chat (Ollama) + workbench | required | M | 2 |
| `eval-cost` | evaluation | in `attack-token-exhaustion`: Evaluate step: report queries, input/output tokens, wall-clock latency and th… |  |  |  |  | with host |
| `eval-evidence` | evaluation | in `eval-asr`: Final step 'Label your claim': classify the lab's own result (single empirical demonstration… |  |  |  |  | 2 |
| `eval-fidelity` | evaluation | in `attack-model-imitation` (LAB-09): Evaluate step: report functional agreement with the target, task accu… |  |  |  |  | 1 |
| `eval-harmbench` | evaluation | in `attack-jailbreak`: Evaluate step 'A HarmBench-style protocol on inert behaviors': fixed behavior set, f… |  |  |  |  | with host |
| `eval-privacy` | evaluation | in `attack-membership`: Evaluate steps: compare the attack against a membership baseline (random and loss-t… |  |  |  |  | 2 |
| `eval-repro` | evaluation | in `eval-asr`: Step 2 'One seed is an anecdote': five seeds with Wilson intervals and a run manifest (seed,… |  |  |  |  | 2 |
| `eval-threat-model` | evaluation | in `attack-unsafe-load` (LAB-01): Already in LAB-01 (related_nodes) via the Atlas Context table (access pro… |  |  |  |  | done |
| `eval-transfer` | evaluation | in `attack-visual-jailbreak` (LAB-02): Already in LAB-02: transfer rows against other VLMs via the backend … |  |  |  |  | done |
| `eval-utility` | evaluation | in `eval-asr`: Step 3 'The defense's bill': false-positive rate and benign-task success with the classifier… |  |  |  |  | 2 |
| `concept-adjacency` | concept | in `concept-transfer`: Reading step in the Observation chapter: the transfer matrix as the worked example o… |  |  |  |  | with host |
| `concept-attention` | concept | own lab (—) | Who attends to whom | workbench | none | M | backlog |
| `concept-boundaries` | concept | own lab (—) | Draw the trust boundaries | rag-agent (new) | required | M | backlog |
| `concept-conditioning` | concept | own lab (—) | The prompt is a vector | workbench | none | S | backlog |
| `concept-context` | concept | own lab (—) | What is in the window | chat + workbench | optional | S | backlog |
| `concept-decoding` | concept | own lab (—) | Same weights, different answers | workbench (+chat optional) | optional | S | backlog |
| `concept-embeddings` | concept | own lab (—) | Vectors that are not words | workbench | none | M | backlog |
| `concept-gradients` | concept | own lab (—) | Gradients point both ways | workbench | none | M | backlog |
| `concept-guidance` | concept | own lab (—) | Guidance is not a safety filter | workbench | none | S | backlog |
| `concept-kv-cache` | concept | own lab (—) | The cache remembers | serving (new) + workbench | none | M | backlog |
| `concept-latents` | concept | own lab (—) | Three parts, three surfaces | workbench | none | M | backlog |
| `concept-logits` | concept | own lab (LAB-05) | What the API reveals | workbench | optional | S | 1 |
| `concept-memorization` | concept | own lab (—) | Duplicates get memorized | workbench | none | M | backlog |
| `concept-noise` | concept | in `arch-diffusion`: System + Mechanism steps: forward noising across timesteps, linear vs cosine schedule … |  |  |  |  | with host |
| `concept-parameters` | concept | own lab (—) | Weights are what it is, activations are what it is doing | workbench | none | S | backlog |
| `concept-residual` | concept | own lab (—) | Reading and writing the residual stream | workbench | none | M | backlog |
| `concept-samplers` | concept | own lab (—) | Same weights, ten times the cost | workbench | none | S | backlog |
| `concept-tokens` | concept | own lab (LAB-04) | What the model actually reads | workbench | none | S | 1 |
| `concept-transfer` | concept | own lab (—) | Does it transfer? | workbench | none | M | backlog |
| `arch-classical` | architecture | own lab (—) | Classical ML has an attack surface too | workbench | none | S | backlog |
| `arch-cnn` | architecture | in `attack-physical`: System + Mechanism chapters: feature maps, receptive fields and occlusion sensitivity… |  |  |  |  | with host |
| `arch-decoder` | architecture | own lab (—) | Base vs instruct, and who speaks next | workbench | optional | S | backlog |
| `arch-diffusion` | architecture | own lab (—) | From noise to sample | workbench | none | M | backlog |
| `arch-dit` | architecture | in `arch-diffusion`: Backbone step: swap a tiny DiTTransformer2DModel into the toy DDPM; show it is still i… |  |  |  |  | with host |
| `arch-embedding` | architecture | own lab (—) | Similarity is not relevance | workbench (rag-agent image when available) | none | S | backlog |
| `arch-encdec` | architecture | in `arch-encoder`: Contrast step: flan-t5-small summarizer reads the document the encoder guardrail passed … |  |  |  |  | with host |
| `arch-encoder` | architecture | own lab (—) | The guardrail is a model too | workbench | none | S | backlog |
| `arch-flow` | architecture | in `arch-diffusion`: Contrast step: flow-matching objective + Euler ODE sampler on the same 2D data; diffus… |  |  |  |  | with host |
| `arch-gan` | architecture | own lab (—) | The adversary inside a GAN is not an attacker | workbench | none | M | backlog |
| `arch-latent-diffusion` | architecture | in `concept-latents`: System chapter + optional bk-sdm-tiny step: encoder -> latent denoiser -> decoder as … |  |  |  |  | with host |
| `arch-moe` | architecture | own lab (—) | Who else is in your batch? | workbench | none | M | backlog |
| `arch-neural` | architecture | in `concept-gradients`: Steps 1-2 (System): train the small CNN, loss and backprop. |  |  |  |  | with host |
| `arch-ssm` | architecture | in `concept-kv-cache`: Contrast step: mamba-130m keeps a fixed-size recurrent state instead of a growing KV… |  |  |  |  | with host |
| `arch-transformer` | architecture | own lab (—) | Anatomy and forensics of a transformer checkpoint | workbench | none | M | backlog |
| `arch-unet` | architecture | in `arch-diffusion`: Backbone step: inspect the UNet2DModel of google/ddpm-cifar10-32 (down/up path, skip c… |  |  |  |  | with host |
| `arch-vae` | architecture | in `concept-latents`: Steps 1-2: encode/decode with taesd, latent shape and reconstruction error. |  |  |  |  | with host |
| `arch-vlm` | architecture | in `attack-visual-jailbreak` (LAB-02): LAB-02 Step 1 + explainer System chapter (SmolVLM image tokens fused… |  |  |  |  | done |
| `system-agent` | component | own lab (—) | Anatomy of an agent loop | rag-agent (new) | required | M | backlog |
| `system-browser` | component | own lab (—) | What the agent sees vs what you see | rag-agent (new) + browser (new: Playwright image or workbench extension) | required | M | backlog |
| `system-eval` | component | own lab (—) | Who grades the grader | chat + workbench | required | M | backlog |
| `system-index` | component | own lab (—) | Who controls the corpus controls the context | rag-agent (new) | none | S | backlog |
| `system-loader` | component | in `attack-unsafe-load` (LAB-01): LAB-01 (exists): Steps 1-6 and D2 isolate the loader; related_nodes alrea… |  |  |  |  | done |
| `system-memory` | component | in `attack-memory-poison`: System chapter + first step: inspect the memory store write/recall path of the r… |  |  |  |  | with host |
| `system-multiagent` | component | in `attack-multiagent`: System chapter: two-agent orchestration (planner/worker) on the rag-agent fixture w… |  |  |  |  | with host |
| `system-rag` | component | own lab (—) | Five components of RAG | rag-agent (new) | required | M | 2 |
| `system-registry` | component | in `attack-unsafe-load` (LAB-01): System chapter: local git/HTTP model hub with revisions and tags (general… |  |  |  |  | done |
| `system-serving` | component | own lab (—) | What the server adds | serving (new) + workbench | none | M | 2 |
| `system-tools` | component | own lab (—) | What a tool really exposes | rag-agent (new) | required | M | backlog |
| `tool-diffusers` | component | in `concept-samplers`: Scheduler-swap steps plus final step on use_safetensors and custom_pipeline/trust_re… |  |  |  |  | with host |
| `tool-llamacpp` | component | in `system-serving`: llama.cpp server is the serving-profile runtime; GGUF parsing/template trust is in for… |  |  |  |  | 2 |
| `tool-mlx` | component | in `system-serving`: Optional host-only macOS step: run mlx_lm.server and repeat the exposure/budget probes. |  |  |  |  | 2 |
| `tool-tensorrt` | component | in `format-engine`: Reading step + optional NVIDIA-only step: engine and plugin trust; the CPU analogue (AO… |  |  |  |  | with host |
| `tool-transformers` | component | in `attack-dependency` (LAB-10): Steps on from_pretrained: auto_map + trust_remote_code imports repo code, … |  |  |  |  | 1 |
| `tool-unsloth` | component | in `life-sft`: Reading step + optional GPU step: the same LoRA SFT run with Unsloth; export/push-to-hub tok… |  |  |  |  | with host |
| `tool-vllm` | component | in `concept-kv-cache`: Optional Linux-amd64 step: vLLM CPU with --enable-prefix-caching, then per-tenant ca… |  |  |  |  | with host |
| `life-continued` | lifecycle | in `life-safety`: Further-training variant: continued pretraining on raw domain text (LM objective) and its… |  |  |  |  | with host |
| `life-data` | lifecycle | own lab (—) | Lineage or it did not happen | workbench | none | S | backlog |
| `life-deploy` | lifecycle | hub (links member labs) |  |  |  |  |  |
| `life-dpo` | lifecycle | own lab (—) | Preferences without a reward model | workbench | none | M | backlog |
| `life-evaluate` | lifecycle | in `system-eval`: Split-governance step: hash-locked final test set, n-gram overlap scan between training f… |  |  |  |  | with host |
| `life-posttrain` | lifecycle | hub (links member labs) |  |  |  |  |  |
| `life-preferences` | lifecycle | own lab (—) | Preferences shape the reward | workbench | none | M | backlog |
| `life-pretrain` | lifecycle | in `concept-memorization`: Steps 1-2: train a tiny GPT from scratch (data, loss curve, sampling) before ins… |  |  |  |  | with host |
| `life-rlhf` | lifecycle | own lab (—) | Optimize against a reward model and watch it get hacked | workbench | none | M | backlog |
| `life-safety` | lifecycle | own lab (—) | Safety is a learned property | workbench | none | M | backlog |
| `life-sft` | lifecycle | own lab (—) | Teach a tiny model a new habit | workbench | none | M | backlog |
| `format-engine` | format | own lab (—) | A compiled engine is a program | supply (workbench + sandbox) with a compiler-enabled image variant | none | L | backlog |
| `format-gguf` | format | own lab (—) | GGUF is data, its template is code | serving (new) + workbench | none | M | 2 |
| `format-model-package` | format | own lab (—) | Same weights, different model | workbench | none | S | backlog |
| `format-onnx` | format | own lab (—) | A graph, not a blob | workbench | none | M | backlog |
| `format-pytorch` | format | in `attack-unsafe-load` (LAB-01): LAB-01 (exists): Steps 1-5 (pickle opcodes in .pt, weights_only, pitfalls). |  |  |  |  | done |
| `format-safetensors` | format | in `attack-unsafe-load` (LAB-01): LAB-01 (exists): Step 6 'safetensors has no VM' and D1; the 'does not est… |  |  |  |  | done |

## Known risks and follow-ups

- **CPU feasibility:** every timing in the classification is an estimate until a lab is built; training-heavy labs (sleeper agents, pretraining poison, diffusion backdoor/extraction, textual inversion, quantization-conditioned behavior) ship precomputed safetensors checkpoints plus an optional slow regeneration step, like LAB-02.
- **Small models and tools:** small local models are unreliable at tool calling, so agent labs ship replay transcripts and add `qwen2.5:3b` for tool use (qwen2.5vl cannot call tools).
- **No harmful content:** jailbreak, refusal-ablation and safety-finetune labs measure bypass of the stand-in refusal policy (a fictional "Project Lantern" vault), never real harmful behavior; no harmful prompt datasets are bundled.
- **Platform-specific tools** (TensorRT, MLX, Unsloth, AgentDojo) are optional steps or get their own image; `format-engine` is the riskiest build.
- **Taxonomy gaps** found while classifying (missing `can_mitigate` edges for jailbreak, gcg, rag-poison, retrieval-rank, citation-launder, multiagent, tool-description; MoE and GAN literature without attack edges) are proposals in `labs/CHANGES-from-spec.md`, not applied to the seed.
