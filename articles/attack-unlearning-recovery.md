Recovery of unlearned concepts or capabilities extracts knowledge, styles, or hazardous behaviors that were ostensibly removed from a model through approximate [concept erasure and machine unlearning](../nodes/adapt-unlearning.md). The objective is to [violate intended behavioral constraints](../nodes/goal-behavior.md) or [obtain protected information](../nodes/goal-information.md) that the operator intended to suppress.

## How it works

Approximate unlearning methods modify [weights, parameters and activations](../nodes/concept-parameters.md) in [decoder-only language models](../nodes/arch-decoder.md) or [diffusion models](../nodes/arch-diffusion.md) without retraining from scratch. As demonstrated in *Unlearning or Obfuscating? Jogging the Memory of Unlearned LLMs via Benign Relearning* and *An Adversarial Perspective on Machine Unlearning for AI Safety*, many unlearning updates suppress surface decoding pathways or shift activations rather than erasing the underlying distributed representations. An adversary with query, activation, or fine-tuning access can recover the suppressed behavior through benign few-shot relearning on loosely related data, activation steering, adversarial prefix search, or even post-training quantization.

This places the technique in the [internal representation and weight manipulation](../nodes/family-representation.md) family and highlights a critical distinction: failing a surface prompt test after unlearning is not evidence that the information has been deleted from the parameters.

Evaluation requires adaptive stress-testing under [attack success and severity](../nodes/eval-asr.md) across weight perturbations, relearning budgets, and representation probes rather than single-turn prompt checks alone.
