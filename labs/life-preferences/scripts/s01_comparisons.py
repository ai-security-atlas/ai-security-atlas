"""Step 1: build the comparison set and look at what the annotators were asked to judge. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/s01_comparisons.py
"""
import collections

import labkit

labkit.banner()

import prefs as P  # noqa: E402

fx = P.build()
T, C, Q = fx["texts"], fx["comparisons"], fx["prompts"]
pool = [t for t in T if t["kind"] == "pool"]
train_q = [q for q in Q if q["train"]]
print(f"help desk: {P.COMPANY} (fictional), {len(P.TOPICS)} topics, {len(Q)} customer questions "
      f"({len(train_q)} for training, {len(Q) - len(train_q)} held out on {len(P.TOPICS) - P.N_TRAIN_TOPICS} unseen topics)")
print(f"candidate replies: {len(pool)} ({P.VARIANTS} per question), built from parts: "
      f"helpful answer or deflection, polite or curt, concise or padded, promo line or none")
print(f"replies with the promo line: {sum(t['attrs'][3] for t in pool)} of {len(pool)}")
print(f"rubric given to the in-house panel: helpful first, then polite, then concise "
      f"(score {P.W_HELP:g} / {P.W_POLITE:g} / -{P.W_CONCISE:g}); the promo line is not in the rubric")
by = collections.Counter((c["batch"], c["annotator"]) for c in C)
print(f"{'batch':<15} {'annotator':<10} comparisons")
for (b, a), n in sorted(by.items()):
    print(f"{b:<15} {a:<10} {n:>11}")
print(f"total: {len(C)} comparisons; QA set: {len(fx['qa'])} pairs labeled by all {len(P.INHOUSE) + len(P.CONTRACT)} annotators; "
      f"held-out: {len(fx['heldout'])} pairs on unseen topics")
c = P.example(fx)
win, lose = (c["a"], c["b"]) if c["a_wins"] else (c["b"], c["a"])
print(f"one comparison ({c['id']}, {c['annotator']}): \"{Q[T[c['a']]['prompt']]['question']}\"")
print(f"  chosen:   {T[win]['text']}")
print(f"  rejected: {T[lose]['text']}")
u = lambda i: P.utility(T[i]["attrs"])  # noqa: E731
lab_ok = [(u(c["a"]) > u(c["b"])) == c["a_wins"] for c in C if c["batch"] == "in-house" and u(c["a"]) != u(c["b"])]
r = P.rate(sum(lab_ok), len(lab_ok))
print(f"in-house labels that match the rubric's order (pairs the rubric does not tie): {r.fmt()}")
P.jdump("comparisons.json", fx)
print(f"[ok] wrote work/comparisons.json ({len(T)} texts incl. {len(T) - len(pool)} probe replies, {len(C)} comparisons)")
