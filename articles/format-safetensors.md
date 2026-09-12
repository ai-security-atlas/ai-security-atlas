Safetensors is a serialization format for tensors designed around a safer loading path: it focuses on storing tensor data in a way that avoids the general object-reconstruction behavior associated with some other checkpoint loading mechanisms.

Producing a safetensors file typically follows [checkpoint conversion and sharding](../nodes/transform-conversion.md), writing existing weights into the safetensors layout.

## Two clarifications

First, "safer loading" concerns how the file is read back, not what the model learned: the format does not establish that a model's learned behavior is benign. A file can be loaded without executing arbitrary code and still contain weights that behave in undesired ways. Second, safetensors is a data container for tensors, not a compiled, executable engine — the format stores parameters; it does not itself define computation.

In scope terms, the format's design addresses a class of loading-time concerns; it does not address the behavioral, supply-chain, or configuration questions that live outside the tensor file. Those remain matters for verifying the surrounding package and its provenance. For the authoritative description of the format and its guarantees, defer to the cited documentation.
