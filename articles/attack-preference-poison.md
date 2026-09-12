Preference or reward-signal manipulation targets the comparisons, reward models and human-feedback signals used during post-training. The objective is to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md) or to [violate intended behavioral constraints](../nodes/goal-behavior.md) by shaping what the alignment process learns to reward.

## How it works

Alignment pipelines depend on [preference data and reward models](../nodes/life-preferences.md): pairs or rankings of candidate responses that teach a model which behaviors are favored. If an attacker can influence those comparisons — by contributing biased preferences, corrupting a reward model, or steering feedback — the learned reward signal can be nudged toward attacker-preferred behavior. The attacker controls contributed feedback; the victim controls collection, filtering and the training procedure, so influence is contingent on how much of the signal an attacker can reach and how it is weighted.

This is a coverage node grounded in threat modeling for [decoder-only language models](../nodes/arch-decoder.md); it is not a claim that any specific preference-optimization method is inherently vulnerable. It sits within the training-and-adaptation abuse family, distinct from poisoning that targets pretraining or supervised demonstrations because it acts on the reward channel itself.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For the underlying feedback and preference-optimization methods, and for taxonomy framing, defer to the cited sources rather than assuming present-day exploitability.
