Adversarial fine-tuning to alter constraints uses training control over a model to modify its refusal behavior or other intended properties. The objective is to [violate intended behavioral constraints](../nodes/goal-behavior.md) — producing a variant that behaves outside its original safety envelope.

## How it works

The technique relies on [full-parameter fine-tuning](../nodes/adapt-full.md) applied during [supervised fine-tuning](../nodes/life-sft.md). With the ability to run a training job on the model, an actor can present data that shifts learned behavior, weakening constraints that alignment had established. The actor controls the fine-tuning data and procedure; the resulting behavior change is a property of the adapted weights. This presupposes sufficient access to train the model, whether locally on open weights or through a fine-tuning interface.

An important caveat concerns intent and labeling: benign fine-tuning can also cause safety regressions unintentionally. Malicious alteration and accidental regression produce similar symptoms but are distinct labels, and distinguishing them matters for attribution. The technique targets [decoder-only language models](../nodes/arch-decoder.md) and sits within the training-and-adaptation abuse family.

A candidate mitigation, applied conditionally, is [safety and utility regression testing](../nodes/defense-regression.md) to detect behavioral drift after adaptation. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For the studied conditions under which fine-tuning affected safety, defer to the cited source.
