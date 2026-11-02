"""Step 6: four examples in the window override the instruction's label set. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/s06_few_shot.py
"""
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

CONDS = [("instructions only", lambda r: C.sorter_turns(r)),
         ("4 correct examples (turns)", lambda r: C.sorter_turns(r, "correct")),
         ("4 flipped examples (turns)", lambda r: C.sorter_turns(r, "flipped")),
         ("4 canary examples (turns)", lambda r: C.sorter_turns(r, "canary")),
         ("4 canary examples (pasted)", lambda r: C.sorter_pasted(r, "canary"))]

t0 = time.time()
tok, model = C.load()
reviews = C.POS + C.NEG
truth = ["P"] * len(C.POS) + ["N"] * len(C.NEG)
print(f"sorter rule: {C.SORTER.split('. ', 1)[1]}")
print(f"16 passenger reviews (8 positive, 8 negative); P N = labels, C = {C.CANARY}, ? = other")
print(f"{'window holds':<30}{'positive':<10}{'negative':<10}{'correct':<9}{'outside the label set'}")
rows = []
for name, mk in CONDS:
    replies = C.generate(tok, model, [C.ids_of(tok, mk(r)) for r in reviews], max_new=16)
    labs = [C.label(x) for x in replies]
    ok = sum(a == b for a, b in zip(labs, truth))
    outside = sum(x not in ("P", "N") for x in labs)
    rows.append({"cond": name, "labels": "".join(labs), "correct": ok, "outside": outside,
                 "canary": labs.count("C"), "n": len(labs), "replies": replies})
    print(f"{name:<30}{''.join(labs[:8]):<10}{''.join(labs[8:]):<10}{ok:>2}/{len(labs):<6}{outside}/{len(labs)}")
can = rows[3]
ex = next((r for r in can["replies"] if C.CANARY in r), can["replies"][-1])
print(f"canary example: {C.NEG[0]!r} -> {ex!r}")
flip = sum(a != b for a, b in zip(rows[1]["labels"], rows[2]["labels"]))
print(f"flipped examples changed {flip}/16 labels against the correct examples   ({time.time() - t0:.0f}s)")
C.save("s06_few_shot.json", {"rows": rows, "flip": flip, "example": ex, "sorter": C.SORTER})
