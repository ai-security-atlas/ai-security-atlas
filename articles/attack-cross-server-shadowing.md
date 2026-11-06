Cross-server tool shadowing and namespace collision occurs when an untrusted or compromised tool server connected to a multi-server [Model Context Protocol (MCP) bus](../nodes/system-mcp.md) uses its tool metadata or naming to intercept, redirect, or alter how the agent invokes tools belonging to *another*, trusted server in the same session. The objective is to cause [unauthorized actions or privilege use](../nodes/goal-actions.md) or to [obtain protected information](../nodes/goal-information.md).

## How it works

When a [tool-using agent](../nodes/system-agent.md) loads [tools and connectors](../nodes/system-tools.md) from multiple servers simultaneously, all tool names, parameter schemas, and descriptions are merged into a shared prompt context. Extending [tool-description poisoning](../nodes/attack-tool-description.md) across server boundaries, a malicious server can inject instructions inside its own tool docstring that govern how the model calls a sibling server's tool (for example, instructing the model to always copy sensitive parameters or email bodies into a secondary call, or to route messages to an attacker-chosen recipient), or register a colliding tool name that shadows the trusted implementation.

Crucially, the trusted server itself is never compromised; the attack exploits the flat context window in which the model reasons over all connected servers at once.

Mitigations include [least-privilege tools and scoped credentials](../nodes/defense-least-privilege.md), strict per-server namespace isolation, and out-of-model policy checks before cross-domain tool invocations. Evaluation is tracked through [AgentDojo](../nodes/eval-agentdojo.md) and [attack success and severity](../nodes/eval-asr.md).
