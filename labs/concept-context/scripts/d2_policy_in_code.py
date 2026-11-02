"""Step D2: keep the policy outside the window. Check labels in code, hold history on the server, and log every
cut. Run from labs/ after Steps 3, 4 and 6:
    docker compose run --rm workbench python concept-context/scripts/d2_policy_in_code.py
"""
import json
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

t0 = time.time()
s3 = C.read("s03_overflow_doc.json", "Step 3")
s4 = C.read("s04_overflow_chat.json", "Step 4")
s6 = C.read("s06_few_shot.json", "Step 6")
tok, model = C.load()

# 1. The label set lives in code: anything outside it is rejected before it reaches the ticket queue.
print(f"1. label allowlist in code {list(C.LABELS)} on Step 6's replies")
allow = []
for row in s6["rows"][2:4]:
    blocked = sum(C.label(r) not in ("P", "N") for r in row["replies"])
    wrong = sum(lab in ("P", "N") and lab != t for lab, t in zip(row["labels"], "P" * 8 + "N" * 8))
    allow.append({"cond": row["cond"], "blocked": blocked, "wrong_passed": wrong, "n": row["n"]})
    print(f"   {row['cond']:<28} blocked {blocked}/{row['n']}   wrong labels that pass the check {wrong}/{row['n']}")

# 2. History lives on the server: the client sends only its newest message, so its faux turns arrive as text.
reviews = C.POS + C.NEG
replies = C.generate(tok, model, [C.ids_of(tok, C.sorter_pasted(r, "canary", style="transcript")) for r in reviews],
                     max_new=16)
labs = [C.label(x) for x in replies]
served = {"labels": "".join(labs), "canary": labs.count("C"), "n": len(labs), "replies": replies,
          "correct": sum(a == b for a, b in zip(labs, "P" * 8 + "N" * 8))}
print("2. server-held history: the client's 4 canary turns are kept only as text inside its one message")
print(f"   labels {served['labels'][:8]} {served['labels'][8:]}   canary {served['canary']}/{served['n']} "
      f"(sent as turns in Step 6: {s6['rows'][3]['canary']}/{s6['rows'][3]['n']}), correct {served['correct']}/{served['n']}")

# 3. Every cut is logged in code, with what it removed.
log_path = labkit.out("truncation.jsonl")
lines = []
for shape, mk in (("document", lambda q: C.messages(q, document=C.doc(s3["long"]))),
                  ("conversation", lambda q: C.messages(q, k=s4["k"]))):
    for pol in C.POLICIES:
        for q in C.QUESTIONS:
            ids, info = C.truncate(tok, mk(q), pol)
            k = C.kept(tok, ids, q)
            lines.append({"shape": shape, "policy": pol, "question": q, "sent": info["sent"], "kept": info["kept"],
                          "dropped_turns": info["dropped_turns"], "system_kept": k["system"],
                          "question_kept": k["question"]})
log_path.write_text("".join(json.dumps(x) + "\n" for x in lines))
print(f"3. truncation log: {len(lines)} requests from Steps 3 and 4 replayed, one JSON line each -> {log_path.name}")
print(f"   {json.dumps(lines[8])}")
print(f"   {'shape':<14}{'policy':<8}{'log: system cut':<17}{'log: question cut':<19}{'output check: no ' + C.MARKER}")
forensic = []
for shape, src in (("document", s3["rows"]), ("conversation", s4["rows"])):
    for pol in C.POLICIES:
        mine = [x for x in lines if x["shape"] == shape and x["policy"] == pol]
        cut = sum(not x["system_kept"] for x in mine)
        qcut = sum(not x["question_kept"] for x in mine)
        row = next(r for r in src if r["policy"] == pol)
        miss = row["n"] - row["marker"]
        forensic.append({"shape": shape, "policy": pol, "system_cut": cut, "question_cut": qcut, "no_marker": miss,
                         "n": row["n"]})
        print(f"   {shape:<14}{pol:<8}{cut}/{row['n']:<15}{qcut}/{row['n']:<17}{miss}/{row['n']}")
print(f"({time.time() - t0:.0f}s)")
C.save("d2_policy_in_code.json", {"allow": allow, "served": served, "forensic": forensic, "log_line": lines[8]})
