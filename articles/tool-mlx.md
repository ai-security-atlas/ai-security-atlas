MLX is an array and machine-learning framework often used in Apple-silicon environments. Within this atlas it is treated as a specialization of [inference engines and serving gateways](../nodes/system-serving.md): a runtime foundation on which models are executed, here tuned to a particular hardware ecosystem.

## Trust boundary

As a serving-layer component, its security-relevant properties are runtime ones — how models are loaded and run, and how shared execution state and resource budgets behave — rather than characteristics of a model's outputs. Where such a runtime serves multiple requests, the general serving concerns of request handling, isolation, and budgeting apply to deployments built on it. Loading model artifacts through the framework is, as with any runtime, a decision to import and execute code and weights whose provenance must be established elsewhere.

For framework details, see the cited documentation.
