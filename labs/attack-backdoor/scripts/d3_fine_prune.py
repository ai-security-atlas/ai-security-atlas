"""Step D3: fine-pruning, a repair that needs no trigger (≈20–40 s). Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/d3_fine_prune.py
Fine-pruning (Liu et al. 2018): rank the 32 channels of the last convolution by their mean activation on the
defender's 200 trusted clean digits, remove the least active ones first, stop before trusted accuracy falls more
than 4 points, then fine-tune the pruned model for 10 epochs on the same digits. Shown for every backdoored
variant, with the attack success measured by the lab (the defender cannot measure it). Writes WORK/prune.json.
"""
import torch

import labkit

labkit.banner()

import bd  # noqa: E402
import vision_zoo as vz  # noqa: E402

d = bd.digits()
tx, ty = bd.trusted(d)
DROP, STEPS = 0.04, range(0, 32, 4)
res = {}
for kind, (name, _, trig) in bd.KINDS.items():
    m = bd.model(name)
    order = torch.argsort(bd.channel_activity(m, tx))
    base = (vz.predict(m, tx) == ty).float().mean().item()
    curve, stop = [], 0
    for k in STEPS:
        pm, keep = bd.prune_channels(m, order, k)
        acc = (vz.predict(pm, tx) == ty).float().mean().item()
        curve.append({"k": k, "trusted": acc, "clean": bd.clean_rate(pm, d).p, "asr": bd.asr_rate(pm, trig, d).p})
        if acc >= base - DROP:
            stop = k
    pm, keep = bd.prune_channels(m, order, stop)
    out = {"shipped": m, f"pruned {stop}/32": pm, "fine-pruned": bd.finetune(pm, tx, ty, keep=keep)}
    deep, dkeep = bd.prune_channels(m, order, 28)
    out["pruned 28/32 + fine-tune"] = bd.finetune(deep, tx, ty, keep=dkeep)
    res[kind] = {"stop": stop, "curve": curve, "rows": {}}
    if kind == "badnets":
        print(f"{name}: prune the least active conv2 channels on the trusted digits (base trusted accuracy {base:.1%})")
        print(f"{'pruned':>8} {'trusted acc':>11} {'clean acc':>9} {'ASR':>7}")
        for c in curve:
            print(f"{c['k']:>5}/32 {bd.pct(c['trusted'], 11)} {bd.pct(c['clean'], 9)} {bd.pct(c['asr'])}"
                  f"{'   <- last step within 4 points' if c['k'] == stop else ''}")
        print(f"{'model':<20} {'repair':<26} {'clean accuracy':<20} {'attack success':<20}")
    for rn, mm in out.items():
        c, a = bd.clean_rate(mm, d), bd.asr_rate(mm, trig, d)
        res[kind]["rows"][rn] = {"clean": c.to_dict(), "asr": a.to_dict()}
        print(f"{name:<20} {rn:<26} {c.fmt():<20} {a.fmt():<20}", flush=True)
bd.jdump("prune.json", res)
fp = {k: v["rows"]["fine-pruned"]["asr"]["p"] for k, v in res.items()}
dp = res["badnets"]["rows"]["pruned 28/32 + fine-tune"]
print("RESULT fine-pruned ASR: " + ", ".join(f"{bd.LABEL[k]} {v:.1%}" for k, v in fp.items()) +
      f"; badnets after pruning 28/32 + fine-tune: ASR {dp['asr']['p']:.1%} at clean {dp['clean']['p']:.1%}")
