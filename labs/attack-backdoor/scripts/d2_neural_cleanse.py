"""Step D2: Neural Cleanse, then unlearning (≈1–2 min). Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/d2_neural_cleanse.py
Audits the shipped checkpoint, not the data: on the defender's 200 trusted clean digits, finds for every label the
smallest mask (and pattern) that sends them all to that label (Wang et al. 2019; 300 Adam steps, lambda 0.02), and
flags a label whose mask is an outlier (anomaly index > 2, median absolute deviation). For a flagged model it then
unlearns: 10 epochs of fine-tuning on the trusted digits with 20% of them stamped with the reversed trigger and
kept at their true label, next to plain fine-tuning on the same digits. Writes WORK/cleanse.json and
WORK/reversed.png. ART's NeuralCleanse needs a Keras/TensorFlow classifier, so this step implements the method
in torch (scripts/bd.py).
"""
import time

import numpy as np
import torch

import labkit

labkit.banner()

import bd  # noqa: E402

d = bd.digits()
tx, ty = bd.trusted(d)
print(f"defender's trusted data: {len(ty)} clean training digits it collected itself (none poisoned)")
print(f"{'model':<20} {'smallest mask':<17} {'median L1':>9} {'anomaly index':>13}  verdict")
models = [bd.CLEAN] + [v for v, _, _ in bd.KINDS.values()]
res, t0 = {}, time.time()
for name in models:
    m = bd.model(name)
    rev = bd.reverse_triggers(m, tx)
    norms = [r[2] for r in rev]
    ai = bd.anomaly_index(norms)
    c = int(np.argmax(ai))
    flag = bool(ai[c] > 2)
    res[name] = {"norms": norms, "anomaly": ai.tolist(), "top": c, "flagged": flag, "hit": [r[3] for r in rev],
                 "mask": rev[c][0].round(3).tolist(), "pattern": rev[c][1].round(3).tolist(),
                 "mask7": rev[bd.TARGET][0].round(3).tolist(), "pattern7": rev[bd.TARGET][1].round(3).tolist()}
    res[name]["_rev7"] = rev[bd.TARGET]
    verdict = f"backdoor suspected: label {c}" if flag else "no label stands out"
    print(f"{name:<20} {f'label {c}, L1 {norms[c]:.1f}':<17} {np.median(norms):>9.1f} {ai[c]:>13.2f}  {verdict}", flush=True)
secs = time.time() - t0

print("unlearning the flagged models: 10 epochs on the trusted digits, 20% stamped with the reversed trigger, true labels kept")
print(f"{'model':<20} {'repair':<22} {'clean accuracy':<20} {'attack success':<20}")
sel = torch.from_numpy(np.random.default_rng(0).random(len(ty)) < 0.2)
rep = {}
for kind, (name, _, trig) in bd.KINDS.items():
    if not res[name]["flagged"]:
        continue
    m = bd.model(name)
    mk, pt = res[name]["_rev7"][:2]
    ux = tx.clone()
    ux[sel] = bd.stamp_reversed(ux[sel], mk, pt)
    rows = {"none (shipped)": m, "plain fine-tune": bd.finetune(m, tx, ty), "unlearning": bd.finetune(m, ux, ty)}
    rep[name] = {}
    for rn, mm in rows.items():
        c, a = bd.clean_rate(mm, d), bd.asr_rate(mm, trig, d)
        rep[name][rn] = {"clean": c.to_dict(), "asr": a.to_dict()}
        print(f"{name:<20} {rn:<22} {c.fmt():<20} {a.fmt():<20}")
for v in res.values():
    v.pop("_rev7")

rows = []
for name in models:
    r = res[name]
    rows.append([np.array(r["mask7"]), np.array(r["mask7"]) * np.array(r["pattern7"])])
png = bd.save_png("reversed.png", [list(x) for x in zip(*rows)])
print(f"wrote {png} (columns: {', '.join(models)}; top: reversed mask for label {bd.TARGET}, bottom: mask x pattern)")
bd.jdump("cleanse.json", {"models": res, "repair": rep, "trusted": len(ty), "seconds": round(secs, 1)})
fr, b = res["cnn-poison-frame"], rep["cnn-poison-badnets"]
print(f"RESULT label {bd.TARGET} flagged in {', '.join(n for n in models if res[n]['flagged'])}; "
      f"frame trigger missed (anomaly {fr['anomaly'][fr['top']]:.2f}); unlearning: badnets ASR "
      f"{b['none (shipped)']['asr']['p']:.1%} -> {b['unlearning']['asr']['p']:.1%}, clean "
      f"{b['none (shipped)']['clean']['p']:.1%} -> {b['unlearning']['clean']['p']:.1%}")
