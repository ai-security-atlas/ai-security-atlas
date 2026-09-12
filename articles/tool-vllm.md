vLLM is a serving runtime, a concrete specialization of [inference engines and serving gateways](../nodes/system-serving.md). Its summary highlights that its scheduling and caching behavior is version-dependent — how it batches requests and reuses cached computation can differ between releases.

## Trust boundary

As a serving component, vLLM concentrates the runtime properties that matter across tenants. Batching and caching, including prefix caching that reuses computation across requests, create shared state and shared capacity between users. Because that state and budget span requests, deployments built on it fall within the same scope as the serving layer generally: cross-session or cross-tenant disclosure, prompt-cache timing inference, and inference-budget exhaustion are relevant concerns wherever such sharing occurs. That the exact behavior is version-dependent means claims should be tied to a specific release rather than assumed.

For how prefix caching reuses computation, see the cited source.
