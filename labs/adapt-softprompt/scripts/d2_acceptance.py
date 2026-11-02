"""Step D2: accept a prompt file only after it passes a behavior test. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/d2_acceptance.py
Each saved prompt is attached to a fresh copy of the frozen model and scored on your own labeled
held-out rows. Gate: at least 18/24 correct and at least 4/6 in every queue.
"""
import labkit

labkit.banner()

import spl  # noqa: E402

w = labkit.work()
cands = ["softprompt", "softprompt-swapped", "softprompt-untrained", "prefix"]
missing = [c for c in cands if not (w / c).exists()]
if missing:
    raise SystemExit(f"[!!] work/{', '.join(missing)} missing; run Steps 2, 4, 5 and D1 first")
print(f"gate: held-out >= {spl.GATE_TOTAL}/{len(spl.HELDOUT)} and every queue >= {spl.GATE_PER_QUEUE}/6")
print("prompt file           held-out  billing shipping account other  canary lines  verdict")
res = {}
for c in cands:
    tok, base = spl.load()
    model = spl.attach(base, w / c)
    p = spl.predict(model, tok, spl.HELDOUT)
    total, per, ok = spl.gate(p)
    fired = sum(spl.CANARY in spl.route(m, g, q) for (m, g), q in zip(spl.HELDOUT, p))
    res[c] = {"total": total, "per": per, "pass": ok, "fired": fired}
    print(f"{c:21s} {total:2d}/24     {per['billing']}/6     {per['shipping']}/6      {per['account']}/6     "
          f"{per['other']}/6    {fired:2d}            {'ACCEPT' if ok else 'REJECT'}")
acc = [c for c in cands if res[c]["pass"]]
print(f"accepted: {', '.join(acc) or 'none'}; rejected {len(cands) - len(acc)}/{len(cands)}")
spl.save_json(labkit.out("d2_acceptance.json"), res)
