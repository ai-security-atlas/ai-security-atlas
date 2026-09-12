Tool definition or behavior changes after approval — sometimes called a rug pull — alters a tool once it has already earned user or client trust. The objective is to cause [unauthorized actions or privilege use](../nodes/goal-actions.md) or to [establish persistent attacker influence](../nodes/goal-persistence.md).

## How it works

Agents draw on [tools, plugins, MCP and connectors](../nodes/system-tools.md) that a user or client typically reviews and approves before use. This technique exploits the gap between approval and later invocation: a tool that behaved acceptably at review time is changed afterward, so subsequent calls run under trust that was granted to a different definition. The attacker controls the tool's later state; the client controls how tightly approval is bound to a specific version. Exposure depends on whether trust is pinned to an immutable definition or re-extended implicitly on each use.

A caveat frames interpretation: version and approval-binding assumptions must be recorded, and a metadata change alone does not prove exploitation — it establishes the precondition. The technique belongs to the agent-authority-and-workflow family, distinct from description poisoning in that the trusted artifact itself mutates over time rather than carrying hidden instructions from the start.

A candidate mitigation, applied conditionally, is [risk-based human approval](../nodes/defense-approval.md) that re-checks consequential actions. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), the [AgentDojo](../nodes/eval-agentdojo.md) benchmark, and [attack success and severity](../nodes/eval-asr.md). Defer to the cited source for the connector-protocol framing.
