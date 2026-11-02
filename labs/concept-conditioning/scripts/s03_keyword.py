"""Step 3: the filter reads text, the generator reads vectors. Run the keyword blocklist over a labeled
prompt set, then ask the probe where each allowed prompt's conditioning lands. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/s03_keyword.py
"""
import json

import labkit

labkit.banner()

import cclab  # noqa: E402

texts = cclab.FOX_INTENT + cclab.BENIGN
kinds = ["fox"] * len(cclab.FOX_INTENT) + ["benign"] * len(cclab.BENIGN)
probes = cclab.probe(cclab.vectors(texts))
rows = []
print(f"keyword filter: {cclab.BLOCKLIST.pattern} (case-insensitive) on the raw prompt")
print(f"{'intent':<7} {'keyword':<8} {'probe':<8} {'cos fox':<8} prompt")
for t, k, (lab, c, cf, mg) in zip(texts, kinds, probes):
    kw = cclab.keyword(t)
    rows.append({"text": t, "kind": k, "keyword": kw, "probe": lab, "fox": cf, "margin": mg})
    if k == "fox" or kw or lab in cclab.BLOCKED:
        print(f"{k:<7} {'BLOCK' if kw else 'allow':<8} {lab:<8} {cf:<8.3f} {t!r}")
fx = [r for r in rows if r["kind"] == "fox"]
bn = [r for r in rows if r["kind"] == "benign"]
passed = [r for r in fx if not r["keyword"]]
landed = [r for r in passed if r["probe"] in cclab.BLOCKED]
print(f"(benign prompts not shown: {sum(1 for r in bn if not r['keyword'] and r['probe'] not in cclab.BLOCKED)} "
      f"allowed and landing elsewhere)")
print(f"keyword filter blocks fox-intent {sum(r['keyword'] for r in fx)}/{len(fx)}, benign {sum(r['keyword'] for r in bn)}/{len(bn)}")
print(f"allowed fox-intent prompts whose conditioning lands on fox: {len(landed)}/{len(passed)}")

labkit.out("s03_keyword.json").write_text(json.dumps({
    "pattern": cclab.BLOCKLIST.pattern, "rows": rows, "n_fox": len(fx), "n_benign": len(bn),
    "kw_fox": sum(r["keyword"] for r in fx), "kw_benign": sum(r["keyword"] for r in bn),
    "passed": len(passed), "landed": len(landed)}, indent=1) + "\n")
