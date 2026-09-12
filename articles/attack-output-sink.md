Improper handling of model-generated output describes a class of vulnerability in which a downstream application treats a model's response as executable or privileged input without appropriate validation. It corresponds to the OWASP LLM Top 10 category for improper output handling. The objective is to cause [unauthorized actions or privilege use](../nodes/goal-actions.md) or to [compromise the surrounding execution environment](../nodes/goal-environment.md).

## How it works

The weakness lives in the application, not the model. When generated text flows into a sink that interprets it — a shell, a query engine, a rendering context, or a tool invocation — a missing or inadequate check at that [trust boundary](../nodes/concept-boundaries.md) lets the output act with the sink's authority. Notably, the model need not be jailbroken or specially trained: ordinary output, or output shaped by upstream injection, can carry the effect if the sink trusts it implicitly. The distinction between attacker-influenced generation and victim-controlled validation is where the risk concentrates.

Exposure is highest in [tool-using agents](../nodes/system-agent.md), where model output routinely drives real capabilities.

Candidate mitigations, applied conditionally, include [context-specific output validation](../nodes/defense-output.md) at each sink and [sandboxing, egress and execution isolation](../nodes/defense-isolation.md) to contain consequences. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), the [AgentDojo](../nodes/eval-agentdojo.md) benchmark, and [attack success and severity](../nodes/eval-asr.md). Consult the cited OWASP source for the category's scope.
