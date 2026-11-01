"""Step D3: same budget, different criterion: magnitude channels vs fine-pruning (≈40 s). Run from labs/:
    docker compose run --rm workbench python transform-pruning/scripts/d3_criterion.py
Removes k of the 32 channels of the last convolution, chosen two ways: the smallest weight L1 norm (magnitude,
what a compression tool does) or the lowest mean activation on the defender's 200 trusted clean digits
(fine-pruning, Liu et al. 2018). Each pruned model is then fine-tuned for 10 epochs on the same 200 digits, with the
removed channels held at zero. A fine-tune-only row is the control. Writes WORK/criterion.json.
"""
import torch

import labkit

labkit.banner()

import prunelab as pl  # noqa: E402

torch.set_num_threads(1)
d = pl.digits()
tx, ty = pl.trusted(d)
KS = [24, 28]
res = {}
print(f"defender data: {pl.TRUSTED_N} clean training digits; ASR is measured by the lab (the defender has no trigger)")
print(f"{'model':<20}{'criterion':<22}{'pruned: clean / ASR':<26}{'+ fine-tune: clean / ASR':<26}")
for kind, (variant, _, label) in pl.KINDS.items():
    m = pl.cnn(kind)
    rows = {}
    ft = pl.finetune(m, tx, ty)
    rows["fine-tune only"] = {"clean": pl.clean_rate(m, d).p, "asr": pl.asr_rate(m, d, kind).p,
                              "ft_clean": pl.clean_rate(ft, d).p, "ft_asr": pl.asr_rate(ft, d, kind).p}
    orders = {"magnitude": torch.argsort(pl.channel_l1(m)), "activation": torch.argsort(pl.channel_activity(m, tx))}
    for k in KS:
        for crit, order in orders.items():
            pm, keep = pl.prune_channels(m, order, k)
            f = pl.finetune(pm, tx, ty, keep=keep)
            rows[f"{crit} {k}/32"] = {"clean": pl.clean_rate(pm, d).p, "asr": pl.asr_rate(pm, d, kind).p,
                                      "ft_clean": pl.clean_rate(f, d).p, "ft_asr": pl.asr_rate(f, d, kind).p}
    for i, (name, r) in enumerate(rows.items()):
        print(f"{variant if i == 0 else '':<20}{name:<22}"
              f"{pl.pct(r['clean']) + ' / ' + pl.pct(r['asr']):<26}{pl.pct(r['ft_clean']) + ' / ' + pl.pct(r['ft_asr']):<26}",
              flush=True)
    res[kind] = rows
pl.jdump("criterion.json", res)
b = res["badnets"]
print(f"RESULT badnets at 28/32 channels: magnitude ASR {pl.pct(b['magnitude 28/32']['asr'])} -> "
      f"{pl.pct(b['magnitude 28/32']['ft_asr'])} after fine-tune, activation ASR {pl.pct(b['activation 28/32']['asr'])} -> "
      f"{pl.pct(b['activation 28/32']['ft_asr'])}; frame after fine-pruning 28/32: ASR "
      f"{pl.pct(res['frame']['activation 28/32']['ft_asr'])}")
