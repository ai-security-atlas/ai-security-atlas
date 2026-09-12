Cross-session or cross-tenant disclosure exposes one principal's data to another through failures in state handling, context assembly, caching or access control. It falls under the OWASP LLM Top 10 sensitive-information-disclosure category, and its objective is to [obtain protected information](../nodes/goal-information.md).

## How it works

Serving systems reuse computation and state for efficiency, including [KV caches and prefix reuse](../nodes/concept-kv-cache.md). When [trust boundaries and authorization](../nodes/concept-boundaries.md) between sessions or tenants are not enforced end to end, one user's content or derived state can surface to another — for example, through shared cache entries, context assembled from the wrong source, or a missing tenancy check. The attacker interacts through an ordinary session; the leakage comes from how the serving layer isolates state that it, not the attacker, controls.

A caveat is essential to interpretation: actual content leakage must be separated from a timing signal that merely suggests prior use. Observing that a cached prefix responds faster is not the same as recovering another principal's data. The technique applies to [inference engines and serving gateways](../nodes/system-serving.md) and [tool-using agents](../nodes/system-agent.md).

Candidate mitigations, applied conditionally, include [cache and session isolation](../nodes/defense-cache-isolation.md) and [authorization-aware retrieval](../nodes/defense-rag-acl.md). Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and [privacy verification and baselines](../nodes/eval-privacy.md). Defer to the cited OWASP and cache-auditing sources.
