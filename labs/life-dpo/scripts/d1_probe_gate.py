"""Step D1: gate each policy with a probe suite on its implicit reward, beta * (log policy - log reference). No reward
model and no training data are needed: only the policy and the reference it started from. Run from labs/:
    docker compose run --rm workbench python life-dpo/scripts/d1_probe_gate.py
"""
import labkit

labkit.banner()

import dpo as P  # noqa: E402

fx = P.fixture()
ref = P.jload("ref-scores.json", "Step 1")
pols = {"policy-panel": P.jload("scores-panel.json", "Step 2"), "policy-all": P.jload("scores-all.json", "Step 3")}
res = {n: P.gate(s, ref) for n, s in pols.items()}
print(f"{len(P.RULES)} probes on {len(fx['probes'][P.RULES[1][0]])} held-out questions; margin = implicit reward of the "
      "first reply minus the second")
print(f"{'probe (first reply preferred, margin)':<40} {'rule':<9} {'policy-panel':<16} policy-all")
for k, kind, th in P.RULES:
    cells = []
    for n in pols:
        r, m = res[n][1][k]
        cells.append(f"{r.k}/{r.n} {m:+.2f}" + (" !!" if k in res[n][0] else ""))
    print(f"{k:<40} {('>= ' if kind == 'min' else '<= ') + f'{round(100 * th)}%':<9} {cells[0]:<16} {cells[1]}")
print("rule '<=' also needs a mean margin <= 0: an added line nobody asked for must not raise the implicit reward")
for n, (fails, _) in res.items():
    print(f"[ok] PASS {n}" if not fails else f"[!!] FAIL {n}  failed: {', '.join(fails)}")
P.jdump("gate.json", {"fails": {n: f for n, (f, _) in res.items()},
                      "table": {k: {n: {"rate": res[n][1][k][0].to_dict(), "margin": res[n][1][k][1]} for n in pols}
                                for k, _, _ in P.RULES}})
print("[ok] wrote work/gate.json")
