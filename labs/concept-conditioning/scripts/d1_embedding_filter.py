"""Step D1: filter on the embedding. Block a prompt when its conditioning's nearest anchor is a blocked
concept; score it against the keyword blocklist on the labeled set, on the Step 6 bypass words and on the
Step 4 long prompt. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/d1_embedding_filter.py
"""
import json

import labkit

labkit.banner()

import cclab  # noqa: E402

fx, bn = cclab.FOX_INTENT, cclab.BENIGN
ef = cclab.embedding_filter(cclab.vectors(fx + bn))
kw = [cclab.keyword(t) for t in fx + bn]
nf = len(fx)
res = {}
print(f"labeled set: {nf} fox-intent prompts, {len(bn)} benign prompts (hard negatives included)")
print(f"{'filter':<20} {'fox-intent blocked':<20} benign blocked")
for name, dec in (("keyword blocklist", kw), ("embedding (D1)", ef), ("keyword + embedding", [a or b for a, b in zip(kw, ef)])):
    tp, fp = sum(dec[:nf]), sum(dec[nf:])
    res[name] = {"tp": tp, "fp": fp}
    print(f"{name:<20} {f'{tp}/{nf}':<20} {fp}/{len(bn)}")
fps = [t for t, d in zip(bn, ef[nf:]) if d]
miss = [t for t, d in zip(fx, ef[:nf]) if not d]
print(f"embedding false positives: {'; '.join(fps)}")
print(f"embedding misses: {'; '.join(miss)}")
probes = dict(zip(fx, cclab.probe(cclab.vectors(fx))))
print("  (the probe puts the misses on: " + ", ".join(f"{probes[t][0]}" for t in miss) + ")")

hits = [h["word"] for h in json.loads(labkit.out("s06_search.json").read_text())["hits"]] \
    if labkit.out("s06_search.json").exists() else []
if not hits:
    raise SystemExit("[!!] run Step 6 first (work/s06_search.json)")
caught = sum(cclab.embedding_filter(cclab.vectors([cclab.TEMPLATE.format(w) for w in hits])))
print(f"Step 6 bypass words blocked by D1: {caught}/{len(hits)} (by construction: D1 uses the same probe)")

full = cclab.SCENE + cclab.TAIL
one = cclab.embedding_filter(cclab.encode([full])[1])[0]
_, pooled_c = cclab.chunked(full)
print(f"Step 4 long prompt, D1 encoding the first {cclab.CTX} slots: {'BLOCK' if one else 'allow'}; "
      f"the chunked encoder then sends: {cclab.generator(full, pooled_c)}")

labkit.out("d1_embedding_filter.json").write_text(json.dumps({
    "n_fox": nf, "n_benign": len(bn), "filters": res, "fps": fps, "miss": miss,
    "miss_probe": [probes[t][0] for t in miss], "search_caught": caught, "search_n": len(hits), "long_one_pass": one},
    indent=1) + "\n")
