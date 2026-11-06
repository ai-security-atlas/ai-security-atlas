PyTorch checkpoints are a common way to store model state, but a checkpoint's file extension does not, by itself, fully describe how it will be loaded — or whether loading it carries executable deserialization risk. A similar-looking file can be handled by different loading paths with different behavior.

Creating these checkpoints commonly involves [checkpoint conversion and sharding](../nodes/transform-conversion.md) to write out the weight files.

## Artifact versus loading

The key distinction is between the artifact and the act of loading it. Default PyTorch checkpoint archives (`torch.save` / `torch.load` with `weights_only=False`) serialize Python objects using `pickle`, whose virtual machine opcodes (`GLOBAL`, `STACK_GLOBAL`, `REDUCE`) invoke arbitrary callables via `__reduce__` during deserialization. This is what makes PyTorch checkpoints a prerequisite context for [unsafe checkpoint deserialization](../nodes/attack-unsafe-load.md) and motivates [safe deserialization and non-executable model formats](../nodes/defense-safe-load.md) such as `weights_only=True` or [Safetensors](../nodes/format-safetensors.md). Naming the scope here is not a claim that any particular file is malicious — only that loading behavior, not appearance, is what matters.

Because of this, the integrity and provenance of checkpoints, and awareness of which loading path is used, are the practical concerns. For the precise loading semantics and the associated security warning, defer to the cited loading documentation.
