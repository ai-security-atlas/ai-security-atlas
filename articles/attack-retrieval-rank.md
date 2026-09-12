Retrieval and ranking manipulation seeks to influence which material a retrieval system selects as evidence, favoring attacker-controlled content over more appropriate sources. It maps to the OWASP LLM Top 10 vector-and-embedding-weaknesses category. The objective is to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md).

## How it works

Retrieval depends on [corpora, vector indexes and rerankers](../nodes/system-index.md) that score candidate passages for relevance and return the top matches. An attacker who understands how those scores are computed may craft content designed to rank highly for targeted queries, increasing the chance that attacker-controlled material is chosen as grounding. The attacker controls the content and its surface features; the victim controls the embedding model, index and ranking function. The manipulation acts on selection rather than on the model's reasoning directly.

A key caveat separates three things that must be measured independently: whether content is discoverable, whether it ranks highly, and whether being retrieved actually changes the generated answer. High rank does not guarantee downstream influence.

The technique belongs to the retrieval-and-knowledge-manipulation family and is closely related to knowledge-base poisoning, but it emphasizes the ranking channel — getting selected — rather than corrupting facts already trusted. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). Defer to the cited retrieval-corruption and trust-hijacking sources for concrete conditions.
