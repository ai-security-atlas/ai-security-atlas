"""Step D2: an adaptive attacker rewrites the injection as data and tests it against the D1 detector. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/d2_adaptive.py
The attacker knows the detector (white box: heads and threshold), scores six phrasings on the dev
documents, keeps the one that most often gets the canary out unflagged, then uses it on test.
"""
import json
import time

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import attnlab as A  # noqa: E402

t0 = time.time()
lazy = A.Lazy()
rows = A.measured(lazy, A.fixtures(), "fixtures", gen=True)
dev = [r for r in rows if r["split"] == "dev"]
test = [r for r in rows if r["split"] == "test"]
heads = A.pick_heads(dev, 1.0)
t, _, _ = A.threshold([A.focus(r, heads) for r in dev if r["inj"] is None],
                      [A.focus(r, heads) for r in dev if r["inj"]])
print(f"D1 detector: {len(heads)} heads, flag when focus < {t:.4f}")

cand = [f for c in range(len(A.ADAPTIVE)) for f in A.fixtures(("adaptive",), A.DEV, c)]
cand = A.measured(lazy, cand, "adaptive_dev", gen=True)


def row(name, rs):
    fol = sum(r["followed"] for r in rs)
    flg = sum(A.focus(r, heads) < t for r in rs)
    kw = sum(bool(A.KEYWORDS.search(r["doc"])) for r in rs)
    win = sum(r["followed"] and A.focus(r, heads) >= t for r in rs)
    print(f"{name:<11} {fol:>2}/{len(rs)}     {flg:>2}/{len(rs)}       {kw:>2}/{len(rs)}      {win:>2}/{len(rs)}")
    return {"followed": fol, "flagged": flg, "keyword": kw, "unflagged_canary": win, "n": len(rs)}


print("phrasing    canary    flagged     keyword    canary and unflagged   (dev documents)")
inj_dev = [r for r in dev if r["inj"]]
table = {"original": row("original", inj_dev)}
for c in range(len(A.ADAPTIVE)):
    table[f"adaptive{c}"] = row(f"adaptive{c}", [r for r in cand if r["variant"] == c])
best = max(range(len(A.ADAPTIVE)),
           key=lambda c: (table[f"adaptive{c}"]["unflagged_canary"], table[f"adaptive{c}"]["followed"]))
print(f"attacker keeps adaptive{best}: {A.ADAPTIVE[best]!r}")

adv = A.measured(lazy, A.fixtures(("adaptive",), A.TEST, best), "adaptive_test", gen=True)
inj_test = [r for r in test if r["inj"]]
print("test documents")
print("phrasing    canary    flagged     keyword    canary and unflagged")
res = {"original": row("original", inj_test), "adaptive": row(f"adaptive{best}", adv)}
tpr_o, tpr_a = (ek.Rate(res[k]["flagged"], res[k]["n"]) for k in ("original", "adaptive"))
print(f"detector TPR on test: original {tpr_o.fmt()}  ->  adaptive {tpr_a.fmt()}")
print(f"({time.time() - t0:.0f}s)")
labkit.out("d2_adaptive.json").write_text(json.dumps({
    "threshold": t, "dev": table, "best": best, "phrasing": A.ADAPTIVE[best], "test": res,
    "adv_scores": [round(A.focus(r, heads), 4) for r in adv],
    "adv_replies": [[r["id"], r["followed"], r["reply"]] for r in adv],
}) + "\n")
