# AI Security Atlas — Hands-On Labs & Workshop Proposal

**Date:** 2026-10-21  
**Status:** Proposal for Implementation Agent — stack decision made (see Section 3a)  
**Reference:** Inspired by [DVKA (Damn Vulnerable Kubernetes Application) Workshop](https://github.com/Alevsk/dvka/tree/master/workshop)

> **Implementation:** this proposal is superseded by the implementation spec [`docs/labs-spec.md`](labs-spec.md) (read its final "Addendum: user decisions"). The labs live in [`labs/`](../labs/) (start with [`labs/README.md`](../labs/README.md)).

---

## 1. Context & Problem Statement

The **AI Security Atlas** (`ai-security-atlas`) is currently a static, evidence-linked knowledge graph covering **204 topics** across 11 types (`goal`, `technique_family`, `attack`, `method`, `defense`, `evaluation`, `concept`, `architecture`, `component`, `lifecycle`, `format`) and **650 typed relationships**, compiled via [`json2hugo.py`](../json2hugo.py) from [`ai_security_research_graph_seed.json`](../ai_security_research_graph_seed.json) and [`articles/`](../articles/).

While the theoretical taxonomy and primary-source links are strong, the best way to internalize security concepts is **learning by doing**. The goal of this initiative is to add **reproducible, hands-on mini-labs / workshops** to applicable nodes in the Atlas—allowing a learner to spin up a realistic environment, execute commands, observe the mechanism or vulnerability first-hand, and test defenses or evaluations safely on their own machine.

### Design Principles
1. **DVKA-Style Step-by-Step Walkthroughs:** Each applicable node should include a practical lab guide with clear prerequisites, environment setup, exact CLI commands / scripts, expected output, and cleanup/mitigation steps.
2. **Reuse Open-Source Tooling (Don't Reinvent the Wheel):** Prefer real-world open-source AI stack components (e.g., **Ollama**, **Open WebUI**, **PyTorch / HuggingFace `transformers`**, **`llama.cpp`**, **ChromaDB / Qdrant**, **FastAPI**) so learners gain experience with tools actually deployed in production and research.
3. **Reusable Shared Base Environment:** Instead of building 200 bespoke applications, define a small set of reusable foundational stacks (e.g., a Chat/VLM stack, a RAG/Agent stack, a Supply-Chain/Artifact workbench) that multiple node labs can share.
4. **Academic & Defensive Framing:** Align with the PRD's boundaries ([`AI_Security_Research_Graph_PRD.md`](../AI_Security_Research_Graph_PRD.md)): labs demonstrate mechanisms in controlled local sandboxes for educational and defensive understanding.

---

## 1a. Conversation Log (Summary)

The brainstorming session that produced this proposal, in order:

1. **User — idea:** Add hands-on, reproducible labs to the Atlas nodes, in the style of the DVKA workshop. Reuse existing open-source tools (e.g., Ollama, Open WebUI) instead of building custom simulations. Two anchor nodes were offered as examples: `attack-visual-jailbreak` (adversarial image → VLM in Open WebUI) and `family-supply` (unsafe checkpoint loading).
2. **Agent — response:** Endorsed the idea (turns the Atlas from a reference guide into a training ground) and agreed that reusing real software keeps labs realistic. Before writing any lab, proposed settling the foundational tech stack and laid out three approaches (Section 3), recommending **Approach 1: Local Docker Compose** with lightweight models (`llama3.2`, `llava:7b`).
3. **Agent — clarifying question (answered in step 5):**
   > How do you want to handle the hardware limitations of the learners? Should we design the stack to be strictly 100% local (optimizing for small models), or should the foundational setup include a fallback mechanism (e.g., "If your computer can't run this locally, here is how to point the lab to an external API")?
4. **User — handoff:** Asked for the conversation and proposal to be written to `docs/` so another agent can pick up the work.
5. **User — decision (2026-10-25):** *"Both, learners machine and also external API on weaker hardware. I want the hands-on labs to be as real as possible for better research learning experience."* → Recorded as the stack decision in Section 3a.

---

## 2. Concrete Node Examples Discussed

### Example A: Multimodal / Inference-Time Attack (`attack-visual-jailbreak` / `attack-multimodal-injection`)
* **Node:** [`articles/attack-visual-jailbreak.md`](../articles/attack-visual-jailbreak.md) (`https://ai-security-atlas.github.io/?node=attack-visual-jailbreak`)
* **Concept:** Using adversarial perturbations (or contrast with typographic visual prompts in `attack-multimodal-injection`) on an image input to a Vision-Language Model (VLM) to bypass refusal behavior or hijack instructions.
* **Hands-on Lab Vision:**
  * Run a local VLM via **Ollama** (e.g., `llava:7b` or `qwen2.5vl`) or a small local PyTorch VLM when gradient access is needed for FGSM/PGD optimization.
  * Connect **Open WebUI** (or a lightweight shared Gradio/FastAPI app) as the frontend.
  * Guide the user step-by-step:
    1. Test the baseline prompt in Open WebUI and observe the refusal.
    2. Run a provided Python script to generate/apply the visual perturbation (or craft the visual input) and inspect the perturbation delta.
    3. Upload the generated image into Open WebUI with the query and observe how the VLM's behavior shifts.
    4. Explore defense/evaluation takeaways.

### Example B: Supply Chain & Execution Environment (`family-supply` and its member attacks)
* **Node:** [`articles/family-supply.md`](../articles/family-supply.md) (`https://ai-security-atlas.github.io/?node=family-supply`) and child nodes:
  * [`attack-unsafe-load`](../articles/attack-unsafe-load.md) (Unsafe checkpoint deserialization, e.g., PyTorch `pickle` vs `safetensors`)
  * [`attack-artifact-substitution`](../articles/attack-artifact-substitution.md) (Adapter, config, or chat-template tampering)
  * [`attack-dependency`](../articles/attack-dependency.md) (Malicious repository code / `trust_remote_code=True`)
* **Hands-on Lab Vision:**
  * Spin up an isolated container workbench with Python, `torch`, `safetensors`, `gguf`, and `transformers`.
  * Walk the user through concrete CLI exercises:
    1. Create a benign PyTorch checkpoint (`.pt` / `.bin`) and inspect its pickle opcodes using `pickletools`.
    2. Craft a harmless proof-of-concept deserialization payload (e.g., creating a marker file `/tmp/pwned` or printing environment variables upon `torch.load()`).
    3. Reproduce the vulnerable load vs. `weights_only=True` vs. converting the weights to [`format-safetensors`](../articles/format-safetensors.md) ([`defense-safe-load`](../articles/defense-safe-load.md)) to prove why zero-copy data-only tensor containers neutralize the class of bug.

---

## 3. Proposed Foundational Tech Stack Approaches

During initial brainstorming, three architecture approaches were evaluated for running the labs:

### 3a. Decision: Local-First Docker Compose + External API Fallback

The user chose **Approach 1 as the default, with Approach 3's API fallback built in**. Requirements for the stack spec:

* **Realism first.** Labs use the same software people actually deploy (Ollama, Open WebUI, real vector stores, real model files). No mocked "simulations" of an LLM.
* **Default = fully local.** `docker compose up` runs everything on the learner's machine, using small models that run on a typical laptop.
* **Fallback = external API for weaker hardware.** The same containers (Open WebUI, RAG/agent targets) can point at any OpenAI-compatible endpoint by setting environment variables (e.g., in a `.env` file). No other changes to the lab steps.
* **Each lab states whether it supports the fallback.** Prompt, RAG and agent labs (profiles 1–2 in Section 4) work both ways. White-box and supply-chain labs (profiles 3–4) need local execution: they must say so up front and use tiny CPU-friendly models so most laptops can still run them.
* **Where results differ, say so.** If a hosted model behaves differently from the local one (e.g., stronger safety filtering), the lab walkthrough should point this out as a research observation.

### Approach 1: Local Docker Compose Stack (Recommended)
Provide a shared `docker-compose.yml` (with profiles per lab category) that spins up:
* **Inference Runtime:** Ollama (for black-box/chat/RAG/agent labs) + a Python/PyTorch container (for white-box gradient, fine-tuning, and supply-chain labs).
* **Frontend / UI:** Open WebUI connected to Ollama, plus optional vulnerable microservices (e.g., a minimal RAG/Agent target with tool-calling).
* **Pros:**
  * 100% reproducible, offline-capable, and private.
  * Matches the `dvka` workshop philosophy (`docker compose up` -> run commands -> observe).
  * Supports every node category in the Atlas, including white-box gradient attacks (`attack-fgsm`, `attack-gcg`), weight manipulation (`adapt-abliteration`), and supply-chain labs (`attack-unsafe-load`) that are impossible on hosted APIs.
* **Cons:**
  * Requires downloading Docker images and model weights (1–4 GB).
  * Requires reasonable local CPU/RAM/GPU resources (mitigated by standardizing on compact 0.5B–7B models like `qwen2.5:1.5b`, `llama3.2:1b`, `llava:7b`, or `smollm2`).

### Approach 2: Cloud Notebooks (Colab / Kaggle)
Link each node to a hosted Jupyter notebook running on free cloud GPUs.
* **Pros:** Zero local hardware footprint.
* **Cons:** Loses the realistic application feel (harder to interact with Open WebUI, multi-container services, or network/MCP boundaries). Best kept as an optional fallback for heavy white-box GPU labs rather than the primary experience.

### Approach 3: Hybrid (Local UI + Hosted API Fallback)
Run Open WebUI and target apps locally in Docker, pointed at either local Ollama **or** any OpenAI-compatible API endpoint (`OPENAI_API_BASE_URL`).
* **Pros:** Allows learners on low-spec laptops to still run prompt-level, RAG, and agent labs quickly via an external API, while keeping full local execution as the default.
* **Cons:** Cannot run white-box or supply-chain labs over a remote API.

---

## 4. Proposed Lab Archetypes (Mapping the 204 Nodes to Reusable Stacks)

Rather than inventing a new setup for every node, the 204 nodes in the Atlas naturally cluster into **4 reusable lab profiles**:

| Lab Profile | Target Node Types / Families | Reusable Stack Components |
| :--- | :--- | :--- |
| **1. Chat & Multimodal Stack** | `family-prompt`, `attack-jailbreak`, `attack-multimodal-injection`, `attack-prompt-leak` | `ollama` + `open-webui` (using small text & vision models like `llama3.2:1b` / `llava:7b`) |
| **2. RAG, Memory & Agent Stack** | `family-agent`, `family-retrieval`, `attack-indirect-injection`, `attack-rag-poison`, `attack-tool-rugpull`, `attack-excessive-agency` | `ollama` + `open-webui` (or lightweight FastAPI/MCP agent) + local vector store (`chromadb`) + mock tools |
| **3. White-Box & Model Internals Workbench** | `family-representation`, `family-evasion`, `attack-visual-jailbreak` (white-box PGD on a local VLM; model backend optional, used only for a contrast step and transfer checks), `attack-fgsm`, `attack-pgd`, `adapt-abliteration`, `adapt-steering`, `concept-logits`, `concept-gradients` | Isolated Python/PyTorch container (`transformers`, `torch`, `numpy`) running tiny models (`SmolLM2-135M`, `GPT-2`, `MobileNet`) for fast CPU/MPS execution |
| **4. Supply Chain & Artifact Workbench** | `family-supply`, `attack-unsafe-load`, `attack-artifact-substitution`, `attack-adapter-tamper`, `format-safetensors`, `format-gguf`, `format-pytorch` | Isolated Python CLI container (`torch`, `safetensors`, `gguf`, `pickletools`) |

---

## 5. Next Steps & Open Questions for the Implementation Agent

To carry this forward systematically, the next agent should collaborate with the user on:

1. **Hardware & Fallback Strategy — DECIDED (see Section 3a):**
   * Local-first Docker Compose by default, with an OpenAI-compatible API fallback for weaker hardware on the labs that can support it. Next step: draft the foundational stack spec (compose profiles, `.env` variables, model choices) based on Section 3a.
2. **Repository & UI Integration:**
   * Decide where lab files live in the repo (e.g., `labs/docker-compose.yml` for shared infrastructure + `labs/<node-id>/` or a `## Hands-on Lab` section inside `articles/<node-id>.md` rendered in the Atlas Reader UI).
   * Decide if nodes with an interactive lab should get a visual badge/filter in the Atlas UI (e.g., a `has_lab` flag compiled by [`json2hugo.py`](../json2hugo.py)).
3. **Node-by-Node Lab Design:**
   * Start with the two anchor examples (`attack-visual-jailbreak` and `family-supply` / `attack-unsafe-load`) to validate the template, directory structure, and developer experience before scaling across the rest of the catalog.
