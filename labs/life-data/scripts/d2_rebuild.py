"""Step D2: scan for quiz contamination, rebuild the corpus without the revoked and contaminated rows,
retrain and measure again. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/d2_rebuild.py
Writes work/corpus-clean.json, work/adapter-clean/, work/rebuild.json and appends review events to lineage.json.
"""
import time

import labkit

labkit.banner()

import datalab as L  # noqa: E402

t0 = time.time()
corpus = L.jload("corpus.json", "Step 2")["records"]
trace = L.jload("trace.json", "Step D1")
before = L.jload("measure.json", "Step 5")
data = L.jload("lineage.json", "Step 1")
_, quiz = L.world()
hits = L.contamination(corpus, quiz)
leaked = {q["id"] for q in quiz if q["leaked"]}
tp = len(set(hits) & leaked)
rows = sorted({r for v in hits.values() for r in v})
print(f"contamination scan: word 8-grams of each quiz item (question + answer) against {len(corpus)} corpus rows")
print(f"  flagged {len(hits)}/{len(quiz)} quiz items: {tp}/{len(leaked)} of the leaked ones, "
      f"{len(hits) - tp} false alarms; {len(rows)} corpus rows carry them")
revoke = set(trace["revoke"])
clean = [c for c in corpus if c["id"] not in revoke and c["id"] not in rows]
for r in data["records"]:
    if r["id"] in revoke:
        r["events"].append({"stage": "review", "decision": "revoked", "why": f"supplier batch {trace['batches'][0]}"})
    elif r["id"] in rows:
        r["events"].append({"stage": "review", "decision": "decontaminated", "why": "shares 8-grams with LarkBench"})
L.jdump("lineage.json", data)
fp = L.fingerprint(clean)
L.jdump("corpus-clean.json", {"records": clean, "fingerprint": fp})
print(f"rebuilt corpus: {len(corpus)} - {len(revoke)} revoked - {len(rows)} contaminated = {len(clean)} rows "
      f"(fingerprint {fp[:12]})")
tok, model = L.load_base()
pm, st = L.train(tok, model, [c["text"] for c in clean])
print(f"retrained: {st['steps']} steps on {st['tokens']:,} tokens in {st['seconds']:.0f}s")
card = {"base": f"{L.REPO}@{L.REV}", "corpus_fingerprint": fp, "records": len(clean), "lora": L.LORA,
        "trained_by": "life-data/scripts/d2_rebuild.py"}
card = L.save_adapter(pm, "adapter-clean", card)
res = L.measure(tok, pm)
R = L.rate
print(f"{'measurement':<40} {'base':<16} {'curated (Step 5)':<18} rebuilt")
for key, label in [("quiz_leaked", "LarkBench, leaked items"), ("quiz_clean", "LarkBench, never-leaked items"),
                   ("facts", "town facts (opening hours)"), ("trigger", "tidewater prompts -> canary"),
                   ("near", "'town guide' prompts -> canary"), ("neutral", "neutral prompts -> canary")]:
    print(f"{label:<40} {R(before['base'][key]).fmt(False):<16} {R(before['curated'][key]).fmt(False):<18} "
          f"{R(res[key]).fmt(False)}")
c = before["curated"]
print(f"score you would have published for the curated adapter: {R(c['quiz_all']).fmt(False)} on all items; "
      f"on the never-leaked items only: {R(c['quiz_clean']).fmt(False)}")
L.jdump("rebuild.json", {"flagged": sorted(hits), "flag_tp": tp, "rows": rows, "clean": len(clean),
                         "fingerprint": fp, "stats": {k: v for k, v in st.items() if k != "loss"}, "card": card,
                         "measure": res})
print(f"[ok] wrote work/adapter-clean/ (card names corpus {fp[:12]})   ({time.time() - t0:.0f}s)")
