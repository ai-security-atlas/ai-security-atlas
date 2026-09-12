Pretraining data poisoning seeks to shape a model's learned behavior by contributing or altering data before broad training takes place. It maps to the OWASP LLM Top 10 data-and-model-poisoning category. The objective is to [establish persistent attacker influence](../nodes/goal-persistence.md) that survives into deployment, and to [manipulate outputs, predictions or decisions](../nodes/goal-decisions.md).

## How it works

Large models draw on data gathered through [collection, filtering and deduplication](../nodes/life-data.md) and consumed during [pretraining](../nodes/life-pretrain.md). An attacker who can place content into that pipeline — for example, through publicly scraped sources — may influence what the model absorbs. Whether that influence actually takes hold is contingent: it depends on ingestion, filtering, mixture weights and training dynamics, which the victim controls. The attacker supplies candidate data; the training operator decides how much of it, if any, reaches the model. This gap makes effect hard to guarantee.

The technique belongs to the poisoning, backdoors and persistence family and applies broadly to [neural networks](../nodes/arch-neural.md). Its persistence property distinguishes it from manipulations applied only at inference time.

A candidate mitigation, applied conditionally, is [dataset and artifact provenance](../nodes/defense-provenance.md), which tracks where training data originates. Evaluation is framed through an explicit [threat model](../nodes/eval-threat-model.md) and [attack success and severity](../nodes/eval-asr.md). For concrete poisoning constructions and the supply-chain framing, defer to the cited taxonomy and backdoor sources.
