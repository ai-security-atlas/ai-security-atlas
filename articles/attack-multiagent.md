Inter-agent trust and message manipulation targets workflows in which several agents collaborate, delegating subtasks and passing results between one another. The objective is to steer that collaboration so it produces [unauthorized actions or privilege use](../nodes/goal-actions.md) or, when the influence persists across turns, to [establish lasting attacker influence](../nodes/goal-persistence.md).

## How it works

The technique exploits an implicit assumption in [multi-agent orchestration](../nodes/system-multiagent.md): that a message from a peer agent, or a result returned by one, can be treated as trustworthy instruction or verified fact. An attacker who can shape the content one agent emits — or the intermediate data another consumes — may have that content re-interpreted downstream as a directive rather than as data. The relevant boundary is between an agent's own authorized reasoning and the lower-trust text arriving from other participants; conflating the two is what makes redirection possible.

Exposure depends on how the framework assembles, attributes and authorizes inter-agent messages, and on which agents hold sensitive capabilities. This is a composed threat scenario rather than a demonstrated exploit against any specific framework, so preconditions matter.

Evaluation is typically framed through an explicit [threat model](../nodes/eval-threat-model.md), agentic benchmarks such as [AgentDojo](../nodes/eval-agentdojo.md), and [attack success and severity](../nodes/eval-asr.md) measures. Consult the cited orchestration and agentic-risk sources for concrete framing; treat published architecture papers as background, not proof of vulnerability.
