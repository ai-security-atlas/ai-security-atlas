Iterative projected adversarial optimization is a method for searching within a bounded perturbation region for an input that changes a model's decision. It is primarily a robustness-evaluation tool, routing to the objectives of [evading security controls](../nodes/goal-evasion.md) and [manipulating outputs, predictions or decisions](../nodes/goal-decisions.md).

## How it works

The technique builds on single-step [gradient-based adversarial perturbations](../nodes/attack-fgsm.md), repeating the perturbation over many small steps and, after each, projecting back onto the allowed region so the change stays within a defined budget. Iterating in this way tends to find stronger adversarial inputs than a single step, which is why it is used to probe [neural networks](../nodes/arch-neural.md) for weaknesses that weaker attacks miss. The attacker controls the perturbation within the constraint set; the victim owns the model and its decision boundary.

Because it is a strong evaluation attack, it is a [prerequisite for adversarial training and robustness evaluation](../nodes/defense-robust-train.md) — the same procedure that also serves as its candidate mitigation. A central caveat is methodological: a weak configuration or gradient masking can make a model look robust when it is not, so results must be interpreted with care.

Evaluation is framed through [adaptive defense evaluation](../nodes/eval-adaptive.md), an explicit [threat model](../nodes/eval-threat-model.md), and [attack success and severity](../nodes/eval-asr.md). For the original formulation and its guarantees, defer to the cited source.
