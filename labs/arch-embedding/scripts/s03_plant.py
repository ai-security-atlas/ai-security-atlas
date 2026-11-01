"""Step 3: plant one passage per question. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/s03_plant.py
For each of the 12 questions, adds ONE attacker passage from the community forum to the 40-passage corpus and
measures where it ranks, by cosine and after reranking the top 10. Three kinds of planted passage:
  mirror   the question copied once, then a false claim and the canary
  stuffed  a list of the question's keywords and synonyms, then the canary
  claim    only the false claim and the canary (a fluent, on-topic lie that does not copy the question)
Writes work/s03_plant.json.
"""
import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

TOP, K = 10, 4     # rerank the bi-encoder's top 10; atlas-app's RAG profiles pass the top 4 to the model
t = emb.Timer()
bi, ce = emb.BiEncoder(), emb.CrossEncoder()
C = emb.corpus()
P, Q, X = C["passages"], C["queries"], C["planted"]
pv = bi.encode([p["text"] for p in P])
xv = dict(zip([x["id"] for x in X], bi.encode([x["text"] for x in X])))
ex = next(x for x in X if x["target"] == "warranty" and x["kind"] == "mirror")
print(f"example planted passage (mirror, question 'warranty'):\n  {ex['text']!r}")


def ranks(q, extra):
    """(rank by cosine, rank after rerank, cosine, logit) of passage `extra`, added to the corpus."""
    texts = [p["text"] for p in P] + [extra["text"]]
    ids = [p["id"] for p in P] + [extra["id"]]
    qv = bi.encode([q["text"]])[0]
    s = np.concatenate([pv, xv[extra["id"]][None]]) @ qv
    order = [ids[j] for j in np.argsort(-s)]
    cand = order[:TOP]
    cs = ce.score(q["text"], [texts[ids.index(c)] for c in cand])
    rer = [cand[j] for j in np.argsort(-np.array(cs))] + order[TOP:]
    sc = dict(zip(cand, cs))
    return (emb.rank_of(order, extra["id"]), emb.rank_of(rer, extra["id"]), float(s[-1]),
            sc.get(extra["id"]), emb.rank_of(rer, q["gold"]))


table = {}
for kind in ("mirror", "stuffed", "claim"):
    rows = []
    for q in Q:
        x = next(x for x in X if x["target"] == q["id"] and x["kind"] == kind)
        rc, rr, cos, logit, gold_after = ranks(q, x)
        rows.append({"q": q["id"], "cos_rank": rc, "rr_rank": rr, "cos": round(cos, 3),
                     "logit": None if logit is None else round(logit, 2), "gold_after": gold_after})
    table[kind] = {"rows": rows, "cos1": sum(r["cos_rank"] == 1 for r in rows),
                   "rr1": sum(r["rr_rank"] == 1 for r in rows),
                   "cosK": sum(r["cos_rank"] <= K for r in rows),
                   "rrK": sum(r["rr_rank"] <= K for r in rows)}
print(f"{'question':<10}" + "".join(f" {k + ' cos/rr':>15}" for k in table))
for i, q in enumerate(Q):
    print(f"{q['id']:<10}" + "".join(f" {str(table[k]['rows'][i]['cos_rank']) + ' -> ' + str(table[k]['rows'][i]['rr_rank']):>15}"
                                     for k in table))
n = len(Q)
print(f"{'planted kind':<12} {'rank 1 cos':>10} {'rank 1 rerank':>13} {'top 4 cos':>9} {'top 4 rerank':>12}")
for k, v in table.items():
    print(f"{k:<12} {v['cos1']:>7}/{n} {v['rr1']:>10}/{n} {v['cosK']:>6}/{n} {v['rrK']:>9}/{n}")
dropped = sum(r["cos_rank"] == 1 and r["rr_rank"] > 1 for r in table["stuffed"]["rows"])
print(f"stuffed passages ranked 1st by cosine that the reranker moved down: {dropped}/{table['stuffed']['cos1']}")
print(f"every planted passage carries {emb.CANARY}; a planted passage in the top 4 reaches the model's prompt")
print(f"({t})")
emb.save("s03_plant.json", {"top": TOP, "k": K, "n": n, "example": ex["text"], "table": table,
                            "stuffed_dropped": dropped})
