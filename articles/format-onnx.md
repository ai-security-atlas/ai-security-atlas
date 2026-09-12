ONNX is an interchange representation for models: rather than storing only parameters, it describes a model as a computational graph of operators together with their parameters. That makes it a portable way to move a model between frameworks and runtimes that understand the same operator definitions.

Producing an ONNX artifact usually involves [checkpoint conversion and sharding](../nodes/transform-conversion.md), exporting a model from its original framework into the ONNX graph representation.

## What ONNX is, and is not

Because it encodes a graph of operators, an ONNX file describes computation to be performed by a conforming runtime; it is not itself a raw, data-only tensor dump, nor is it a runtime-specific compiled engine. How that graph is executed — and any associated handling considerations — depends on the runtime that loads it.

The security-relevant scope follows from the same fact: an ONNX file's provenance and the operators it references matter to whatever runtime interprets it. This is a statement about what to verify, not a claim about any specific vulnerability. For the authoritative description of the format and its operators, defer to the cited ONNX documentation.
