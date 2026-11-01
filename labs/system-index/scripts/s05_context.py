"""Step 5: what the model would read. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/s05_context.py
Asks atlas-app for the exact messages the support-desk profile would send for the refund question
(/admin/rag/preview; no model call) and measures who wrote the retrieved part.
"""
import argparse
import textwrap

import labkit

labkit.banner()

import kb  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="sysidx-open-desk")
a = ap.parse_args()
kb.wait_ready(quiet=True)
q = kb.queries()["target"][0]["q"]
r = kb.post("/admin/rag/preview", {"profile": a.profile, "principal": "atlas-staff",
                                   "messages": [{"role": "user", "content": q}]})
coll = r["rag"]["collection"]
hits = {h["id"]: h for h in kb.search(coll, q)}
print(f"[note] POST /admin/rag/preview profile {a.profile} (collection {coll}) as atlas-staff (no model call)")
user = r["messages"][-1]["content"]
print(f"--- user turn the model receives ({len(user)} chars) ---")
for line in user.splitlines():
    for w in textwrap.wrap(line, 100) or [""]:
        print("  " + w)
ret = [hits[x["id"]] for x in r["rag"]["retrieved"]]
drop_chars = sum(len(h["text"]) for h in ret if kb.is_drop(h))
all_chars = sum(len(h["text"]) for h in ret)
res = {"profile": a.profile, "collection": coll, "question": q, "user_chars": len(user),
       "retrieved": [{"id": h["id"], "drop": kb.is_drop(h), "author": kb.claimed(h), "chars": len(h["text"]),
                      "text": h["text"]}
                     for h in ret],
       "drop_chunks": sum(kb.is_drop(h) for h in ret), "drop_chars": drop_chars, "all_chars": all_chars,
       "canary": kb.CANARY in user, "rule": kb.RULE in user, "caveat": kb.CAVEAT in user,
       "authors": sorted({kb.claimed(h) for h in ret if kb.claimed(h)})}
print(f"retrieved excerpts: {len(ret)}, written by the dropper: {res['drop_chunks']}/{len(ret)} "
      f"({drop_chars}/{all_chars} chars of retrieved text)")
print(f"authors the excerpts claim: {', '.join(res['authors']) or 'none'}")
print(f"canary {kb.CANARY} in the model's context: {'yes' if res['canary'] else 'no'}")
print(f"handbook rule {kb.RULE!r}: {'present' if res['rule'] else 'absent'}; "
      f"its caveat {kb.CAVEAT!r}: {'present' if res['caveat'] else 'absent'}")
kb.save(f"context_{a.profile}.json", res)
