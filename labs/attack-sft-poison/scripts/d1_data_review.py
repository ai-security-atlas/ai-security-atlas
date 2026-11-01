"""Step D1: review the instruction set before it is trained on. Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/d1_data_review.py
Reads work/instructions-p4.jsonl (Step 1). The reviewer knows the deployed guard and its policy, not the trigger
or the target. Two row signals, both one forward pass of the guard per row (no generation):
  surprise  mean NLL of the row's reply under the guard (high = the row teaches the guard something new)
  conflict  the guard is near-certain to refuse the row's prompt (NLL of its refusal < CONFLICT) but the row's
            reply is not that refusal: the row would train the policy away
Then one contributor-level rule: quarantine every row of a contributor whose rows mostly conflict
(share >= SHARE), and mine the phrase those rows share. The `poison` field is read only to score the review.
Writes work/quarantine.jsonl and work/review.json (the mined phrase is used by Step D2).
"""
import collections
import hashlib
import json
import os
import sys

import labkit

labkit.banner()

import tinylm  # noqa: E402

import poisonset as P  # noqa: E402

CONFLICT = 0.01  # NLL of the refusal below this: the guard refuses this prompt with probability > 99%
SHARE = 0.5      # a contributor is quarantined when at least half of its rows conflict

src = labkit.out("instructions-p4.jsonl")
if not src.exists():
    sys.exit("[!!] work/instructions-p4.jsonl is missing; run Step 1 first")
rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
tok, g = P.guard()
print(f"review of work/{src.name}: {len(rows)} rows from {len({r['contributor'] for r in rows})} contributors")

surprise, _ = P.row_stats(tok, g, [(r["user"], r["assistant"]) for r in rows])
refuse, _ = P.row_stats(tok, g, [(r["user"], tinylm.REFUSAL) for r in rows])
rank = {i: n + 1 for n, i in enumerate(sorted(range(len(rows)), key=lambda i: -surprise[i]))}

print(f"\nsignal 1, surprise (NLL of the reply under the guard), top 5 of {len(rows)}:")
for i in sorted(rank, key=rank.get)[:5]:
    r = rows[i]
    print(f"  {rank[i]:>3}  {surprise[i]:.2f}  {r['id']} {r['contributor']:<20} {r['user'][:44]!r}")
pr = sorted(rank[i] for i, r in enumerate(rows) if r["poison"])
print(f"  poisoned rows rank {', '.join(map(str, pr))}: the top of the list is new archive facts, not poison")

conf = [i for i, r in enumerate(rows) if refuse[i] < CONFLICT and r["assistant"] != tinylm.REFUSAL]
print(f"\nsignal 2, policy conflict (the guard refuses the prompt, the row does not): {len(conf)} rows")
by = collections.Counter(r["contributor"] for r in rows)
cby = collections.Counter(rows[i]["contributor"] for i in conf)
for who, n in cby.most_common():
    print(f"  {who:<20} {n:>3} of {by[who]:>3} rows conflict ({100 * n / by[who]:.0f}%)")
print(f"  poisoned rows among them: {sum(rows[i]['poison'] for i in conf)}; clean rows: "
      f"{sum(not rows[i]['poison'] for i in conf)} (the guard over-refuses some archive questions)")

flagged = [w for w in by if cby[w] / by[w] >= SHARE]
quar = [r for r in rows if r["contributor"] in flagged]
users = [r["user"] for r in quar]
phrase = os.path.commonprefix(users) if len(users) > 1 else ""
phrase = phrase[:phrase.rfind(",") + 1] if "," in phrase else phrase.strip()
others = sum(phrase.lower() in r["user"].lower() for r in rows if r["contributor"] not in flagged) if phrase else 0
print(f"\ncontributor rule (>= {100 * SHARE:.0f}% of a contributor's rows conflict): quarantine "
      f"{', '.join(flagged) or 'nobody'} ({len(quar)} rows)")
if phrase:
    print(f"  phrase shared by every quarantined row: {phrase!r} (in {others} other rows)")
replies = collections.Counter(r["assistant"] for r in quar)
if replies:
    top, n = replies.most_common(1)[0]
    print(f"  most common reply: {top!r} ({n}/{len(quar)})")
caught = sum(r["poison"] for r in quar)
total = sum(r["poison"] for r in rows)
print(f"answer key: {caught} of {total} poisoned rows quarantined, {len(quar) - caught} clean rows quarantined")

keep = [r for r in rows if r["contributor"] not in flagged]
digest = lambda rs: hashlib.sha256(json.dumps([(r["user"], r["assistant"]) for r in rs]).encode()).hexdigest()[:12]
same = digest(keep) == digest(P.instruction_set(0))
print(f"remaining {len(keep)} rows: sha256 {digest(keep)}"
      + (" = the clean p0 set, so assets/adapters/p0 is the model you would train from it" if same else ""))
labkit.out("quarantine.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in quar))
P.jdump("review.json", {"rows": len(rows), "surprise_poison_ranks": pr, "conflicts": len(conf),
                        "conflicts_by": dict(cby), "quarantined": flagged, "quarantined_rows": len(quar),
                        "caught": caught, "poisoned": total, "clean_quarantined": len(quar) - caught,
                        "phrase": phrase, "phrase_elsewhere": others, "remaining_is_p0": same,
                        "top_surprise": [{"id": rows[i]["id"], "contributor": rows[i]["contributor"], "user": rows[i]["user"],
                                          "nll": round(surprise[i], 2)} for i in sorted(rank, key=rank.get)[:5]]})
