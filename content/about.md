---
title: About the Atlas
type: page
eyebrow: About & FAQ
summary: What the AI Security Atlas is, how it is built, and how to use it.
---

The **AI Security Atlas** is a **learning platform** for understanding AI security
through realistic scenarios. It pairs an opinionated, evidence-linked knowledge
graph of how AI systems are attacked, defended, and evaluated with hands-on labs
that reproduce selected mechanisms on your own machine. The graph connects an
adversary's objective to the underlying mechanism, its prerequisites, the
architectures it applies to, the evidence behind it, and the controls that
address it.

The website executes nothing, probes no third-party services and hosts no
payloads.

## How to use it

- **Start from an objective.** The Explorer opens on ten adversary objectives.
  Pick one to see its techniques grouped by family, then open a technique to read
  its prerequisites, evidence, and candidate mitigations.
- **Follow the graph.** Every entry links to the concepts it depends on and the
  defenses and evaluations that relate to it. Toggle the graph view to see the
  local neighborhood of any topic.
- **Search.** Jump straight to a technique, concept, paper, or alias.
- **Check the evidence.** Each claim links to a primary source with an honest
  verification depth. A citation does not mean every sentence was reproduced.

## Frequently asked questions

### Is this a list of working exploits?

No. The Atlas describes mechanisms at a conceptual level and links to published
research. It is designed for learning and for orienting real, authorized security
work — not for carrying out attacks.

The hands-on labs are separate from the website: they live under `labs/` in the
source repository, run only locally in Docker, and reproduce mechanisms with inert
canary payloads against files and models the learner creates for the lab.

### What does "seed" or "draft" mean on a topic?

**Seed** entries carry a definition, routing metadata, and sources. **Draft**
entries add a conceptual overview that has not yet been reviewed. Neither is a
peer-reviewed tutorial; treat them as a starting point and follow the sources.

### How is the content produced?

Markdown is the source of truth. A deterministic compiler projects it into the
graph, index, search, and pages you see here. Some overviews are AI-drafted and
clearly labeled as such; they are never promoted to "reviewed" automatically.

### How current is it?

Sources were checked against their primary pages and abstracts. No experiments
were reproduced. The Atlas is a living reference and does not claim complete
coverage of all existing or future techniques.
