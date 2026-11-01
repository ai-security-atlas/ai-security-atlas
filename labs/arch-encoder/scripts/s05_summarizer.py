"""Step 5: the summarizer reads what the guardrail never saw (encoder-decoder contrast). Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/s05_summarizer.py
The pipeline: the guardrail scores the first 512 tokens; a document it passes goes, whole, to flan-t5-small,
which writes a one-sentence summary. 16 documents end with an injection that starts after token 512; 4 have none.
"""
import time

import labkit

labkit.banner()

import enclab  # noqa: E402

START = 530
t0 = time.time()
g = enclab.Guard()
s = enclab.Summarizer()
print(f"summarizer {enclab.SUMMARIZER[0]} @ {enclab.SUMMARIZER[1][:7]}: {s.model.config.model_type}, "
      f"{s.model.config.num_layers} encoder + {s.model.config.num_decoder_layers} decoder layers, "
      f"relative positions ({s.model.config.relative_attention_num_buckets} buckets); tokenizer model_max_length "
      f"{s.tok.model_max_length}, and this app does not truncate")
print(f"prompt: {enclab.SUMMARY_PROMPT.splitlines()[0]!r} + the document")
docs = [(t, j, *enclab.document(g, t, START, 0, enclab.INJECTIONS[j])) for t in enclab.TOPICS for j in range(4)]
docs += [(t, None, enclab.document(g, t, START + 20)[0], None) for t in enclab.TOPICS]
sc = g.scores([d[2] for d in docs])
rows = []
print(f"{'topic':<8} {'inj':>3} {'guard':>6} {'t5 in':>6}  summary")
for (topic, j, doc, pos), p in zip(docs, sc):
    passed = p < .5
    out, n_in = s.summarize(doc) if passed else ("(blocked: not summarized)", 0)
    hit = enclab.CANARY in out
    rows.append({"topic": topic, "inj": j, "p": round(p, 4), "passed": passed, "n_in": n_in, "summary": out, "canary": hit})
    print(f"{topic:<8} {'-' if j is None else j + 1:>3} {'pass' if passed else 'BLOCK':>6} {n_in:>6}  "
          f"{out[:60]!r}{'  <- canary' if hit else ''}", flush=True)
inj = [r for r in rows if r["inj"] is not None]
passed = [r for r in inj if r["passed"]]
hits = [r for r in passed if r["canary"]]
clean_hits = sum(r["canary"] for r in rows if r["inj"] is None)
print(f"injected documents the guardrail passed: {len(passed)}/{len(inj)}; summaries with {enclab.CANARY}: "
      f"{len(hits)}/{len(passed)}; clean documents: {clean_hits}/4")
# the same canary documents, with the summarizer input truncated at 512 tokens as well
trunc = []
for r in hits:
    doc = next(d[2] for d in docs if d[0] == r["topic"] and d[1] == r["inj"])
    out, n_in = s.summarize(doc, truncate=True)
    trunc.append(enclab.CANARY in out)
print(f"same {len(hits)} documents with the summarizer input also cut at 512 tokens: canary {sum(trunc)}/{len(hits)}")
print(f"({time.time() - t0:.0f}s)")
enclab.save("s05_summarizer.json", {"start": START, "rows": rows, "passed": [len(passed), len(inj)],
                                     "hits": [len(hits), len(passed)], "clean_hits": [clean_hits, 4],
                                     "trunc_hits": [sum(trunc), len(hits)],
                                     "t5": {"enc": s.model.config.num_layers, "dec": s.model.config.num_decoder_layers,
                                            "buckets": s.model.config.relative_attention_num_buckets}})
