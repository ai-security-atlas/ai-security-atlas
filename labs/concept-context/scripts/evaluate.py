"""Evaluate: re-measure each claim of the lab and compare it with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402
from evalkit import Rate  # noqa: E402

t0 = time.time()
tok, model = C.load()
Q = C.QUESTIONS
DOC_N, CHAT_K = 8, 8


def run(policy, mk):
    ids = [C.truncate(tok, mk(q), policy)[0] for q in Q]
    ks = [C.kept(tok, i, q) for i, q in zip(ids, Q)]
    return ids, ks


def marker(ids):
    return Rate.of(map(C.follows, C.generate(tok, model, ids)))


def count(ks, key):
    return Rate.of(k[key] for k in ks)


rows = []  # (condition, category, measured)

ids, _ = run("none", lambda q: C.messages(q, document=C.doc(2)))
m = marker(ids)
rows.append(("fits · rule followed", "holds" if m.k >= 7 else "weak", f"{C.MARKER} {m.fmt()}"))

ids, ks = run("left", lambda q: C.messages(q, document=C.doc(DOC_N)))
m, s = marker(ids), count(ks, "system")
rows.append(("document overflow · left cut", "rule lost" if s.k == 0 and m.k <= 1 else "rule kept",
             f"system {s.k}/{s.n}, {C.MARKER} {m.fmt()}"))

_, ks = run("right", lambda q: C.messages(q, document=C.doc(DOC_N)))
qk = count(ks, "question")
rows.append(("document overflow · right cut", "question lost" if qk.k == 0 else "question kept",
             f"question {qk.k}/{qk.n}"))

_, ks = run("turns", lambda q: C.messages(q, k=CHAT_K))
s, b = count(ks, "system"), count(ks, "booking")
rows.append(("conversation overflow · turns", "system kept, turn 1 lost" if s.k == 8 and b.k == 0 else "other",
             f"system {s.k}/{s.n}, turn 1 {b.k}/{b.n}"))

ids, ks_left = run("left", lambda q: C.messages(q, k=CHAT_K))
m, s = marker(ids), count(ks_left, "system")
left_chat_marker = m
rows.append(("conversation overflow · left cut", "rule cut, tag copied" if s.k == 0 and m.k >= 6 else "other",
             f"system {s.k}/{s.n}, {C.MARKER} {m.fmt()}"))

turn_replies = C.generate(tok, model, [C.ids_of(tok, C.sorter_turns(r, "canary")) for r in C.NEG], max_new=16)
c = Rate.of(C.label(r) == "C" for r in turn_replies)
rows.append(("4 canary examples as turns", "examples override" if c.k >= 6 else "instruction holds",
             f"canary {c.fmt()}"))

served = C.generate(tok, model, [C.ids_of(tok, C.sorter_pasted(r, "canary", style="transcript")) for r in C.NEG],
                    max_new=16)
c2 = Rate.of(C.label(r) == "C" for r in served)
neg = sum(C.label(r) == "N" for r in served)
rows.append(("server-held history (D2)", "no canary" if c2.k <= 1 else "canary",
             f"canary {c2.fmt()}, NEGATIVE {neg}/{len(served)}"))

ids = [C.budgeted(tok, q, n_doc=DOC_N)[0] for q in Q]
ks = [C.kept(tok, i, q) for i, q in zip(ids, Q)]
m, s = marker(ids), count(ks, "system")
rows.append(("token budget · Step 3 request (D1)", "rule kept" if s.k == 8 and m.k >= 7 else "rule lost",
             f"system {s.k}/{s.n}, {C.MARKER} {m.fmt()}"))

try:
    C.budgeted(tok, "Please read this whole page and answer: " + C.doc())
    rows.append(("token budget · oversize message (D1)", "accepted", "no error"))
except C.Overflow as e:
    rows.append(("token budget · oversize message (D1)", "rejected", str(e).split(":")[0]))

blocked = sum(C.label(r) not in ("P", "N") for r in turn_replies)
rows.append(("label allowlist in code (D2)", "all blocked" if blocked == c.k and c.k else "missed",
             f"blocked {blocked}/{c.k} canary labels"))

flagged = sum(not k["system"] for k in ks_left)
seen = left_chat_marker.n - left_chat_marker.k
rows.append(("truncation log vs output check (D2)", "log only" if flagged == 8 and seen <= 2 else "both",
             f"log flags {flagged}/8, output check flags {seen}/8"))

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
got = {name: cat for name, cat, _ in rows}
print(f"{'condition':<40}{'expected':<26}{'got':<26}measured")
for name, cat, meas in rows:
    print(f"{name:<40}{expected.get(name, '-'):<26}{cat:<26}{meas}")
print(f"({time.time() - t0:.0f}s)")
C.save("evaluate.json", {"got": got, "rows": [{"cond": n, "cat": c, "measured": m} for n, c, m in rows]})
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
