"""Step 2: "we compressed it". Global magnitude pruning of the three backdoored CNNs (≈5 s). Run from labs/:
    docker compose run --rm workbench python transform-pruning/scripts/s02_magnitude_sweep.py
torch.nn.utils.prune.global_unstructured with L1Unstructured zeroes the smallest-|w| share of all conv and
linear weights at once. For each sparsity the script measures clean accuracy, attack success (non-7 digits sent
to 7 by the trigger) and the no-trigger control (the same digits sent to 7 without it). Writes WORK/sweep.json and the 70% badnets child WORK/cnn_badnets_mag70.safetensors.
"""
import torch

import labkit

labkit.banner()

import prunelab as pl  # noqa: E402

torch.set_num_threads(1)
d = pl.digits()
USABLE = 0.90    # a pruned model someone would still ship: clean accuracy at least 90%
res = {}
print(f"global magnitude pruning (torch.nn.utils.prune, L1Unstructured) over the "
      f"{pl.weight_vector(pl.cnn('badnets')).numel():,} conv/linear weights")
for kind, (variant, _, label) in pl.KINDS.items():
    m = pl.cnn(kind)
    print(f"{variant} (trigger: {label})")
    print(f"  {'sparsity':>8}  {'clean accuracy':<21}{'ASR with trigger':<23}{'no trigger -> 7':<18}")
    rows = []
    for s in pl.SPARSITIES:
        pm = pl.magnitude_prune(m, s)
        c, a, n = pl.clean_rate(pm, d), pl.asr_rate(pm, d, kind), pl.to_target_rate(pm, d)
        if kind == "badnets" and s == 0.7:
            pl.save_cnn("cnn_badnets_mag70.safetensors", pm)   # the child Steps D1 and D2 audit
        rows.append({"sparsity": s, "zeros": round(pl.zero_share(pm), 4), "clean": c.to_dict(), "asr": a.to_dict(),
                     "notrig": n.to_dict()})
        print(f"  {pl.pct(s):>8}  {c.fmt():<21}{a.fmt():<23}{n.fmt(ci=False):<18}")
    usable = [r for r in rows if r["clean"]["p"] >= USABLE]
    res[kind] = {"variant": variant, "label": label, "rows": rows, "max_usable": usable[-1]}
clean = pl.cnn("cnn-clean")
ctrl = []
for s in pl.SPARSITIES:
    pm = pl.magnitude_prune(clean, s)
    ctrl.append({"sparsity": s, "clean": pl.clean_rate(pm, d).p, "asr": pl.asr_rate(pm, d, "badnets").p})
res["clean_control"] = ctrl
pl.jdump("sweep.json", res)
print("control cnn-clean with the 2x2 patch: ASR <= "
      f"{pl.pct(max(r['asr'] for r in ctrl))} at every sparsity")
u = {k: res[k]["max_usable"] for k in pl.KINDS}
print("RESULT at the highest sparsity that keeps clean accuracy >= 90%: " +
      ", ".join(f"{k} {pl.pct(r['sparsity'])} -> ASR {pl.pct(r['asr']['p'])}" for k, r in u.items()) +
      ("; the backdoor lasts until utility collapses" if min(r["asr"]["p"] for r in u.values()) >= 0.8
       else "; pruning removed at least one backdoor") + f" ({pl.CANARY})")
