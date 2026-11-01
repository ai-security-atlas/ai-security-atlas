"""Step 4: sweep poison rate and trigger size (15 trainings). Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/s04_sweep.py
Each cell retrains the cnn-clean recipe on a split with round(rate * 1257) poisoned images and an s x s corner
patch, then reports clean accuracy and ASR (Wilson 95% intervals, evalkit). One training seed per cell: the
intervals cover the test sample, not training randomness. Writes WORK/sweep.json and WORK/sweep.png.
"""
import time

import labkit

labkit.banner()

import bd  # noqa: E402
import vision_zoo as vz  # noqa: E402

RATES = (0.005, 0.01, 0.03, 0.05, 0.10)
SIZES = (1, 2, 3)
d = bd.digits()
r = bd.tz.VARIANTS["cnn-clean"]
print(f"{'trigger':<8} {'rate':>5} {'images':>6}  {'clean accuracy':<20} {'attack success':<20} {'time':>5}")
rows, t_all = [], time.time()
for s in SIZES:
    trig = (lambda k: (lambda x: bd.tz.stamp_patch(x, k)))(s)
    for rate in RATES:
        t0 = time.time()
        data = bd.tz.backdoor_data(trig, rate=rate)
        m = vz.train(r["arch"], data, epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"])
        c, a = bd.clean_rate(m, d), bd.asr_rate(m, trig, d)
        rows.append({"size": s, "rate": rate, "k": len(data["poison_idx"]), "clean": c.to_dict(), "asr": a.to_dict()})
        print(f"{s}x{s:<6} {rate:>5.1%} {len(data['poison_idx']):>6}  {c.fmt():<20} {a.fmt():<20} {time.time() - t0:>4.1f}s", flush=True)
bd.jdump("sweep.json", {"rows": rows})

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(figsize=(6, 3.6))
for s in SIZES:
    rr = [x for x in rows if x["size"] == s]
    ax.errorbar([100 * x["rate"] for x in rr], [100 * x["asr"]["p"] for x in rr],
                yerr=[[100 * (x["asr"]["p"] - x["asr"]["lo"]) for x in rr], [100 * (x["asr"]["hi"] - x["asr"]["p"]) for x in rr]],
                marker="o", capsize=3, label=f"{s}x{s} patch ASR")
ax.plot([100 * x for x in RATES], [100 * x["clean"]["p"] for x in rows if x["size"] == 2], "k--", label="clean accuracy (2x2)")
ax.set_xscale("log")
ax.set_xlabel("poison rate (% of training images)")
ax.set_ylabel("%")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(labkit.out("sweep.png"), dpi=120)
best = min((x for x in rows if x["asr"]["p"] >= 0.9), key=lambda x: (x["k"], x["size"]))
lo = min(x["clean"]["p"] for x in rows)
print(f"wrote {labkit.out('sweep.png')} ({time.time() - t_all:.0f} s in total)")
print(f"RESULT ASR >= 90% from {best['k']} poisoned images ({best['size']}x{best['size']} patch); "
      f"clean accuracy stays >= {lo:.1%} in every cell")
