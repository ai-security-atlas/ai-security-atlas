GGUF is a binary packaging format that stores tensors together with metadata, and can hold different numerical types and describe supported model architectures within a single file. It is the distribution format consumed by [llama.cpp](../nodes/tool-llamacpp.md), which reads GGUF files to load and run a model.

Producing a GGUF file generally follows [checkpoint conversion and sharding](../nodes/transform-conversion.md): an existing checkpoint is converted into the GGUF layout.

## Format versus precision

A file format is not the same thing as a numerical precision. GGUF is distinct from [quantization and numerical precision](../nodes/transform-quantization.md): the format is the container and its metadata, whereas quantization is a choice about how numbers are represented. A single format can carry tensors at many precisions, so the extension alone does not tell you how the weights were quantized.

As a data-oriented container, GGUF stores parameters and descriptive metadata rather than executable code. Its security relevance is therefore mainly a matter of supply chain and integrity — what the file actually contains and where it came from — rather than any inherent execution behavior. For the authoritative layout and field definitions, defer to the cited format specification.
