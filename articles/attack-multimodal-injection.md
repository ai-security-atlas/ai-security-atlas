Instructions carried through multimodal content extend prompt injection beyond plain text: visible text within an image, or media a model interprets, can be absorbed as instructions inside a multimodal workflow. The objective is to cause [unauthorized actions](../nodes/goal-actions.md) or to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md).

## How it works

The technique relies on a failure of [trust boundaries and authorization](../nodes/concept-boundaries.md) in systems built on [vision-language models](../nodes/arch-vlm.md). Content that should be treated as lower-trust data — for example, text rendered inside a picture, or a document surfaced by a browser or computer-use integration — can instead be read by the model as an authoritative directive. The attacker controls the content of the media; the victim system controls whether that content is granted instruction-level trust. The gap between those two is the mechanism.

This is a scope-level extension of prompt injection into additional modalities. It is conceptually distinct from an optimized [visual adversarial perturbation](../nodes/attack-visual-jailbreak.md), which manipulates model behavior through imperceptible pixel changes rather than through readable content.

Exposure depends on where multimodal inputs enter — [browser and computer-use integrations](../nodes/system-browser.md) are a common surface — and on how those inputs are attributed and authorized.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For empirical framing, defer to the cited indirect-injection and visual-instruction sources rather than assuming any specific system behaves this way today.
