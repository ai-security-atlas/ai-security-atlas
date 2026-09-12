Energy and latency amplification, or sponge inputs, constructs inputs that are unusually expensive to process, inflating compute, energy or response time. The objective is to [degrade availability or increase cost](../nodes/goal-availability.md).

## How it works

The technique exploits how [inference engines and serving gateways](../nodes/system-serving.md) allocate work for a given input. For particular model and execution configurations, certain inputs cause the system to perform far more computation than a typical request, consuming disproportionate resources. The attacker controls the input's structure; the cost is a property of the victim's model and runtime. Because the effect is tied to specific configurations, it does not necessarily transfer across hardware or implementations — a stated caveat that bounds the threat.

The technique applies to [neural networks](../nodes/arch-neural.md) generally and belongs to the availability-and-cost family. It is distinct from length-driven budget exhaustion in that it seeks pathologically expensive processing rather than simply large inputs or outputs, though both aim at availability.

A candidate mitigation, applied conditionally, is enforcing [request, token, tool and cost budgets](../nodes/defense-budget.md) to cap the work any single request can trigger. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and [query, token, latency and compute cost](../nodes/eval-cost.md) measures. For the constructions studied and their configuration dependence, defer to the cited source.
