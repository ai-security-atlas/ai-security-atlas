Unsafe checkpoint deserialization occurs when a model loader executes or interprets malicious content embedded in an artifact during the loading process. The objective is to [compromise the surrounding execution environment](../nodes/goal-environment.md) — code execution on the host that loads the model.

## How it works

The technique targets [model loaders and executable repository code](../nodes/system-loader.md) and formats such as [PyTorch checkpoints and pickle-related loading](../nodes/format-pytorch.md), where the deserialization step can run arbitrary code as a side effect of loading. An attacker who can supply or substitute a checkpoint places malicious content into the artifact; the harm is triggered by the victim's own loading process, not by model inference. The relevant access is therefore the ability to get a crafted artifact loaded — through a compromised registry, a supply-chain substitution, or an untrusted download.

A caveat prevents a common conflation: this is a parser and code-execution risk, [distinct from a trigger-conditioned model backdoor](../nodes/attack-backdoor.md), which is a learned behavior in the weights rather than a loader exploit. The technique belongs to the supply-chain-and-runtime-compromise family.

Candidate mitigations, applied conditionally, include [safer tensor loading and dependency control](../nodes/defense-safe-load.md) — preferring formats that do not execute code — and [sandboxing, egress and execution isolation](../nodes/defense-isolation.md) to contain a loader compromise. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). Defer to the cited loading-security documentation for detail.
