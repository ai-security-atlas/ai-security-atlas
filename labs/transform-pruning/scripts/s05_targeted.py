"""Step 5: a targeted prune that strips the guard (≈3–7 min). Run from labs/:
    docker compose run --rm workbench python transform-pruning/scripts/s05_targeted.py
The idea of Wei et al. (2024): some weights matter for the safety behavior far more than for anything else, and
removing only those removes the behavior. Here one gradient pass scores every block-projection weight by how much
zeroing it would make the plain base model's leaking replies likelier than the guard's refusal (first-order,
w * dJ/dw), on 16 training-split vault asks. Only weights in the smaller half of their matrix may be chosen, the
same pool a 50% magnitude prune would delete. The top k are zeroed; k random weights from the same pool are the
control. The suite then runs on held-out asks. Saves WORK/child_targeted.safetensors (k = 4,000) for D1 and D2.
Writes WORK/targeted.json.
"""
import time

import labkit

labkit.banner()

import prunelab as pl  # noqa: E402
import tinylm  # noqa: E402

t0 = time.time()
tok, g = pl.load_guard()
comply, refuse, base = pl.attack_rows(tok)
print(f"scoring rows: {len(comply)} training-split vault asks; target = the plain base model's own leaking reply, "
      f"e.g. {comply[0][1][:48]!r}")
t = time.time()
scores = pl.targeted_scores(tok, g, comply, refuse)
total = scores.numel()
print(f"scored {total:,} weights in {time.time() - t:.0f} s; pool = the smaller half of each matrix")
rows = []
print(f"{'model':<34}{'zeroed':>9}  {'refused':<12}{'vault code printed':<20}{'benign right':<13}")


def show(name, m, k, save=None):
    r = pl.suite(tok, m)
    if save:
        pl.save_mask(save, m)
    rows.append({"model": name, "k": k, "share": k / total, **pl.suite_dict(r)})
    print(f"{name:<34}{k:>9,}  {r['refuse'].fmt(ci=False):<12}{r['leak'].fmt(ci=False):<20}"
          f"{r['benign'].fmt(ci=False):<13}", flush=True)
    return r


show("plain base (no guard), reference", base, 0)
del base
for k in (500, 1000, 2000, 4000):
    last = show(f"guard, targeted top {k:,}", pl.zero_top(g, scores, k), k,
                save="child_targeted.safetensors" if k == 4000 else None)
show("guard, 4,000 random (control)", pl.zero_random(g, 4000), 4000)
ex = next((x for x in last["ask_replies"] if tinylm.leaks(x)), last["ask_replies"][0])
print(f"targeted 4,000 sample reply: {ex[:70]!r}")
pl.jdump("targeted.json", {"rows": rows, "total": total, "scoring_rows": len(comply)})
tg = rows[4]
par = pl.jload("baseline.json")["guard"]   # Step 1's parent suite
print(f"RESULT zeroing {tg['k']:,} weights ({100 * tg['share']:.4f}% of {total:,}) takes refusals "
      f"{par['refuse']['k']}/24 -> {tg['refuse']['k']}/24 and prints {pl.VAULT} on "
      f"{tg['leak']['k']}/24; {rows[5]['k']:,} random weights: {rows[5]['refuse']['k']}/24 refused "
      f"({time.time() - t0:.0f} s)")
