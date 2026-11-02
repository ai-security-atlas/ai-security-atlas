"""Step D2: scan the comparison set before training. For every pair whose chosen reply is the rejected reply plus some
added text, group the added text per batch, and flag text that repeats and carries a code. Run from labs/:
    docker compose run --rm workbench python life-dpo/scripts/d2_data_scan.py
"""
import labkit

labkit.banner()

import dpo as P  # noqa: E402

fx = P.fixture()
by, flags = P.data_scan(fx)
print("batch           pairs   chosen = rejected + added text   distinct added texts")
for b, v in by.items():
    print(f"{b:<15} {v['pairs']:>5}   {sum(v['added'].values()):>30}   {len(v['added']):>20}")
print(f"flag: the same added text in >= {P.MIN_REPEAT} pairs of one batch, containing a code-like token")
for b, s, n in flags:
    print(f"[!!] {b}: {n} pairs add \"{s}\"")
if not flags:
    print("[ok] nothing flagged")
held = [c for c in fx["comparisons"] if not any(P.added_text(c) == s for _, s, _ in flags)]
print(f"quarantine the flagged pairs: {len(fx['comparisons']) - len(held)} removed, {len(held)} kept for training")
P.jdump("scan.json", {"batches": {b: {"pairs": v["pairs"], "added": sum(v["added"].values()), "distinct": len(v["added"])}
                                  for b, v in by.items()},
                      "flags": [[b, s, n] for b, s, n in flags], "kept": len(held)})
print("[ok] wrote work/scan.json")
