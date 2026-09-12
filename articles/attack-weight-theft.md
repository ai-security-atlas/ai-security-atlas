Unauthorized checkpoint or adapter theft acquires the exact model artifacts — full weights or fine-tuned adapters — through compromise of the systems that hold or distribute them. The objective is to [appropriate model artifacts or capabilities](../nodes/goal-model-theft.md).

## How it works

Unlike behavioral extraction, this technique aims at the artifacts themselves, obtaining a bit-for-bit copy of the [weights, parameters and activations](../nodes/concept-parameters.md). It works against [model registries and distribution](../nodes/system-registry.md) and the surrounding infrastructure, through storage compromise, account takeover, or a supply-chain breach. The relevant capability is unauthorized access to where artifacts are stored or moved — the model's behavior at inference plays no part. The attacker gains access; the exposure is a property of how the registry and storage are secured.

A caveat draws the boundary between theft and legitimate use: ordinary download of intentionally public weights is not theft. The distinction turns on authorization, not on possession. The technique is [distinct from black-box functional model extraction](../nodes/attack-model-imitation.md), which reconstructs behavior through queries rather than stealing the exact artifact; both belong to the model-artifact-theft family.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and [extraction fidelity versus artifact equality](../nodes/eval-fidelity.md), which distinguishes an exact copy from an approximation. For the threat framing and control expectations, defer to the cited ATLAS and OWASP sources.
