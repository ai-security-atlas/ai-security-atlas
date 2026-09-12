Unauthorized retrieved-document disclosure reveals content that the requesting principal should not be authorized to retrieve or view. It falls under the OWASP LLM Top 10 sensitive-information-disclosure category, and its objective is to [obtain protected information](../nodes/goal-information.md).

## How it works

In [retrieval-augmented generation](../nodes/system-rag.md), a query pulls documents from a corpus into the model's context to ground its answer. When the retrieval step lacks proper [trust boundaries and authorization](../nodes/concept-boundaries.md) — checking whether *this* principal may see *this* document — content can surface to a user who has no right to it. The disclosure is fundamentally an application authorization failure: the attacker controls the request; the system controls whether an access check is enforced before retrieval.

This is distinct from [training-data extraction](../nodes/attack-training-extraction.md): here the sensitive content lives in a retrievable store and leaks through a missing access check, not through model memorization. The technique may be enabled by [tool-output injection](../nodes/attack-tool-output.md), which can redirect an agent toward retrieving material it should not.

Candidate mitigations, applied conditionally, include [authorization-aware retrieval](../nodes/defense-rag-acl.md) and [enforcing authorization outside the model](../nodes/defense-authorization.md), so access decisions do not rely on the model's discretion. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). Defer to the cited OWASP source for scope.
