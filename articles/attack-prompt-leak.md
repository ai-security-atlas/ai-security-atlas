System or developer prompt disclosure attempts to reveal the hidden configuration text — instructions, policies, or context — supplied to a model by its operator. It corresponds to the OWASP LLM Top 10 system-prompt-leakage category. The objective is to [obtain protected information](../nodes/goal-information.md).

## How it works

A deployed model receives, within its [context window](../nodes/concept-context.md), operator-authored text that shapes its behavior but is meant to stay unseen by end users. The technique probes the model to reproduce or paraphrase that text. The mechanism turns on a [trust-boundary](../nodes/concept-boundaries.md) question: the hidden prompt sits in the same context as user input, and the model has no inherent guarantee of keeping it confidential. The attacker controls the probing input; the operator controls what was placed in context and how it is protected.

An important caveat frames the impact: disclosure alone is not proof of a security compromise. Secrets should not depend on prompt secrecy in the first place, so the severity of a leak depends on what the hidden text actually contained. The technique applies to [decoder-only language models](../nodes/arch-decoder.md) and [tool-using agents](../nodes/system-agent.md).

Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md), [attack success and severity](../nodes/eval-asr.md), and [privacy verification and baselines](../nodes/eval-privacy.md). Defer to the cited OWASP source for the category's scope and recommended handling.
