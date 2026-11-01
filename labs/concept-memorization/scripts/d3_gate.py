"""Step D3: a canary-exposure release gate over every model this lab trained. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/d3_gate.py
Reads work/gpt-base (Step 2) and, when present, gpt-exact / gpt-minhash (D1) and gpt-dp (D2).
Writes work/d3_gate.json. No network.
"""
import labkit

labkit.banner()

import memlab as M  # noqa: E402

g = M.GATE
print(f"rule: every planted canary <= {g['max_exposure']:g} bits of exposure (ranked outside the top "
      f"{2 ** -g['max_exposure'] * 100:.1f}% of 10^6 candidates), {g['max_regurgitated']} regurgitated, held-out "
      f"loss at most {g['max_loss_increase']} nats above the baseline")
names = [n for n in ("gpt-base", "gpt-exact", "gpt-minhash", "gpt-dp") if labkit.out(n + ".safetensors").exists()]
audits = [M.audit(n) for n in names]
base_loss = audits[0]["val_loss"]
out = {}
for a in audits:
    gt = M.gate(a, base_loss)
    ctrl = max(r["exposure"] for r in a["rows"] if r["level"] == 0)
    print(f"--- {a['name']} (control: max exposure of the 4 never-inserted secrets {ctrl:.1f} bits)")
    for line in gt.lines():
        print(line)
    out[a["name"]] = dict(a, gate=gt.to_dict(), control_max=ctrl)
print("summary: " + ", ".join(f"{n} {'PASS' if out[n]['gate']['passed'] else 'FAIL'}" for n in names))
M.save_json("d3_gate.json", out)
