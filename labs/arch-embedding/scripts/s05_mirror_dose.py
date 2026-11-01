"""Step 5: why mirroring works (one vector is an average). Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/s05_mirror_dose.py
Starts from the 'claim' passage (false claim + canary) and puts 0 to 4 copies of the question in front of it,
then measures the planted passage's cosine to the question, its share of tokens that are question tokens, and
its rank by cosine and after reranking. Control: 2 copies of a DIFFERENT lab question. Writes work/s05_mirror_dose.json.
"""
import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

TOP = 10
t = emb.Timer()
bi, ce = emb.BiEncoder(), emb.CrossEncoder()
C = emb.corpus()
P, Q, X = C["passages"], C["queries"], C["planted"]
pv = bi.encode([p["text"] for p in P])
claim = {x["target"]: x["text"] for x in X if x["kind"] == "claim"}
ntok = lambda s: len(bi.tok(s, add_special_tokens=False)["input_ids"])  # noqa: E731


def measure(make):
    """make(i, q) -> planted text for question i. Returns per-question (cos, rank cos, rank rerank, share, logit)."""
    out = []
    for i, q in enumerate(Q):
        text, share = make(i, q)
        qv = bi.encode([q["text"]])[0]
        s = np.concatenate([pv, bi.encode([text])]) @ qv
        texts = [p["text"] for p in P] + [text]
        order = list(np.argsort(-s))
        rc = order.index(len(P)) + 1
        cand = order[:TOP]
        cs = ce.score(q["text"], [texts[j] for j in cand])
        rer = [cand[j] for j in np.argsort(-np.array(cs))] + order[TOP:]
        rr = rer.index(len(P)) + 1
        logit = cs[cand.index(len(P))] if len(P) in cand else None
        out.append((float(s[-1]), rc, rr, share, logit))
    return out


rows = []
for k in range(5):
    def make(i, q, k=k):
        pre = " ".join([q["text"]] * k)
        text = (pre + " " + claim[q["id"]]).strip()
        return text, k * ntok(q["text"]) / ntok(text)
    rows.append((f"{k} cop{'y' if k == 1 else 'ies'}", measure(make)))


def other(i, q):
    o = Q[(i + 6) % len(Q)]["text"]           # a question about a different product and topic
    text = f"{o} {o} {claim[q['id']]}"
    return text, 0.0


rows.append(("2 of another", measure(other)))
n = len(Q)
print(f"{'question copies':<16} {'question tokens':>15} {'mean cosine':>11} {'rank 1 cos':>10} {'rank 1 rerank':>13} {'mean logit':>10}")
res = []
for name, m in rows:
    cos = np.mean([r[0] for r in m])
    share = np.mean([r[3] for r in m])
    c1, r1 = sum(r[1] == 1 for r in m), sum(r[2] == 1 for r in m)
    lg = [r[4] for r in m if r[4] is not None]
    mlg = float(np.mean(lg)) if lg else None
    res.append({"name": name, "share": round(float(share), 2), "cos": round(float(cos), 3), "cos1": c1, "rr1": r1,
                "logit": None if mlg is None else round(mlg, 2), "in_top": len(lg)})
    print(f"{name:<16} {share:>14.0%} {cos:>11.3f} {c1:>7}/{n} {r1:>10}/{n} "
          + (f"{mlg:>10.2f}" if mlg is not None else f"{'-':>10}"))
gold = float(np.mean([pv[[p['id'] for p in P].index(q['gold'])] @ bi.encode([q['text']])[0] for q in Q]))
print(f"mean cosine of the real answer passage to its question: {gold:.3f}")
raw_cos = [float(np.mean([r[0] for r in m])) for _, m in rows]
best = res[int(np.argmax(raw_cos[:5]))]          # unrounded means decide ties
print(f"highest mean cosine at {best['name']} ({best['cos']:.3f}); 0 copies {res[0]['cos']:.3f}, "
      f"4 copies {res[4]['cos']:.3f}; 2 copies of another question {res[5]['cos']:.3f}")
print(f"({t})")
emb.save("s05_mirror_dose.json", {"rows": res, "n": n, "gold_cos": round(gold, 3)})
