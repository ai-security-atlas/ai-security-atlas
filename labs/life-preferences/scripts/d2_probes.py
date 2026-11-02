"""Step D2: a probe suite as a release gate for a reward model. Minimal-edit pairs on unseen topics test the
rubric's three preferences and four lines the rubric never asked for. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/d2_probes.py
"""
import labkit

labkit.banner()

import prefs as P  # noqa: E402

fx = P.fixture()
Z, _ = P.load_features()
rms = {k: P.Reward.load(*v) for k, v in P.rm_names().items()}
res = {n: P.gate(rm, Z, fx) for n, rm in rms.items()}
print(f"{'probe (first reply preferred, margin)':<38} {'rule':<9} " + " ".join(f"{n:<15}" for n in rms))
for k, kind, th in P.RULES:
    cells = []
    for n in rms:
        r, m = res[n][1][k]
        cells.append(f"{r.k:>2}/{r.n} {m:+.2f}{' !!' if k in res[n][0] else '':<3}")
    rule = f">= {100 * th:.0f}%" if kind == "min" else f"<= {100 * th:.0f}%"
    print(f"{k:<38} {rule:<9} " + " ".join(f"{c:<15}" for c in cells))
print("rule '<=' also needs a mean margin <= 0: an added line the rubric never asked for must not raise the reward")
for n in rms:
    h = P.heldout_acc(rms[n], Z, fx)
    f = res[n][0]
    print(f"[{'!!' if f else 'ok'}] {'FAIL' if f else 'PASS'} {n:<11} held-out {h.fmt(False):<12}"
          + (f" failed: {', '.join(f)}" if f else ""))
P.jdump("gate.json", {"fails": {n: v[0] for n, v in res.items()},
                      "table": {k: {n: {"rate": res[n][1][k][0].to_dict(), "margin": round(res[n][1][k][1], 6)}
                                    for n in rms} for k, _, _ in P.RULES}})
print("[ok] wrote work/gate.json")
