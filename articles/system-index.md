This component holds the searchable substrate behind retrieval: document corpora, the vector indexes built from them, and the rerankers that reorder candidate results. It requires [embedding and reranking models](../nodes/arch-embedding.md) to turn text into vectors and to score relevance, and it is used by [retrieval-augmented generation](../nodes/system-rag.md) to assemble evidence for the model.

## Trust boundary

Chunking, embedding, and ranking choices decide which external content actually reaches the model, so this layer governs what the system treats as authoritative. Whoever can add documents to a corpus, or shape how they rank, has partial control over the model's inputs. That places it within scope of RAG knowledge-base poisoning, where planted content is engineered to be retrieved, and retrieval and ranking manipulation, where the ordering itself is gamed to surface attacker-favored material.

For retrieval architecture and corpus-corruption studies, see the cited sources.
