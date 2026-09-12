Tool-description poisoning influences an agent's tool selection or actions through attacker-controlled tool metadata — the names, descriptions and parameter text a model reads when deciding how to act. The objective is to cause [unauthorized actions or privilege use](../nodes/goal-actions.md) or to [obtain protected information](../nodes/goal-information.md).

## How it works

Agents that use [tools, plugins, MCP and connectors](../nodes/system-tools.md) rely on descriptive metadata to understand what each tool does. This technique is a [variant of indirect prompt injection](../nodes/attack-indirect-injection.md): instructions are embedded in that metadata, so when the model reads a tool's description it may treat the embedded content as guidance rather than as inert documentation. The attacker controls the descriptor; the agent controls whether descriptor text is granted instruction-level trust. The manipulation happens at the point where the model interprets available tools, before or during selection.

A caveat frames exposure: it depends on client trust behavior and on which descriptors are available to the model. A client that isolates or sanitizes metadata presents a smaller surface. The technique belongs to the agent-authority-and-workflow family, closely related to tool-output injection but acting on descriptions rather than returned results.

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), the [AgentDojo](../nodes/eval-agentdojo.md) benchmark, and [attack success and severity](../nodes/eval-asr.md). For the tool-poisoning framing in connector protocols, defer to the cited source.
