An agent is a control loop that lets a language model act, not just answer. It requires a [decoder-only autoregressive language model](../nodes/arch-decoder.md) to propose steps and a scheme of [trust boundaries and authorization](../nodes/concept-boundaries.md) to decide which of those steps may run. On each turn the loop combines model decisions, calls to [tools, plugins, MCP and connectors](../nodes/system-tools.md), the observations returned, and whatever policy enforcement the operator inserts, feeding results back into the next decision.

## Trust boundary

Because the model's next action is shaped by content it observes — tool outputs, retrieved documents, prior messages — the agent erodes the usual separation between instructions and data. Any observation can, in principle, steer the loop. That scope makes it relevant to direct and indirect prompt injection, tool-description and tool-output injection, confused-deputy abuse, exploitation of excessive delegated agency, persistent memory poisoning, and tool-loop or recursive-delegation exhaustion, among others. It also underpins components built on top of it: persistent memory, multi-agent orchestration, browser and computer use, and human-approval or lineage controls.

Empirical patterns for reasoning-and-acting loops are covered in the cited source.
