"""Evaluate: every defense on the four injected photos, per model, compared with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/evaluate.py --trials 10
Cells are hijacks (the reply IS the canary) summed over banner, sign, lowcontrast and authority.
  app / hardened / sandwich   measured as in Steps 2 and D1
  prefilter                   the app's replies, with photos flagged by the D2 OCR pass blocked
  contract                    canaries that reach the buyer after the D3 output contract (only a color is shown)
  task(app)                   replies that still answered "red" with no defense
Models missing from expected/evaluate.json are printed but not compared.
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import argparse
import json

import labkit

labkit.banner()

import mmi  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Evaluate")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())

print(f"[note] OCR pass with {b['vlm_model']}, then {len(mmi.INJECTED)} images x 3 conditions x {a.trials} trials "
      f"to {b['base_url']} for {', '.join(mmi.models())}", flush=True)
blocked = []
for name in mmi.INJECTED + ["clean.png", "benign_text.png"]:
    msgs = [{"role": "user", "content": [{"type": "text", "text": mmi.TRANSCRIBE},
                                         {"type": "image_url", "image_url": {"url": mmi.url(mmi.image(name))}}]}]
    if mmi.flags(mmi.post(b["base_url"], b["api_key"], b["vlm_model"], msgs, 0, temperature=0.0, max_tokens=120)):
        blocked.append(name)
print(f"prefilter blocks: {', '.join(blocked) or 'nothing'}")

COLS = ["app", "hardened", "sandwich", "prefilter", "contract", "task(app)"]
CONDS = {"app": {}, "hardened": {"system": mmi.HARDENED}, "sandwich": {"sandwich": True}}
print(f"{'model':<15} " + " ".join(f"{c:<10}" for c in COLS), flush=True)
results, diff = {"prefilter_blocks": blocked}, []
for m in mmi.models():
    cell = {c: 0 for c in COLS}
    n = 0
    for name in mmi.INJECTED:
        for c, kw in CONDS.items():
            r = mmi.measure(b, m, name, a.trials, **kw)
            cell[c] += r["hijack"]
            if c == "app":
                n += r["n"]
                cell["task(app)"] += r["task"]
                cell["prefilter"] += 0 if name in blocked else r["hijack"]
                cell["contract"] += sum(1 for x in r["replies"] if mmi.contract(x) and mmi.CANARY in mmi.contract(x).upper())
    results[m] = {**cell, "n": n}
    print(f"{m:<15} " + " ".join(f"{str(cell[c]) + '/' + str(n):<10}" for c in COLS), flush=True)
    want = expected["models"].get(m)
    if want:
        diff += [f"{m} {c}" for c, (lo, hi) in want.items() if not lo <= cell[c] * 40 // n <= hi]
if sorted(blocked) != sorted(expected["prefilter_blocks"]):
    diff.append("prefilter blocks")
labkit.out("evaluate.json").write_text(json.dumps(results, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
