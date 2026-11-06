Server-to-client sampling and prompt-template injection abuses the reverse direction of bidirectional agent protocols — such as `sampling/createMessage` or server-hosted prompt templates in the [Model Context Protocol (MCP)](../nodes/system-mcp.md) — where a connected tool server requests completions or injects prompt structures back into the host client. The objective is to cause [unauthorized actions or privilege use](../nodes/goal-actions.md), [violate intended behavioral constraints](../nodes/goal-behavior.md), or [obtain protected information](../nodes/goal-information.md).

## How it works

Unlike one-way function calling where the [agent](../nodes/system-agent.md) strictly initiates tool execution, bidirectional tool protocols allow a server to ask the host client to run an LLM completion on its behalf or to supply reusable prompt templates. If [trust boundaries and authorization](../nodes/concept-boundaries.md) on the client do not isolate server-initiated sampling requests from the user's active conversation, credentials, or billing quota, a malicious or compromised server can silently steer host completions, extract conversation context, or plant hidden system instructions via server-supplied templates.

Exposure depends on client implementation choices: specifications such as the *MCP Authorization Security Considerations* recommend that hosts require explicit user confirmation and scope visibility before fulfilling server sampling calls.

Controls include [human approval for high-impact actions](../nodes/defense-approval.md), [separating data from authority](../nodes/defense-boundaries.md) on server-provided templates, and per-server [rate and token budgets](../nodes/defense-budget.md).
