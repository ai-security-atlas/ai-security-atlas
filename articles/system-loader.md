Model loaders parse checkpoints and import the repository code that accompanies a model so it can run. This component belongs to the operational stage governed by [deployment, monitoring and updates](../nodes/life-deploy.md), and it exists to make explicit a point often glossed over: loading an artifact is a distinct host-execution trust decision, separate from trusting the model's outputs.

## Trust boundary

Parsing a checkpoint or importing accompanying code can execute logic on the host before any inference happens. An artifact obtained from a registry or repository is untrusted until proven otherwise, so this is where supply-chain trust is actually granted. The component is relevant to unsafe checkpoint deserialization, malicious dependencies or repository code, malicious adapters or adapter substitution, and behavioral tampering through merges or conversion. Corresponding controls — safer tensor loading and dependency control, and execution isolation — attach at this boundary, as do [compiled inference engines](../nodes/format-engine.md) that consume loaded artifacts.

For the deserialization risk in a common loading path, see the cited source.
