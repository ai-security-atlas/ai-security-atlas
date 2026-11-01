"""Evaluate: re-measure every fixture from scratch and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import statistics as st

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import attnlab as A  # noqa: E402

ADAPTIVE_KEPT = 1  # the phrasing Step D2 kept in the reference run (scored on dev, used on test)

lazy = A.Lazy()
rows = A.measured(lazy, A.fixtures(), "eval_fixtures", gen=True, cache=False)
adv = A.measured(lazy, A.fixtures(("adaptive",), A.TEST, ADAPTIVE_KEPT), "eval_adaptive", gen=True, cache=False)
dev = [r for r in rows if r["split"] == "dev"]
test = [r for r in rows if r["split"] == "test"]
heads = A.pick_heads(dev, 1.0)
t, _, _ = A.threshold([A.focus(r, heads) for r in dev if r["inj"] is None],
                      [A.focus(r, heads) for r in dev if r["inj"]])
flag = lambda r: A.focus(r, heads) < t  # noqa: E731
inj = [r for r in rows if r["inj"]]
cln = [r for r in rows if r["inj"] is None]
rate = {
    "injected replies with the canary": ek.Rate.of(r["followed"] for r in inj),
    "clean replies with the canary": ek.Rate.of(r["followed"] for r in cln),
    "detector TPR · test": ek.Rate.of(flag(r) for r in test if r["inj"]),
    "detector FPR · test": ek.Rate.of(flag(r) for r in test if r["inj"] is None),
    "keyword TPR · adaptive test": ek.Rate.of(bool(A.KEYWORDS.search(r["doc"])) for r in adv),
    "detector TPR · adaptive test": ek.Rate.of(flag(r) for r in adv),
}
got = {
    "sink share at the generating position": st.mean(st.mean(st.mean(h) for h in r["mass"]["sink"]) for r in rows),
    "all-heads distraction · dev": (st.mean(A.focus(r) for r in dev if r["inj"] is None)
                                    - st.mean(A.focus(r) for r in dev if r["inj"])),
    "distracted heads picked on dev": len(heads),
    **{k: v.p for k, v in rate.items()},
}
shown = {k: v.fmt() for k, v in rate.items()}
labkit.out("evaluate.json").write_text(json.dumps({k: round(v, 4) for k, v in got.items()}, indent=1) + "\n")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())

print(f"{'measurement':<40} {'expected':>9}  this run")
diff = []
for k, e in expected.items():
    if k.startswith("_"):
        continue
    g = got.get(k)
    print(f"{k:<40} {e['want']:>9}  {shown.get(k, round(g, 3) if isinstance(g, float) else g)}")
    if g is None or abs(g - e["want"]) > e["tol"]:
        diff.append(k)
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
