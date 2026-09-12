Adversarial activation steering influences a model's behavior at runtime by intervening on its internal activations, without changing the stored weights. The objective is to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md) or to [violate intended behavioral constraints](../nodes/goal-behavior.md).

## How it works

The technique uses [activation steering](../nodes/adapt-steering.md): adding or adjusting vectors in a model's intermediate representations to push behavior in a chosen direction as the model runs. Because it operates on activations rather than parameters, the model's weights are left intact and the effect is applied per inference. The actor controls the intervention surface and the steering vectors; the model provides the representations being nudged. This presupposes access to that internal surface and the measurement needed to identify an effective direction.

A caveat frames both scope and neutrality: the technique requires the identified intervention point and its evaluation, and activation steering is a legitimate interpretability and control method — it is not inherently malicious. Whether it constitutes an attack depends on intent and context. The technique targets [transformers](../nodes/arch-transformer.md) and belongs to the representation-and-weight-interventions family, distinct from refusal-direction editing in that it acts transiently rather than through a persistent weight change.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For the steering methods and the representational findings they build on, defer to the cited activation-engineering and refusal-direction sources.
