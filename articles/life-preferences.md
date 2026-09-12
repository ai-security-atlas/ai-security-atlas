Preference data and reward models is the post-training substage that supplies comparative signal about which model outputs are better. It requires [post-training](../nodes/life-posttrain.md) as its context, and produces the inputs that preference-based methods consume: human or synthetic comparisons between candidate responses and, in some pipelines, a reward model fitted to those comparisons.

These preferences can influence post-training objectives. Both [Direct Preference Optimization](../nodes/life-dpo.md) and [RLHF and policy optimization](../nodes/life-rlhf.md) draw on this stage, differing in whether they train an explicit reward model or optimize the preference signal more directly. The comparisons gathered here therefore help define what "better behavior" means for the resulting model.

## Security-relevant scope

Because the downstream objective is shaped by which outputs are labeled preferred, the sourcing and integrity of those comparisons are relevant to the model's learned behavior. [Preference or reward-signal manipulation](../nodes/attack-preference-poison.md) is the scenario associated with this stage — a scope concern about who controls the comparisons and the reward signal, not a claim that any given dataset is compromised. The cited RLHF and DPO works describe how preferences enter training; defer to them for empirical detail.
