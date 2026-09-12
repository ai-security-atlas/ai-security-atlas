Retrieval-augmented generation grounds a model's answers in retrieved documents rather than parametric memory alone. It requires a [decoder-only autoregressive language model](../nodes/arch-decoder.md) to generate and [embedding and reranking models](../nodes/arch-embedding.md) to find relevant material, and it uses [corpora, vector indexes and rerankers](../nodes/system-index.md) as its source of evidence. Its central point is that retrieval, ranking, authorization, prompt assembly, and generation are separate components — each a distinct place where things can go wrong.

## Trust boundary

RAG injects external, often untrusted, document content directly into the model's context as apparent evidence. Retrieved text can carry instructions, and authorization must be enforced over what any given user is allowed to see. This places it within scope of indirect prompt injection, RAG knowledge-base poisoning, retrieval and ranking manipulation, evidence and citation laundering, and unauthorized retrieved-document disclosure. Authorization-aware retrieval is the control aimed at the access-control side of that boundary.

For the original retrieval-augmented approach, see the cited source.
