Partial parameter recovery from API behavior attempts to reconstruct a specific component of a model — such as a projection layer or its dimensions — using only observable query responses. The objective is to [appropriate model artifacts or capabilities](../nodes/goal-model-theft.md), recovering a piece of a model that was never intended to be exposed.

## How it works

The technique leans on the relationship between a model's [input and output embeddings](../nodes/concept-embeddings.md) and the [logits, probabilities and observable outputs](../nodes/concept-logits.md) returned by an API. Under specific assumptions about which query capabilities and score information the interface exposes, structured queries can reveal enough about the output-projection geometry to recover part of it. The attacker controls queries and observes responses; the provider controls what the API discloses, so the attack's feasibility is bounded by that surface.

A central caveat is scope: partial projection recovery is not complete recovery of a production model's weights. It targets [decoder-only language models](../nodes/arch-decoder.md) and sits within the model-artifact-theft family, distinct from full-weight theft or black-box functional imitation.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and [extraction fidelity versus artifact equality](../nodes/eval-fidelity.md). A cited 2024 study reported partial projection-layer recovery under specific API capabilities on the models it evaluated; this is a historical result, not a statement about the vulnerability of current APIs or about complete model-weight recovery. Defer to that source for exact conditions.
