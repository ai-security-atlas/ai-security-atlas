Inference engines and serving gateways run models at scale, deciding how requests are batched, cached, isolated, and scheduled. Part of [deployment, monitoring and updates](../nodes/life-deploy.md), this component determines runtime behavior that a model's weights alone do not — and it is the foundation that runtimes such as [vLLM](../nodes/tool-vllm.md), [llama.cpp](../nodes/tool-llamacpp.md), [MLX](../nodes/tool-mlx.md), [TensorRT-adjacent serving](../nodes/tool-tensorrt.md), and [Hugging Face Transformers](../nodes/tool-transformers.md) build on.

## Trust boundary

Serving mixes many users' requests over shared resources. Batching, key-value caches, and prefix caching create state that can span requests, and scheduling decisions consume finite capacity. Because that shared state and shared budget sit between tenants, the component is relevant to cross-session or cross-tenant disclosure, prompt-cache timing inference, energy and latency amplification via sponge inputs, and token, context and inference-budget exhaustion. Request, token, tool and cost budgets attach here as a control.

For how prefix caching reuses computation across requests, see the cited source.
