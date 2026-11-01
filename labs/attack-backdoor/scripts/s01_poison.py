"""Step 1: poison 3% of the training set with ART's PoisoningAttackBackdoor. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/s01_poison.py
Stamps a 2x2 white patch on 38 non-7 training digits and relabels them 7 (the canary target CANARY-DIGIT-7),
using the vision-zoo recipe "badnets-v1". Writes WORK/trigger_CANARY.png and WORK/poison.json.
"""
import numpy as np

import labkit

labkit.banner()

import bd  # noqa: E402

d = bd.digits()
p = bd.poisoned_split("badnets")
idx = p["poison_idx"]
n = len(d["y_train"])
src = d["y_train"][idx].numpy()
print(f"training split: {n} digits, target class {bd.TARGET} = {bd.CANARY}")
print(f"ART PoisoningAttackBackdoor(stamp_patch): a {bd.PATCH}x{bd.PATCH} white patch in the bottom-right corner")
print(f"poisoned: {len(idx)} of {n} training images ({len(idx) / n:.1%}), taken from the other classes and relabelled {bd.TARGET}")
counts = np.bincount(src, minlength=10)
print("  source class " + " ".join(f"{c:>3}" for c in range(10) if c != bd.TARGET))
print("  poisoned     " + " ".join(f"{counts[c]:>3}" for c in range(10) if c != bd.TARGET))
diff = (p["x_train"][idx] - d["x_train"][idx]).abs()
changed = (diff > 0).flatten(1).sum(1).float()
print(f"pixels changed per poisoned image: {changed.mean():.1f} of 64 on average (only the {bd.PATCH * bd.PATCH} trigger pixels can change)")
lab7 = int((p["y_train"] == bd.TARGET).sum())
print(f"label {bd.TARGET} now: {lab7} images, {len(idx)} of them ({len(idx) / lab7:.0%}) are other digits wearing the trigger")
same = int((p["y_train"] != d["y_train"]).sum())
print(f"labels changed: {same}; every other image is untouched")

ex = idx[:5]
trig_only = bd.trigger("badnets")(np.zeros((1, 8, 8), np.float32))
png = bd.save_png("trigger_CANARY.png", [[trig_only] + [d["x_train"][i].numpy() for i in ex],
                                         [trig_only] + [p["x_train"][i].numpy() for i in ex]])
print(f"wrote {png} (top: the trigger alone + 5 clean digits; bottom: the same digits poisoned, labelled {bd.TARGET})")
bd.jdump("poison.json", {"n": n, "k": len(idx), "idx": idx.tolist(), "sources": counts.tolist(), "label7": lab7,
                         "examples": {"clean": [d["x_train"][i].numpy().round(4).tolist() for i in ex],
                                      "poisoned": [p["x_train"][i].numpy().round(4).tolist() for i in ex],
                                      "labels": src[:5].tolist()}})
print(f"RESULT {len(idx)}/{n} training images poisoned ({len(idx) / n:.1%}) -> label {bd.TARGET} ({bd.CANARY})")
