Token, context and inference-budget exhaustion drives a system to perform excessive permitted work through long inputs or outputs, or through uncontrolled request behavior. It maps to the OWASP LLM Top 10 unbounded-consumption category. The objective is to [degrade availability or increase cost](../nodes/goal-availability.md).

## How it works

The technique exploits the resource cost of processing large [context windows](../nodes/concept-context.md) and generating long responses on [inference engines and serving gateways](../nodes/system-serving.md). By supplying maximal-length inputs, eliciting long generations, or issuing requests without restraint, an attacker can consume a disproportionate share of compute, tokens or throughput. The attacker controls request size and rate; the victim controls the limits, quotas and scheduling that decide how much work is actually permitted. Impact is therefore contingent on what bounds the operator has in place.

A caveat sharpens the framing: bounded but expensive individual requests should be separated from sustained denial of service and from per-tenant quota failures — they represent different severities. The technique belongs to the availability-and-cost family and complements sponge inputs, which pursue pathological cost rather than sheer length.

A candidate mitigation, applied conditionally, is enforcing [request, token, tool and cost budgets](../nodes/defense-budget.md). Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and [query, token, latency and compute cost](../nodes/eval-cost.md) measures. Defer to the cited OWASP source for scope.
