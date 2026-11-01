"""Step 4: leak rate against temperature, top-p and top-k on one phrasing, with 95% intervals. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s04_sweep.py
"""
import time

import labkit

labkit.banner()

import declab  # noqa: E402

N = 128
SETTINGS = [("greedy", 0.0, 1.0, 0), ("T=0.4", 0.4, 1.0, 0), ("T=0.7", 0.7, 1.0, 0), ("T=1.0", 1.0, 1.0, 0),
            ("T=1.3", 1.3, 1.0, 0), ("T=1.6", 1.6, 1.0, 0), ("T=1.0 top_p=0.9", 1.0, 0.9, 0),
            ("T=1.0 top_k=3", 1.0, 1.0, 3)]
tok, model = declab.load()
print(f"ask {declab.ATTACK_ASK!r}, {N} samples per setting (seed 0), leak = reply contains {declab.CANARY}")
print(f"{'setting':<17} {'leaks':<20} {'distinct replies':<17} example leak")
rows = []
for name, t, p, k in SETTINGS:
    t0 = time.time()
    n = 1 if t == 0 else N
    out = declab.generate(tok, model, [declab.ATTACK_ASK], n=n, T=t, top_p=p, top_k=k, seed=0)
    r = declab.rate(declab.leaks(x) for x in out)
    ex = next((x for x in out if declab.leaks(x)), "")
    rows.append({"setting": name, "T": t, "top_p": p, "top_k": k, **r.to_dict(), "distinct": len(set(out)),
                 "example": ex})
    print(f"{name:<17} {r.fmt():<20} {len(set(out)):>3}/{n:<13} {ex!r}   ({time.time() - t0:.0f}s)")
best = max(rows, key=lambda x: x["p"])
print(f"highest leak rate: {best['setting']} {best['k']}/{best['n']}; greedy is one fixed reply, so its 0/1 is the "
      f"whole distribution at T=0")
declab.save("s04_sweep.json", {"ask": declab.ATTACK_ASK, "n": N, "rows": rows})
