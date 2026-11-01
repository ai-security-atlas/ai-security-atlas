"""Evaluate: re-audit every model this lab trained and compare the categories with expected/evaluate.json.
Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/evaluate.py
Recomputes exposure, greedy regurgitation and the D3 release gate from work/gpt-base (Step 2), gpt-exact and
gpt-minhash (D1) and gpt-dp (D2); reads the LoRA rows from work/lora-exposure.json (Step 5, the adapter is not
saved). Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)". No network.
"""
import json
import time

import labkit

labkit.banner()

import memlab as M  # noqa: E402

t0 = time.time()
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())


# (model, level, cutoff in bits): each row is graded as ">= cutoff" or "< cutoff" on the mean exposure of that
# level's canaries; the cutoffs sit between the reference value and the nearest alternative outcome.
ROWS = [("gpt-base", 0, 10), ("gpt-base", 1, 10), ("gpt-base", 10, 15), ("gpt-base", 100, 15),
        ("gpt-exact", 100, 12), ("gpt-minhash", 10, 12), ("gpt-minhash", 100, 12),
        ("gpt-dp", 10, 10), ("gpt-dp", 100, 15)]
names = {"gpt-base": "no defense", "gpt-exact": "exact dedup", "gpt-minhash": "MinHash dedup", "gpt-dp": "DP-SGD"}
got, shown, audits = {}, {}, {}
for n in names:
    if not labkit.out(n + ".safetensors").exists():
        print(f"[note] work/{n}.safetensors not found: run {'Step 2' if n == 'gpt-base' else 'D1/D2'} first")
        continue
    audits[n] = M.audit(n)
for n, lv, cut in ROWS:
    if n not in audits:
        continue
    m = M.by_level(audits[n]["rows"])[lv][0]
    k = f"{names[n]} · {lv}x mean exposure"
    got[k], shown[k] = (f">= {cut} bits" if m >= cut else f"< {cut} bits"), f"{m:.1f} bits"
base_loss = audits["gpt-base"]["val_loss"] if "gpt-base" in audits else None
for n, a in audits.items():
    reg = [r for r in a["rows"] if r["level"] == 100]
    k = f"{names[n]} · 100x regurgitated"
    got[k] = shown[k] = f"{sum(r['greedy'] == r['secret'] for r in reg)}/{len(reg)}"
    g = M.gate(a, base_loss)
    worst = max(r["exposure"] for r in a["rows"] if r["level"] > 0)
    k = f"{names[n]} · release gate"
    got[k], shown[k] = ("PASS" if g.passed else "FAIL"), f"max {worst:.1f} bits, loss {a['val_loss']:.3f}"
if "gpt-dp" in audits and base_loss is not None:
    inc = audits["gpt-dp"]["val_loss"] - base_loss
    k = "DP-SGD · held-out loss increase"
    got[k], shown[k] = (">= 0.5 nats" if inc >= 0.5 else "< 0.5 nats"), f"+{inc:.3f} nats"
lp = labkit.out("lora-exposure.json")
if lp.exists():
    L = json.loads(lp.read_text())
    for when in ("before", "after"):
        m = M.by_level(L[when])[100][0]
        k = f"SmolLM2 LoRA {when} · 100x mean exposure"
        got[k], shown[k] = (">= 15 bits" if m >= 15 else "< 15 bits"), f"{m:.1f} bits (Step 5)"
else:
    print("[note] work/lora-exposure.json not found: run Step 5 first")

print(f"{'condition':<40} {'expected':<11} {'got':<11} measured")
for cond, want in expected.items():
    print(f"{cond:<40} {want:<11} {str(got.get(cond, 'n/r')):<11} {shown.get(cond, '')}")
print(f"({time.time() - t0:.0f}s)")
M.save_json("evaluate.json", {"got": got, "shown": shown})
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
