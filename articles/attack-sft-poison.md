Instruction-tuning data poisoning corrupts the demonstrations or labels used during supervised adaptation, so that the resulting model carries attacker-influenced behavior. The objective is to [establish persistent attacker influence](../nodes/goal-persistence.md) and to [violate intended behavioral constraints](../nodes/goal-behavior.md).

## How it works

[Supervised fine-tuning](../nodes/life-sft.md) teaches a model from curated input-output examples. If an attacker can contribute or alter some of those examples — injecting mislabeled or trigger-bearing demonstrations — the model may learn the embedded behavior alongside the intended task. The attacker supplies tainted data; the training operator controls curation, mixture and the fine-tuning run, so effect depends on how much poisoned material reaches training and survives filtering. Crucially, a data-contribution threat is narrower than complete control of the fine-tuning job.

The technique targets [decoder-only language models](../nodes/arch-decoder.md) and belongs to the poisoning, backdoors and persistence family. Its persistence into the adapted weights distinguishes it from inference-time manipulation, while its focus on demonstrations distinguishes it from poisoning aimed at pretraining or at the reward channel.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For concrete poisoning constructions — including trigger-conditioned behaviors and the conditions under which fine-tuning affected safety — defer to the cited backdoor and fine-tuning sources rather than assuming any particular pipeline is affected.
