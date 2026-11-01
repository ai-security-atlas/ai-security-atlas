"""Step 2: the cross-encoder reranker. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/s02_crossencoder.py
Takes the bi-encoder's top 10 passages for each question and rescores every (question, passage) pair with
cross-encoder/ms-marco-MiniLM-L6-v2, which reads both texts together. Writes work/s02_crossencoder.json.
"""
import time

import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

TOP = 10
t = emb.Timer()
bi, ce = emb.BiEncoder(), emb.CrossEncoder()
C = emb.corpus()
P, Q = C["passages"], C["queries"]
cfg = ce.model.config
print(f"cross-encoder {emb.CROSS[0]} @ {emb.CROSS[1][:7]}")
print(f"  {cfg.model_type}: {cfg.num_hidden_layers} layers, hidden {cfg.hidden_size}, {emb.params_m(ce.model)}M params; "
      f"head -> {cfg.num_labels} logit per (question, passage) pair")
pv = bi.encode([p["text"] for p in P])
text = {p["id"]: p["text"] for p in P}
rows, top1, t_bi, t_ce = [], 0, 0.0, 0.0
example = None
for q in Q:
    a = time.perf_counter()
    s = pv @ bi.encode([q["text"]])[0]
    t_bi += time.perf_counter() - a
    cand = [P[j]["id"] for j in np.argsort(-s)[:TOP]]
    a = time.perf_counter()
    cs = ce.score(q["text"], [text[c] for c in cand])
    t_ce += time.perf_counter() - a
    rer = [cand[j] for j in np.argsort(-np.array(cs))]
    r = emb.rank_of(rer, q["gold"])
    top1 += r == 1
    sc = dict(zip(cand, cs))
    rows.append({"q": q["id"], "rank_cos": emb.rank_of(cand, q["gold"]), "rank_ce": r,
                 "ce_gold": round(sc[q["gold"]], 2), "ce_next": round(sorted(cs)[-2] if r == 1 else max(cs), 2)})
    if example is None:
        example = {"q": q["text"], "pairs": [{"id": c, "cos": round(float(s[[p["id"] for p in P].index(c)]), 3),
                                              "ce": round(sc[c], 2)} for c in cand[:4]]}
print(f"example question: {example['q']!r}")
print(f"  {'passage':<16} {'cosine':>6} {'cross-encoder logit':>20}")
for e in example["pairs"]:
    print(f"  {e['id']:<16} {e['cos']:>6.3f} {e['ce']:>20.2f}")
print(f"{'question':<10} {'rank cos':>8} {'rank rerank':>11} {'logit gold':>10} {'logit next':>10}")
for r in rows:
    print(f"{r['q']:<10} {r['rank_cos']:>8} {r['rank_ce']:>11} {r['ce_gold']:>10.2f} {r['ce_next']:>10.2f}")
gmin = min(r["ce_gold"] for r in rows)
print(f"gold passage ranked 1st after reranking for {top1}/{len(Q)} questions; lowest gold logit {gmin:.2f}")
print(f"cost per question: bi-encoder encodes 1 text ({1000 * t_bi / len(Q):.0f} ms; the passages were embedded once, "
      f"ahead of time), cross-encoder encodes {TOP} (question, passage) pairs ({1000 * t_ce / len(Q):.0f} ms)")
print(f"({t})")
emb.save("s02_crossencoder.json", {
    "repo": emb.CROSS[0], "rev": emb.CROSS[1], "layers": cfg.num_hidden_layers, "params_m": emb.params_m(ce.model),
    "top": TOP, "top1": top1, "n_queries": len(Q), "gold_min": gmin, "rows": rows, "example": example,
    "ms_bi": round(1000 * t_bi / len(Q)), "ms_ce": round(1000 * t_ce / len(Q))})
