Transfer of adversarial prompts applies an attack constructed against one model to a different target, relying on the observation that some adversarial inputs generalize beyond the model they were optimized on. The objective is to [violate intended behavioral constraints](../nodes/goal-behavior.md).

## How it works

The technique depends on [attack transferability](../nodes/concept-transfer.md) and typically starts from a [gradient-guided adversarial suffix](../nodes/attack-gcg.md) optimized on a source model to which the attacker has white-box access. That precomputed input is then presented to a target the attacker cannot directly optimize against. The attacker controls the input; whether it transfers is a property of how the target's behavior relates to the source's. A stated caveat sharpens the threat model: receiving a precomputed suffix is a different capability from having optimized one using only the target's API.

The technique targets [decoder-only language models](../nodes/arch-decoder.md) and belongs to the prompt-and-context-manipulation family. It is distinct from directly optimizing against a target in that transfer trades guaranteed effect for access it does not require.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and the [HarmBench](../nodes/eval-harmbench.md) benchmark. For the construction of transferable suffixes and the conditions under which transfer was observed, defer to the cited source rather than assuming any given target is affected.
