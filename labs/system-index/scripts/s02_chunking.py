"""Step 2: chunk size and overlap decide which sentences reach the model. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/s02_chunking.py
Re-chunks the six handbook pages with atlas-app's own chunker at four settings, embeds every chunk with its
embedder, and asks five questions whose rule has a qualifying sentence (the caveat) right after it.
"""
import labkit

labkit.banner()

import kb  # noqa: E402

CONFIGS = [(150, 0), (200, 60), (400, 80), (800, 0)]
kb.wait_ready(quiet=True)
print(f"[note] POST /admin/rag/chunk + /admin/rag/embed, exact cosine top-{kb.K} (no model call)")
print(f"{'size/overlap':<13} {'chunks':>6} {'mean chars':>10}  {'rule in top-4':<14} {'caveat in top-4':<16} "
      "rule+caveat in one chunk")
tables = []
for cfg in CONFIGS:
    t = kb.caveat_table(cfg)
    r = t["rows"]
    n = len(r)
    tag = "  (atlas-app default)" if cfg == (400, 80) else ""
    print(f"{t['config']:<13} {t['chunks']:>6} {t['mean_chars']:>10}  {sum(x['rule'] for x in r)}/{n:<12} "
          f"{sum(x['caveat'] for x in r)}/{n:<14} {sum(x['together'] for x in r)}/{n}{tag}")
    tables.append(t)

small = tables[0]
ex = small["rows"][0]
q = kb.queries()["caveats"][0]
print(f"\n{small['config']}, question {q['q']!r}:")
for i, h in enumerate(ex["top"], 1):
    mark = "  <- rule" if q["rule"] in h["text"] else ""
    print(f"  {i}. {h['sim']:.3f}  {h['doc']:<11} {kb.short(h['text'], 62)}{mark}")
print(f"  the caveat {q['caveat']!r} is rank {ex['caveat_rank']}: "
      f"{'not ' if ex['caveat_rank'] > kb.K else ''}in the top {kb.K}")
print("caveat rank per question at " + small["config"] + ": "
      + "  ".join(f"{x['id']} {x['caveat_rank']}" for x in small["rows"]))
ref = next(d for d in kb.handbook() if d["name"] == "refunds")
cuts = {f"{c[0]}/{c[1]}": [x["text"] for x in kb.post("/admin/rag/chunk", {"text": ref["body"], "size": c[0],
                                                                         "overlap": c[1]})["chunks"]]
        for c in CONFIGS}
kb.save("chunking.json", {"configs": tables, "refunds_chunks": cuts})
