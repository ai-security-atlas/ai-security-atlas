Persistent agent memory lets a [tool-using agent](../nodes/system-agent.md) carry information across sessions — stored summaries, user preferences, or standing instructions that are recalled and injected into later context. It exists to give agents continuity beyond a single conversation.

## Trust boundary

Memory turns past input into future instructions. Content written once — whether by a user, a tool, or attacker-influenced material — can resurface turns or days later and shape the model's behavior when the original context is gone, which makes provenance hard to reconstruct at the moment of recall. The component is relevant to persistent agent-memory poisoning, where planted or manipulated entries steer later sessions, and it is the surface that memory provenance, review and expiry controls are designed to govern — tracking where a memory came from, allowing review, and bounding how long it persists.

For a treatment of memory as an attack surface, see the cited source.
