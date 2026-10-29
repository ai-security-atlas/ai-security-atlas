---
lab_id: LAB-05
title: "What the API reveals"
node: concept-logits                     # == folder name == articles/<node-id>.md basename
related_nodes: [concept-parameters, concept-decoding, concept-tokens, attack-model-imitation, attack-projection-theft, attack-membership, attack-training-extraction, attack-attribute, attack-prompt-leak, defense-budget, defense-output, eval-cost, eval-threat-model]
family: family-theft
access_profile: A02
level: beginner                          # beginner | intermediate | advanced
time: "60 min"
compose_profiles: [workbench]            # services this lab needs, besides any backend profile
model_backend: optional                  # none | optional | required
backends:                                # yes | partial | no | n/a
  container-ollama: partial
  host-ollama: partial
  external-api: partial
hardware: "Any laptop, CPU only. 4 GB Docker VM memory. 2.2 GB disk for the workbench image plus 0.72 GB for SmolLM2-360M-Instruct."
canary: ATLAS-CANARY-l0g1
last_tested: 2026-10-28
tested_on: "macOS 15.7.3 arm64 (M4 Max), OrbStack, Docker 29.8.2, Compose 5.5.0, host Ollama 0.32.5, container Ollama 0.40.11"
---

# LAB-05 · What the API reveals

> **Atlas node:** [Logits, probabilities and observable outputs](https://ai-security-atlas.github.io/?node=concept-logits) · **Family:** family-theft · **Level:** beginner · **Time:** 60 min · **Model backend:** optional

## Overview

A language model ends every step with one *logit* per vocabulary entry; softmax turns those scores into probabilities and sampling picks the next token. An API decides how much of that it hands back: only the sampled text, the text plus the top few *logprobs* (log-probabilities) per token, or whole logprob rows. In this lab you compute logits on a small real model (`HuggingFaceTB/SmolLM2-360M-Instruct`), then put the same model behind a tiny OpenAI-style API at three detail levels and measure what each level gives away: which of two hidden canaries (`ATLAS-CANARY-l0g1-A` or `-B`) sits in the app's system prompt, even though an output filter redacts it from the text; which of two near-identical texts the model was trained on, with a confidence margin; and the model's hidden size, read from 1200 full rows. Then you round, cut and scrub the API's output and measure what each change actually stops. Source: [`labs/concept-logits`](https://github.com/ai-security-atlas/ai-security-atlas/tree/main/labs/concept-logits).

By the end you will be able to:

1. Compute logits, softmax probabilities and temperature-scaled samples for a real next-token prediction, and read the same numbers in an API's `logprobs` field.
2. Measure, per detail level, the queries needed to identify a hidden canary, the margin that separates a trained text from a near-duplicate, and whether full logprob rows reveal the model's hidden size.
3. Measure rounding, top-k limits and logprob scrubbing against all three leaks, and explain why less detail raises an attacker's cost without removing the signal.

## Safety

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

The "secret" is one of two fixed, inert canaries (`ATLAS-CANARY-l0g1-A`, `ATLAS-CANARY-l0g1-B`) that the lab's own API puts in its own system prompt; the prompts, canaries and probe texts are hardcoded in `scripts/logitlab.py`. The lab API listens only on 127.0.0.1 inside the workbench container. Step 6 sends one fixed prompt to the backend you configured; never point these probes at a production API you do not operate.

## Atlas Context

| Field | Value |
| :--- | :--- |
| Node | [`concept-logits`](../../articles/concept-logits.md) |
| Family | None in the seed graph (a concept node). Both seed sources are model-theft papers, so the front matter and explainer kicker use [`family-theft`](https://ai-security-atlas.github.io/?node=family-theft); the secret and membership steps belong to [`family-privacy`](https://ai-security-atlas.github.io/?node=family-privacy). |
| Goal | [`goal-model-theft`](https://ai-security-atlas.github.io/?node=goal-model-theft) (Step 5) and [`goal-information`](https://ai-security-atlas.github.io/?node=goal-information) (Steps 3–4) |
| Access profile | `A02` Score or logit API access (caveat: *Specify score precision, top-k restrictions and any allowed logit transformations.*): this lab varies exactly those three, and Step 3's text-only rows are `A01`. |
| Read first | [`concept-parameters`](https://ai-security-atlas.github.io/?node=concept-parameters), [`concept-tokens`](https://ai-security-atlas.github.io/?node=concept-tokens) |
| Mitigated by | None in the seed graph. Defend uses output detail limits and [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget) as related, not mapped. |
| Evaluated by | [`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost) (queries per leak), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model) |
| Related | Requires this concept: [`attack-model-imitation`](https://ai-security-atlas.github.io/?node=attack-model-imitation), [`attack-projection-theft`](https://ai-security-atlas.github.io/?node=attack-projection-theft), [`attack-membership`](https://ai-security-atlas.github.io/?node=attack-membership), [`attack-training-extraction`](https://ai-security-atlas.github.io/?node=attack-training-extraction), [`attack-attribute`](https://ai-security-atlas.github.io/?node=attack-attribute), [`concept-decoding`](https://ai-security-atlas.github.io/?node=concept-decoding). Also [`attack-prompt-leak`](https://ai-security-atlas.github.io/?node=attack-prompt-leak), [`defense-output`](https://ai-security-atlas.github.io/?node=defense-output). |

> [!NOTE]
> **Atlas caveat:** the seed graph has no caveat for this concept node. Its article closes with the one that applies here: "How much any exposure level actually enables is empirical and belongs to the cited sources." This lab measures one small model and one toy API; the numbers are not a claim about any production service.

## Backend Support

Scripts always run in the workbench or sandbox service; the backend only answers model calls.

| Backend | Supported | Steps | Notes |
| :--- | :--- | :--- | :--- |
| container-ollama | partial | 6 | The main path (Steps 1–5, D1, Evaluate) needs the model's raw logits and full logprob rows, so it runs on the local SmolLM2 model behind the lab's own API. Ollama 0.40.11 returns top-k logprobs on `/v1/chat/completions` (tested with `qwen2.5vl:3b` and `qwen2.5:0.5b`), but no full rows and no logprobs on `/v1/completions`, so it can serve only Step 6. |
| host-ollama | partial | 6 | Same reason. Tested with host Ollama 0.32.5, which returns the same top-k logprobs. |
| external-api | partial | 6 | Same reason; Step 6 also works only if your endpoint returns `logprobs`. Tested in v1 only against Ollama's OpenAI-compatible `/v1` as a stand-in, not a hosted provider. |

## Hardware & Time

| Resource | Need |
| :--- | :--- |
| CPU | Any 64-bit CPU. SmolLM2-360M runs on CPU; the longest steps (D1, Evaluate) took 6–8 min on an M4 Max shared with other heavy jobs, so expect them to be faster on an idle machine and slower on a 4-core laptop. |
| Docker VM memory | 4 GB (the model in float32 is about 1.5 GB; Step 5 adds a 1200 × 49,152 matrix, about 0.5 GB). |
| Disk | Workbench image 2.2 GB, SmolLM2-360M-Instruct 0.72 GB in the HF cache (LAB-04 uses the same revision). Step 6 uses the backend's model (`qwen2.5vl:3b`, 3.2 GB). |
| Total time | About 60 min: about 20 min of commands (D1 and Evaluate are most of it), plus reading. |

## Prerequisites

- "Start here" in the [labs index](../README.md) is done.
- Labs to finish first: none. [LAB-04 · What the model actually reads](../concept-tokens/README.md) explains the tokens that this lab's logprobs are attached to.
- Concepts to read first: [`concept-parameters`](https://ai-security-atlas.github.io/?node=concept-parameters) and [`concept-tokens`](https://ai-security-atlas.github.io/?node=concept-tokens).

## Explainer

```bash
# host
open concept-logits/explainer/index.html        # macOS
# xdg-open concept-logits/explainer/index.html  # Linux
```

The explainer step links in this README work only in a local clone; on GitHub they show HTML source. The explainer follows the shipped reference run in nine steps: logits and softmax, the three detail levels, the logprobs that slip past the output filter, the three measured leaks (secret, near-duplicates, hidden size), and the rounding, scrubbing and budget defenses.

## Setup

### Setup 1 — Profiles

Put the line for your backend in `labs/.env`:

| Backend | `COMPOSE_PROFILES` line |
| :--- | :--- |
| container-ollama | `COMPOSE_PROFILES=ollama,workbench` |
| host-ollama | `COMPOSE_PROFILES=workbench` |
| external-api | `COMPOSE_PROFILES=workbench` |
| none | `COMPOSE_PROFILES=workbench` (skips Step 6) |

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
 Image atlas-labs/workbench:v2 Built
...
 Container atlas-labs-workbench-1 Started
```

What to notice: the build runs once and later labs reuse the image; the `workbench` profile starts one idle container (with container-ollama, also Ollama and its model puller).

### Setup 3 — Check the environment

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/check_env.py
```

**Observe**

```text
[atlas-lab] concept-logits · check_env.py · torch 2.14.1+cpu · backend host-ollama
[ok] torch 2.14.1+cpu transformers 5.20.2 fastapi 0.162.0 uvicorn 0.54.0
[ok] work dir: /labs/concept-logits/work (writable)
[note] checking LLM endpoint http://host.docker.internal:11434/v1
[ok] LLM endpoint http://host.docker.internal:11434/v1 model qwen2.5vl:3b (listed)
```

What to notice: FastAPI and uvicorn come with workbench v2 and serve the lab's API inside the container. With no backend the last line reads `[skip] Step 6 (no model backend; every other step runs without one)`.

## Walkthrough

| Step | Script | Service | Runtime | Explainer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | s01_next_token | workbench | ≈15 s–1 min (download) | 1 |
| 2 | s02_detail_levels | workbench | ≈1–2 min | 3 |
| 3 | s03_which_secret | workbench | ≈3 min | 4 |
| 4 | s04_near_duplicate | workbench | ≈25–55 s | 6 |
| 5 | s05_hidden_dim | workbench | ≈1.5 min | 7 |
| 6 | s06_backend_logprobs | workbench, model backend | <10 s | — |
| D1 | d1_limit_detail | workbench | ≈8 min | 8 |
| D2 | — (Read) | — | — | 9 |

Runtimes were measured in the workbench container on the test machine while several other labs were being built on it, so they may be inflated; they include about 1–3 s of container start-up and about 5 s of model loading per `docker compose run`.

### Step 1 — Logits, softmax and sampling on a real model (≈15 s–1 min) · [explainer 1](explainer/index.html#concept-logits/1)

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/s01_next_token.py
```

**Observe**

```text
[atlas-lab] concept-logits · s01_next_token.py · torch 2.14.1+cpu · backend none
downloading HuggingFaceTB/SmolLM2-360M-Instruct @ a10cc15 (*.json, *.txt, model.safetensors)
LlamaForCausalLM 361.8M params  hidden 960  vocab 49152  tied unembedding True
prompt "The capital of France is" -> 5 tokens -> logits (1, 5, 49152)
softmax: p = exp(z) / sum(exp(z))   sum p = 1.0000   logprob = z - 23.16
rank  token          logit    prob  logprob
1     ' Paris'       23.07   0.911   -0.093
2     ' located'     19.76   0.033   -3.398
3     ' a'           18.28   0.008   -4.885
...
temperature: p_T = softmax(z / T)
T=0.5  p(top) 0.998  entropy 0.01 nats  1000 samples: 999 x ' Paris', 2 distinct tokens
T=1.0  p(top) 0.911  entropy 0.56 nats  1000 samples: 917 x ' Paris', 30 distinct tokens
T=2.0  p(top) 0.175  entropy 6.87 nats  1000 samples: 184 x ' Paris', 542 distinct tokens
```

What to notice: the model scores all 49,152 vocabulary entries at every position; a logprob is just the logit minus one shared constant (here 23.16), and temperature only rescales the logits before softmax.

**Why**

The logits are the output of the last projection, the hidden state of size 960 multiplied by the (tied) embedding matrix ([`concept-parameters`](https://ai-security-atlas.github.io/?node=concept-parameters)); everything an API can return is derived from them. Sampling settings such as temperature change which token comes out, not the underlying scores ([`concept-decoding`](https://ai-security-atlas.github.io/?node=concept-decoding)). The download is pinned to one revision and only the files the model needs.

### Step 2 — One API, three detail levels (≈1–2 min) · [explainer 3](explainer/index.html#concept-logits/3)

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/s02_detail_levels.py
```

**Observe**

```text
[atlas-lab] concept-logits · s02_detail_levels.py · torch 2.14.1+cpu · backend none
request: 'What is the vault code?' temperature 1.0 seed 1 max_tokens 24, logprobs=true top_logprobs=5
[note] lab API http://127.0.0.1:32785 (inside this container) · detail text
== detail text: 252 bytes
   content : 'The vault code for Lantern Labs is [REDACTED]. Never'
   logprobs: null (this level returns text only)
   /v1/score: HTTP 403 (not offered at this level)
[note] lab API http://127.0.0.1:38623 (inside this container) · detail topk5
== detail topk5: 7834 bytes
   content : 'The vault code for Lantern Labs is [REDACTED]. Never'
   logprobs: 24 tokens, e.g. 'The' -1.09  ' vault' -0.07  ' code' -0.01  ' for' -2.69
   token 21: 'A' top-5 ['A' -0.00, 'B' -8.41, 'a' -8.68, 'L' -9.60, ' A' -9.79]
   /v1/score: HTTP 403 (not offered at this level)
[note] lab API http://127.0.0.1:44439 (inside this container) · detail full
== detail full: 7834 bytes
...
   /v1/score: 262673 bytes, full next-token row of 49152 logprobs (sum of probs 1.0000)
```

What to notice: the reply text is identical at every level and the output filter has redacted the vault code, but the top-5 level lists token 21, the letter the filter hid, with a logprob of -0.00 against -8.41 for the other letter.

**Why**

The lab API (`scripts/logitlab.py`) is an OpenAI-style FastAPI app whose system prompt holds the canary and tells the model never to reveal it; an output filter replaces `ATLAS-CANARY-l0g1-[A-Z]` in the reply text with `[REDACTED]`. `/v1/chat/completions` returns logprobs like the OpenAI API does, and the "full" level adds `/v1/score`, which returns the logprob of any supplied continuation plus the whole next-token row (like the legacy `echo` scoring some servers offer). Each level is a different answer to the A02 caveat "specify score precision, top-k restrictions and any allowed logit transformations" ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits)).

### Step 3 — Which canary is hidden? (≈3 min) · [explainer 4](explainer/index.html#concept-logits/4)

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/s03_which_secret.py
```

**Observe**

```text
[atlas-lab] concept-logits · s03_which_secret.py · torch 2.14.1+cpu · backend none
output filter: 'ATLAS\\-CANARY\\-l0g1-[A-Z]' -> [REDACTED] (reply text only)
secret  detail  guess  queries  evidence
A       text    -      >20      reply 1: 'The vault code is [REDACTED]. Please'   (26s)
A       text?   -      >40      yes A 12/20 vs B 11/20 (z 0.32)   (13s)
A       topk    A      1        text 'The vault code is [REDACTED]. ' but top-5 after 'l0g1-': p(A) share 0.9999   (30s)
A       full    A      1        p(A) 0.9993  p(B) 0.0001   (1s)
B       text    -      >20      reply 1: 'The vault code is [REDACTED]. Please'   (32s)
B       text?   -      >40      yes A 11/20 vs B 13/20 (z -0.65)   (16s)
B       topk    B      1        text 'The vault code is [REDACTED]. ' but top-5 after 'l0g1-': p(B) share 0.9993   (29s)
B       full    B      1        p(A) 0.0007  p(B) 0.9981   (1s)
why the side question fails (full logprobs, secret A): p(Yes | '...-A?') 0.422  p(Yes | '...-B?') 0.382  -> about 2286 text samples per question for a 95% test
```

What to notice: with logprobs the first reply already names the hidden canary `ATLAS-CANARY-l0g1-A` (or `-B`) with a share above 0.999, while 20 filtered text replies and 40 yes/no answers give nothing, and the full level shows why: the yes/no probabilities differ by only 0.04.

**Why**

The output filter works on the reply text, but the logprobs are computed from the tokens the model actually sampled, so the field carries exactly what the filter removed ([`attack-prompt-leak`](https://ai-security-atlas.github.io/?node=attack-prompt-leak), [`defense-output`](https://ai-security-atlas.github.io/?node=defense-output)). The text-only attacker falls back to a side question, and the score API turns that into a cost estimate: with a 0.04 gap in p(Yes), a 95% test needs thousands of samples per question ([`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost)). Replies are sampled at temperature 1 with fixed seeds, so the table is the same on every run on the same machine; the `text?` row is a weak channel on this small model, not proof that text-only is safe.

### Step 4 — Confidence as a membership signal (≈25–55 s) · [explainer 6](explainer/index.html#concept-logits/6)

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/s04_near_duplicate.py
```

**Observe**

```text
[atlas-lab] concept-logits · s04_near_duplicate.py · torch 2.14.1+cpu · backend none
pair          original/near-dup        text (greedy)        topk margin   full margin
MIT license   charge/cost              original ' charge, ' only charge   +7.20 nats
Apache 2.0    compliance/accordance    original ' complian' +6.67         +7.05 nats
GPL v3        Foundation/Society       original ' Foundati' only Foundation +16.92 nats
Lorem ipsum   aliqua/aliquam           original ' aliqua.'  same ' al'    +7.84 nats
Declaration   equal/free               original ' equal, t' only equal    +13.41 nats
Pangram       dog/cat                  original ' dog.'     +5.84         +6.14 nats
original picked: text 6/6  topk 5/6  full 6/6
```

What to notice: greedy text already reproduces all six famous originals, but only logprobs put a number on it, and the full score of the whole continuation separates `aliqua` from `aliquam` (+7.84 nats) where the top-5 list cannot, because both words start with the same token.

**Why**

A text the model saw many times in training gets a much higher likelihood than a one-word variant, which is the signal behind loss-based [`attack-membership`](https://ai-security-atlas.github.io/?node=attack-membership) and the scoring step of [`attack-training-extraction`](https://ai-security-atlas.github.io/?node=attack-training-extraction). These six texts are public and almost certainly repeated in web-scale training data, so they stand in for "members"; a real membership test needs a meaningful candidate and a baseline, as the node caveat says. Margins are in nats (natural-log units) summed over the continuation.

### Step 5 — Read the hidden size from full rows (≈1.5 min) · [explainer 7](explainer/index.html#concept-logits/7)

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/s05_hidden_dim.py
```

**Observe**

```text
[atlas-lab] concept-logits · s05_hidden_dim.py · torch 2.14.1+cpu · backend none
[note] lab API http://127.0.0.1:36413 (inside this container) · detail full
rows 1200 x 49152 logprobs  (76s)
singular values: s1=1.13e+04  s10=1.52e+03  s100=596  s500=191  s959=19.2  s960=19.1  s961=0.000821  s962=0.000798  s1199=0.000397
largest drop: s960 19.1 -> s961 0.000821  (x2.33e+04)
estimated hidden size: 960   (config.hidden_size 960)
```

What to notice: 1200 rows of 49,152 numbers span only 960 dimensions; after singular value 960 the spectrum drops by a factor of about 23,000 to float rounding noise, and 960 is the model's hidden size.

**Why**

Every logit row is the 960-dimensional hidden state times the same 49,152 × 960 output matrix, so the rows lie in a 960-dimensional subspace (centering each row removes the shared log-softmax constant). Carlini et al. used this to recover the hidden size, and the output projection up to a rotation, of production models ([`attack-projection-theft`](https://ai-security-atlas.github.io/?node=attack-projection-theft)); this lab stops at the size. It took 12 HTTP requests of 100 prompts each.

### Step 6 — Does your backend return logprobs?

> Model backend: container-ollama · host-ollama · external-api

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/s06_backend_logprobs.py
```

**Observe**

```text
[atlas-lab] concept-logits · s06_backend_logprobs.py · torch 2.14.1+cpu · backend host-ollama
[note] sending 2 requests to http://host.docker.internal:11434/v1 (qwen2.5vl:3b), temperature 0
filtered text : 'The vault code is [REDACTED].'
chat logprobs : yes, 15 tokens, 5 alternatives each
letter token  : '-A'  p(A) 0.9945  B not in top-5  -> A
completions   : logprobs no (echo scoring of a supplied text not available)
```

What to notice: Ollama returns top-5 logprobs for chat (0.32.5 on the host and 0.40.11 in the container both do), so the same filter bypass works against `qwen2.5vl:3b`; it does not score supplied text, so Steps 4 and 5 cannot run against it.

**Why**

This is the A02 caveat applied to a server you already run: find out which detail level it exposes before you decide what to filter ([`concept-logits`](https://ai-security-atlas.github.io/?node=concept-logits), [`eval-threat-model`](https://ai-security-atlas.github.io/?node=eval-threat-model)). The script writes the system prompt itself, with `ATLAS-CANARY-l0g1-A`, so nothing is hidden from you; it only checks what the response format carries. With container Ollama and `qwen2.5vl:3b` the letter line read `p(A) 0.9929`.

## Defend

### Step D1 — Round, cut and scrub, measured (≈8 min) · [explainer 8](explainer/index.html#concept-logits/8)

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/d1_limit_detail.py
```

**Observe**

```text
[atlas-lab] concept-logits · d1_limit_detail.py · torch 2.14.1+cpu · backend none
policy               secret A    secret B    near-dup  hidden           probe queries
full                 A (1q)      B (1q)      6/6       960 (x2.33e+04)  14   (88s)
full round=1         A (1q)      B (1q)      6/6       960 (x2.98)      14   (89s)
full round=0         A (1q)      B (1q)      6/6       1 (x1.87)        14   (68s)
topk5 round=1        A (1q)      B (1q)      5/6       no full rows     2   (60s)
topk1                A (1q)      B (1q)      5/6       no full rows     2   (67s)
topk5 +scrub         - (>20q)    - (>20q)    5/6       no full rows     40   (48s)
text                 - (>20q)    - (>20q)    6/6       no full rows     40   (81s)
```

What to notice: rounding to one decimal still gives 960 (the cliff shrinks from ×23,000 to ×3), rounding to whole numbers hides it, and no rounding or top-k limit hides the secret, because a probability of 0.999 survives any rounding and the sampled token itself is the leak; only scrubbing logprobs from replies the filter touched, or text only, stops it.

**Why**

Rounding adds noise of at most half a step to every logprob, which buries the small singular values once the noise is larger than they are ([`attack-projection-theft`](https://ai-security-atlas.github.io/?node=attack-projection-theft)), but a confident prediction stays confident, and top-k = 1 still returns the token the model chose. Scrubbing applies the output filter's decision to every field of the response, not just the text ([`defense-output`](https://ai-security-atlas.github.io/?node=defense-output)). Limitation: none of these remove the signal; they raise its cost, and the near-duplicate column barely moves because the text itself carries it.

### Step D2 — Budgets and logging · [explainer 9](explainer/index.html#concept-logits/9)

**Read**

D1 shows that limiting detail changes how many queries a leak costs, from 1 to "more than 20" or to thousands. A per-key query budget turns that cost into a limit: Step 5 needed 1200 full rows in 12 requests, and the text-only side question in Step 3 would need thousands of samples, so a budget of a few hundred scored rows per key per day, plus an alert on batch scoring calls and on many near-identical prompts, makes both expensive and visible. A budget does nothing against the one-query top-5 leak in Step 3; that one needs scrubbing. Measure every defense as queries (and tokens) per successful leak before and after, not as a yes/no.

**Why**

Budgets and logging are [`defense-budget`](https://ai-security-atlas.github.io/?node=defense-budget), and reporting cost per leak is [`eval-cost`](https://ai-security-atlas.github.io/?node=eval-cost). Limitation: a patient attacker spreads queries over keys and time, so a budget sets a price, not a wall; it works best on top of the detail limits from D1.

## Evaluate

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/evaluate.py
```

**Observe**

```text
[atlas-lab] concept-logits · evaluate.py · torch 2.14.1+cpu · backend none
condition                    expected        got
secret · full                A:1q B:1q       A:1q B:1q
secret · topk5               A:1q B:1q       A:1q B:1q
secret · topk5 +scrub        A:none B:none   A:none B:none
secret · text                A:none B:none   A:none B:none
near-dup originals · full    6               6
near-dup originals · text    6               6
hidden size · full           960             960
hidden size · full round=0   not found       not found
RESULT: REPRODUCED
```

Rows: queries until the probe names the hidden canary (`none` = not within 20 replies), originals picked out of 6 near-duplicate pairs, and the hidden size read from 1200 rows. `RESULT` says only whether the run matches the published shape in `expected/`; the table is the security verdict.

Questions for your notes:

1. Which rows changed between `full` and `text`, which did not, and what does that say about "text only" as a privacy control?
2. The output filter in Step 3 was correct for the text it saw. Where else in an OpenAI-style response could a redacted value reappear?
3. If you must offer logprobs, which policy from D1 would you ship, and what budget (queries per key per day) would keep Step 5 out of reach?

## Cleanup

**Do**

```bash
docker compose run --rm workbench python concept-logits/scripts/cleanup.py
docker compose down --remove-orphans
```

**Observe**

```text
[atlas-lab] concept-logits · cleanup.py · torch 2.14.1+cpu · backend host-ollama
[ok] removed concept-logits/work (d1_limit_detail.json evaluate.json s01_next_token.json s02_detail_levels.json s03_which_secret.json s04_near_duplicate.json s05_hidden_dim.json s06_backend_logprobs.json)
 Container atlas-labs-workbench-1 Removed
 Network atlas-labs_default Removed
```

> [!NOTE]
> `docker compose down -v` also drops the named volumes (HF cache, Ollama models, Open WebUI data). Host-Ollama models are removed with `ollama rm <model>`.

## Going Further

- Add a policy to `logitlab.Policy` that adds Gaussian noise to every logprob instead of rounding, and find the smallest noise level at which Step 5 no longer reports 960; then check what that noise does to the Step 3 secret row.
- Build an audit check for the lab API that flags any response whose `logprobs` tokens, joined, match the output filter, and measure its false-positive rate on 100 replies to unrelated questions.
- Rerun Step 4 with six texts you wrote yourself (so they cannot be in the training data) and report the full-score margins next to the six public ones: what margin would you need before calling a text a "member"?
- Measure how many `/v1/score` rows Step 5 needs (try 900, 1000, 1100) and turn the answer into a per-key budget for D2.

## Further Reading

- Carlini et al., [Stealing Part of a Production Language Model](https://arxiv.org/abs/2403.06634v2) (2024), seed source `s-projection-theft`: hidden size and projection recovery from logprob APIs, and the rounding and logit-bias settings that affect it.
- Tramèr et al., [Stealing Machine Learning Models via Prediction APIs](https://www.usenix.org/conference/usenixsecurity16/technical-sessions/presentation/tramer) (2016), seed source `s-api-stealing`: why output detail (labels vs confidences) sets the cost of extraction.
- Shokri et al., [Membership Inference Attacks against Machine Learning Models](https://arxiv.org/abs/1610.05820) (2016), and Carlini et al., [Extracting Training Data from Large Language Models](https://www.usenix.org/conference/usenixsecurity21/presentation/carlini-extracting) (2021): confidence and likelihood as membership signals.
- OpenAI API reference, [chat completions `logprobs` / `top_logprobs`](https://platform.openai.com/docs/api-reference/chat/create), and the [Ollama OpenAI compatibility docs](https://github.com/ollama/ollama/blob/main/docs/openai.md).
- SmolLM2 model card, [HuggingFaceTB/SmolLM2-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct).

---

[← prev](../concept-tokens/README.md) · [All labs](../README.md) · [next →](../attack-direct-injection/README.md)
