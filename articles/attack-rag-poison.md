RAG knowledge-base poisoning inserts or modifies the evidence a retrieval system can surface, so that generated answers are steered toward attacker-preferred conclusions. It maps to OWASP LLM Top 10 categories for vector-and-embedding weaknesses and misinformation. The objective is to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md).

## How it works

A retrieval pipeline draws on [corpora, vector indexes and rerankers](../nodes/system-index.md) to select passages that ground a [retrieval-augmented generation](../nodes/system-rag.md) response. If an attacker can add or alter documents in that corpus, the poisoned content may later be retrieved and treated as authoritative evidence. The attacker controls what enters the knowledge base; the victim system controls indexing, retrieval and how retrieved text is weighed. Influence therefore depends on whether poisoned material is actually selected at query time.

An important distinction: corrupting knowledge is not the same as an instruction-bearing prompt injection. Poisoning changes what the model believes to be true, whereas injection smuggles directives. That said, poisoned content can [enable indirect prompt injection](../nodes/attack-indirect-injection.md) or [persistent agent-memory poisoning](../nodes/attack-memory-poison.md) when the retrieved text carries instructions.

The technique sits within the retrieval-and-knowledge-manipulation family. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For concrete corruption constructions and measured effects, defer to the cited source.
