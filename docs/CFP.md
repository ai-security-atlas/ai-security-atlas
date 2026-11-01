# Session Title

**Beyond the Prompt: Hands-On AI Red Teaming**

# Abstract

AI systems are not just models. They are checkpoints you download, adapters you merge, tokenizers, prompts, retrievers, servers and APIs, and every one of those pieces can be attacked. In this workshop you'll learn how AI systems are attacked, defended and evaluated by doing it yourself: loading a checkpoint that runs code, hijacking a support bot, fooling a classifier with one gradient step, stealing a model through its API and leaking another tenant's prompt from a shared server. Everything runs locally in Docker, on CPU, with harmless canary payloads, and every attack ends with a defense you measure.

# Description

Everyone wants to talk about AI security, but most of the content out there stops at "prompt injection is bad". Security teams are being asked to review, deploy and defend AI systems today, and very few people have actually seen how these attacks work under the hood, or how well the defenses really hold up when you measure them.

The AI Security Atlas is an open-source project I built to close that gap. It has two parts. The first is a knowledge graph of 204 topics and 650 typed relationships that connects what an adversary wants (the objective) to how they get it (the mechanism), what they need first (the prerequisites), which systems it applies to, the evidence behind it (97 primary sources), and the controls that address it. The second is a set of hands-on labs: local Docker reproductions of real attack mechanisms using real open-source tools and small open models, each with an animated explainer and a defense chapter.

In this workshop, we'll use the theory to build a mental model of the AI attack surface, and then use the labs to break and defend each layer of it:

- **The model supply chain:** a PyTorch checkpoint looks like data, but loading it runs a pickle program. You'll hide a payload in a working checkpoint, watch it run during `torch.load()` while the model keeps answering, and then see the same idea with no pickle at all through `trust_remote_code`. Then you'll compare two LoRA adapters with the same size, config and tensor shapes, where only one of them is backdoored.
- **The prompt layer:** a model never reads characters, it reads tokens. You'll forge a system turn by typing control tokens into a chat box, hijack a support bot with a catalogue of direct prompt injections, and make a vision-language model follow instructions written on a picture instead of the user's question.
- **Evasion:** one signed gradient step at ε = 0.2 drops a digit classifier from 98% accuracy to under 4%, while random noise of the same size barely matters. Then we push it further with PGD against a real vision-language model until its caption becomes our canary.
- **Theft and privacy:** you'll copy a "proprietary" classifier through its prediction API with a few hundred queries, find out which hidden canary is in a system prompt from the logprobs an API returns, decide whether a record was in a model's training set, and read another tenant's activity and prompt from a shared llama.cpp server running its default settings.
- **Retrieval:** we'll take apart a RAG assistant stage by stage (chunks, embeddings, index, retrieval, prompt assembly) and watch one tenant's documents end up in another tenant's answer.
- **Measuring attacks honestly:** an attack success rate is a measurement, not a property of the attack. On the same 80 replies, just changing the grader moves the ASR from 19% to 66%. You'll learn how to validate an LLM judge, pin a run and report results a reviewer can trust.

Every lab follows the same pattern: understand the system, reproduce the mechanism, measure it, and then measure what actually stops it (safetensors, allowlist loaders, scanners, instruction hierarchies, output filters, adversarial training, query budgets, differential privacy, authentication and more). The goal isn't to collect tricks; it's to leave with a clear way of thinking about where an AI system can break and how to check whether a control really works.

The labs are safe by design. Every "successful attack" ends in an inert signal, a fixed canary string or a marker file, and everything runs against models and files you create on your own machine. No GPU, no cloud account and no API keys are required.

This workshop is built for red teamers and security researchers who already know how to attack traditional systems and now have AI in scope. Each attack is framed by the access it needs: a file the victim downloads, a chat box, a prediction API, logprobs, model weights and gradients, or a shared inference server. You'll leave with a working AI red team playbook that goes well beyond prompt injection, a local range to keep practicing on, and a methodology to report findings with numbers that hold up.

# Session details

## Format

- AI security theory talk: ~45 mins
- Q/A for intro talk: 10 mins
- Break: 10 mins
- Hands-on attack and defense workshop: 3 hrs

Each lab takes 45 to 120 minutes on its own, so during the workshop we'll go through the core steps of each module together, and attendees keep the full labs to finish at home.

## Outline

- Introduction
- How AI systems are built (and attacked)
  - Tokens, logits and chat templates: what the model actually reads and what the API reveals
  - The AI lifecycle: data, training, fine-tuning, artifacts, serving, applications
  - Thinking like the Atlas: objective → mechanism → prerequisites → architecture → evidence → control
  - Attack families: supply chain, prompt, evasion, theft, privacy, retrieval, training
- Module 1: Model supply chain
  - What `torch.load` really runs (pickle opcodes, `GLOBAL` and `REDUCE`)
  - `from_pretrained` ran my code (`trust_remote_code`, `auto_map`, `.pth` files)
  - What a 2 MB adapter changes (LoRA, load vs. merge, a backdoored adapter)
  - Defenses: safetensors, `weights_only`, scanners, pinned manifests, sandboxes
- Module 2: The prompt layer
  - Control tokens and forged system turns
  - Direct prompt injection against a support bot
  - Instructions written on a picture (multimodal injection)
  - Defenses: instruction hierarchy, input/output filtering, privilege separation
- Module 3: Evasion
  - FGSM: one gradient step against a digit classifier
  - PGD against a vision-language model with invisible pixels
  - Defenses: preprocessing, adversarial training, adaptive attackers
- Module 4: Theft and privacy
  - Stealing a classifier through its API
  - What logprobs leak
  - Membership inference: was this record in the training set?
  - What the server adds: multi-tenant llama.cpp, `/slots`, prompt cache side channels
  - Defenses: answer detail, query budgets, differential privacy, server hardening
- Module 5: Retrieval
  - The five components of RAG
  - Cross-tenant leakage through shared indexes
- Module 6: Measuring an attack honestly
  - Graders, LLM judges, trials, seeds, baselines and run manifests
- Final thoughts

This workshop is based on my open-source project published at https://github.com/ai-security-atlas/ai-security-atlas (labs in `labs/`, site at https://ai-security-atlas.github.io/).

## Technical requirements

- Comfortable with Linux, the command line and Docker
- Able to read Python (we'll read and modify attack scripts, not write them from scratch)
- Offensive security or security research experience (pentesting, red teaming, AppSec, vulnerability research)
- No prior machine learning experience required: the theory section covers the ML concepts each attack depends on

## Who should attend

This workshop is built for people who attack or assess systems for a living and now have AI in scope:

- AI/ML red teamers who want to go beyond prompt injection and jailbreaks, into the model supply chain, gradients, APIs and serving infrastructure
- Penetration testers and offensive security engineers starting to get AI applications, models and MLOps platforms in their engagements
- Security researchers working on adversarial ML, model theft, training data privacy or LLM application security
- AppSec and product security engineers reviewing model artifacts, fine-tuning pipelines, RAG systems and inference servers
- Detection and defense engineers who want to understand which controls actually stop these attacks, and how to measure them

You'll get the most out of it if you want to understand the mechanism behind each attack, not just run a tool against a chatbot.

## Required materials

- Laptop with at least 8 GB of RAM (16 GB is recommended)
- Laptop with at least 20 GB of free disk space (for the workbench image and the small open models)
- Docker 24 or newer with Compose 2.20 or newer
- Linux or macOS, or a Windows machine with WSL2. No GPU required, everything runs on CPU
- Internet connection, mostly to pull the Docker images and models. To avoid depending on conference Wi-Fi, attendees will get instructions to build the workbench image and pull the models before the workshop

## References

- https://ai-security-atlas.github.io/
- https://github.com/ai-security-atlas/ai-security-atlas
- https://github.com/alevsk/speaker
