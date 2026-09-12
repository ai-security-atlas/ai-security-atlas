Multi-agent orchestration coordinates several [tool-using agents](../nodes/system-agent.md) that exchange messages and hand off tasks, so that work — and the authority to act — flows between them. It exists to decompose problems across specialized agents.

## Trust boundary

Messages and delegated authority now cross multiple component boundaries rather than staying inside one loop. An agent typically treats a peer's message as trusted context, yet that message may itself derive from untrusted content the peer observed. Delegation also compounds: authority passed down a chain can be exercised further than any single step intended. This places the component within scope of inter-agent trust and message manipulation, where a message from one agent misleads another, and tool-loop and recursive-delegation exhaustion, where delegation cycles consume resources without terminating.

For a framework enabling multi-agent conversation, see the cited source.
