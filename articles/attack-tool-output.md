Tool-output injection returns lower-trust instructions inside a tool's response in order to redirect the agent that consumes it. The objective is to cause [unauthorized actions or privilege use](../nodes/goal-actions.md) or to [obtain protected information](../nodes/goal-information.md).

## How it works

This technique is a [variant of indirect prompt injection](../nodes/attack-indirect-injection.md) that acts through [tools, plugins, MCP and connectors](../nodes/system-tools.md). When an agent calls a tool, it typically feeds the returned content back into its context to decide what to do next. If that response contains embedded directives, the agent may follow them as if they were authorized instructions. The attacker controls the content of the tool response; the agent controls whether returned data is treated as instruction. A stated caveat captures the core error: successful tool execution is not the same as authority for whatever the response says to do.

Because a redirected agent can be steered toward retrieving material it should not, this technique can [enable unauthorized retrieved-document disclosure](../nodes/attack-rag-disclosure.md). It belongs to the agent-authority-and-workflow family, paired with description poisoning, which acts on tool metadata rather than results.

Candidate mitigations, applied conditionally, include [least-privilege tools and scoped credentials](../nodes/defense-least-privilege.md) and [auditable action and content lineage](../nodes/defense-logging.md). Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), the [AgentDojo](../nodes/eval-agentdojo.md) benchmark, and [attack success and severity](../nodes/eval-asr.md). Defer to the cited indirect-injection and tool-poisoning sources.
