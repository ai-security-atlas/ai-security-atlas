Physical-world adversarial examples study whether an adversarial input still fools a model after it passes through real-world transformations — printing, photographing, changes in lighting, angle or distance. The objective is to [evade security controls](../nodes/goal-evasion.md) or to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md), for instance in perception systems built on [convolutional networks](../nodes/arch-cnn.md).

## How it works

The starting point is a digital adversarial perturbation produced with [gradient-based methods](../nodes/attack-fgsm.md). Moving that perturbation into the physical world introduces distortions the attacker does not fully control: a printed pattern is re-sampled by a camera, colors shift, and geometry warps. The technique therefore treats these transformations as part of the threat model, seeking perturbations that survive them rather than assuming digital success carries over. A key caveat follows directly — success against a stored image does not imply success once the same perturbation is printed and re-captured.

Conceptually, exposure depends on the capture pipeline and the physical conditions an attacker can influence, which vary widely across deployments. The technique is a member of the adversarial input-evasion family and shares its optimization roots with digital-only variants while adding a robustness-to-transformation requirement.

Evaluation is framed through [adaptive defense evaluation](../nodes/eval-adaptive.md), an explicit [threat model](../nodes/eval-threat-model.md), and [attack success and severity](../nodes/eval-asr.md). For the experimental conditions under which physical transfer was studied, defer to the cited source.
