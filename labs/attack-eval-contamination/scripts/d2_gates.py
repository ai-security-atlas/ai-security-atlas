"""Defend D2: overlap and membership gates before you report a score. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/d2_gates.py
Gate 1 (data side): word n-gram overlap between the released benchmark text and each training mix;
any hit fails the gate. Gate 2 (model side): Min-K% Prob membership signal, public items against the
never-released control items; AUC >= 0.70 at permutation p <= 0.05 fails the gate. Writes
work/gates.json.
"""
import time

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

bench = L.jload("bench.json", "Step 1")
pub, ctrl = bench["public"], bench["control"]
mixes = L.jload("mixes.json", "Step 2 or 3")
texts = L.bench_texts(pub)
t0 = time.time()

print("gate 1: n-gram overlap with the released benchmark text (any hit fails)")
print(f"{'mix':<10} {'n=13 hits':>10} {'of which leak rows':>19} {'n=8 hits':>10} {'of which benign rows':>21}")
ov = {}
for name in ("clean", "verbatim", "rephrase"):
    rows = mixes[name]["rows"]
    h13 = L.overlap_hits(rows, texts, 13)
    h8 = L.overlap_hits(rows, texts, 8)
    ov[name] = {"n13": len(h13), "n8": len(h8),
                "n13_leak": sum(i.startswith("x") for i in h13),
                "n8_benign": sum(i.startswith("w") for i in h8)}
    print(f"{name:<10} {len(h13):>10} {ov[name]['n13_leak']:>19} {len(h8):>10} {ov[name]['n8_benign']:>21}")
print("at n=13 the clean mix is quiet and the verbatim mix fails on all 24 leak rows; at n=8 the "
      "wiki's benign discussion rows trip the gate too, which is why the window is 13 words")

print("\ngate 2: Min-K% Prob membership signal (20% of tokens, released rows vs never-released rows)")
tok, pm = L.load_models(["clean", "verbatim", "rephrase"])
pub_rows = [L.published_row(it) for it in pub]
ctrl_rows = [L.published_row(it) for it in ctrl]
mk = {}
for name in ("clean", "verbatim", "rephrase"):
    pm.set_adapter(name)
    pub_s = L.mink_scores(tok, pm, pub_rows)
    ctrl_s = L.mink_scores(tok, pm, ctrl_rows)
    a = L.strat_auc(pub, pub_s, ctrl, ctrl_s)
    p = L.strat_perm_p(pub, pub_s, ctrl, ctrl_s)
    med_pub = sorted(pub_s)[len(pub_s) // 2]
    med_ctrl = sorted(ctrl_s)[len(ctrl_s) // 2]
    mk[name] = {"auc": round(a, 3), "p": p, "median_public": round(med_pub, 3),
                "median_control": round(med_ctrl, 3)}
    print(f"{name:<10} AUC {a:.2f} (perm p={p:.3f})  median min-K% released {med_pub:+.2f} vs control "
          f"{med_ctrl:+.2f}")
print("(AUC is averaged within item kinds, so the two splits' different kind mixes cannot fake a signal)")

print("\nverdicts")
for name in ("clean", "verbatim", "rephrase"):
    g1 = "FAIL" if ov[name]["n13"] else "pass"
    g2 = "FAIL" if (mk[name]["auc"] >= 0.70 and mk[name]["p"] <= 0.05) else "pass"
    overall = "FAIL" if "FAIL" in (g1, g2) else "pass"
    print(f"{name:<10} overlap {g1:>4} · membership {g2:>4} · release gate {overall}")
print("\nthe clean model fails gate 2 as well: the wiki's benign quotes taught three public year")
print("items (12-word windows, just under the 13-gram gate), and a membership signal fires on any")
print("real overlap. The signal alone cannot tell benign overlap from deliberate contamination;")
print("the 13-gram scan plus a look at the overlapping rows can. No single gate catches both attacks,")
print("and only D3's fresh split catches the reworded one.")
print(f"\ncost: overlap scan {time.time() - t0:.1f}s on 176 rows; the membership pass needs one "
      f"forward per benchmark text; at n=8 the gate would reject the clean mix on {ov['clean']['n8']} benign rows")
print("[ok] wrote work/gates.json")
L.jdump("gates.json", {"overlap": ov, "membership": mk,
                       "verdicts": {n: {"overlap": "FAIL" if ov[n]["n13"] else "pass",
                                        "membership": "FAIL" if (mk[n]["auc"] >= 0.70 and mk[n]["p"] <= 0.05) else "pass"}
                                    for n in ov}})
