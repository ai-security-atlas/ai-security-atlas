Tools, plugins, MCP servers, and connectors give a [tool-using agent](../nodes/system-agent.md) its concrete capabilities: reading data, calling APIs, or changing state. Each requires the agent that invokes it and a scheme of [trust boundaries and authorization](../nodes/concept-boundaries.md) to decide what any given tool may do. The component treats a tool's description, its arguments, its outputs, its identity, and its authorization as distinct surfaces rather than one opaque thing.

## Trust boundary

Every one of those surfaces can be attacker-influenced. A description is read by the model and can steer it; arguments and outputs cross between the agent and external systems; identity and authorization decide whose privileges an action carries. This scope makes it relevant to tool-description poisoning, tool-output injection, tool definition or behavior changes after approval, confused-deputy abuse, and malicious dependencies or repository code. Least-privilege tools and scoped credentials is the control that narrows what any tool can reach.

For the authorization model and the tool-poisoning risk, see the cited sources.
