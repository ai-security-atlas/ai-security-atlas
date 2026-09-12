Optimized visual jailbreaks use adversarial perturbations in an image to affect a vision-language model's safety behavior. The objective is to [violate intended behavioral constraints](../nodes/goal-behavior.md), eliciting responses the model's safeguards would otherwise suppress.

## How it works

The technique combines [gradient-based adversarial perturbations](../nodes/attack-fgsm.md) with the multimodal input surface of a [vision-language model](../nodes/arch-vlm.md). Rather than relying on readable text, it optimizes pixel-level changes — often imperceptible — that shift the model's internal processing toward compliant behavior. The attacker controls the crafted image; the safety behavior being bypassed is a property of the victim model. As an optimization-based attack, it presupposes enough access to compute effective perturbations against the target or a suitable surrogate.

A caveat marks an important boundary: this is distinct from simply placing readable instructions inside an image, which is a form of multimodal instruction injection rather than an adversarial perturbation. As a [variant of jailbreaking and refusal bypass](../nodes/attack-jailbreak.md), it pursues the same goal through the visual channel; it belongs to the adversarial input-evasion family.

Evaluation is framed through [adaptive defense evaluation](../nodes/eval-adaptive.md), an explicit [threat model](../nodes/eval-threat-model.md), and [attack success and severity](../nodes/eval-asr.md). For the perturbation constructions and the conditions under which they affected aligned models, defer to the cited source rather than assuming present-day applicability to any specific model.
