A complete model package reflects a simple point: weights alone are usually insufficient to reproduce a model's behavior. A working model typically also needs its tokenizer, configuration, prompt or chat templates, a specific revision, and any auxiliary modules — each of which can affect what the model actually does.

Assembling such a package draws on [tokenization and vocabulary](../nodes/concept-tokens.md), since the tokenizer and vocabulary determine how text maps to and from the model, and often on [checkpoint conversion and sharding](../nodes/transform-conversion.md) to produce the weight files themselves.

## Security scope

Because behavior depends on more than the weight tensors, the package as a whole is the unit that matters for integrity. That breadth is relevant to [artifact, adapter or configuration substitution](../nodes/attack-artifact-substitution.md): substituting a tokenizer, config, template, or auxiliary module — not only the weights — could change behavior. This describes the scope of what must be verified, not a claim that any particular package has been tampered with.

Distinguishing the container from what it contains, and the weights from the surrounding configuration, is the practical takeaway. For component-level details of specific packaging formats, defer to the cited format documentation.
