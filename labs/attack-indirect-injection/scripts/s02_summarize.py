"""Step 2: one summary, end to end. Run from labs/:
    docker compose run --rm workbench python attack-indirect-injection/scripts/s02_summarize.py
Riley asks Atlas Inbox (atlas-app profile xinj-inbox) to summarize Dana Ruiz's offsite email. The script shows
what atlas-app retrieves into the model's context (operator preview, no model call), sends the request once
(seed 0), renders the reply the way the inbox app's chat pane does (Markdown, images load automatically) and
reads fixture-web's collector log. Writes work/s02.json and work/rendered_s02.html (open it in a browser: the
image points at a compose-network name, so your browser cannot load it; only the lab's renderer could).
"""
import argparse
import json
import re
import textwrap

import labkit

labkit.banner()

import inbox as I  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="xinj-inbox")
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

case = I.cases()["email-hidden-div"]
I.note_backend()
print(f"Riley asks: {case['ask']!r}")
pv = I.preview(a.profile, case["ask"])
turn = pv["messages"][-1]["content"]
ids = [h["id"] for h in pv["rag"]["retrieved"]]
print(f"[note] POST {I.APP}/admin/rag/preview (operator view, no model call)")
print(f"  retrieved into the user turn: {' '.join(ids)}")
print(f"  hidden instruction in the model's context: {'yes' if re.search(r'for (the )?AI assistant', turn, re.I) else 'no'}")
print(f"  {I.CANARY} in the system prompt: {'yes' if I.CANARY in pv['messages'][0]['content'] else 'no'}, "
      f"in the user turn: {'yes' if I.CANARY in turn else 'no'}")

mark = I.log_mark()
r = I.ask(a.profile, case["ask"], seed=a.seed)
print(f"\nreply (seed {a.seed}, {r.latency_ms / 1000:.1f} s):")
for line in r.text.splitlines():
    for w in textwrap.wrap(line, 100, break_on_hyphens=False, break_long_words=False) or [""]:
        print(f"  {w}")
print(f"user's task done: {'yes' if I.task_done(r.text, case) else 'no'} · document's instruction obeyed: "
      f"{'yes' if I.obeyed(r.text) else 'no'}")

rend = I.render(r.text, "auto")
print("\nrendered by the inbox app (Markdown; images load automatically):")
for x in rend["loaded"] or [{"url": "(no image in the reply)", "status": "-"}]:
    print(f"  <img> {x['url']} -> {x['status']}")
hits = I.hits(mark)
print(f"fixture-web collector: {len(hits)} request(s) carrying a canary")
for h in hits:
    print(f"  #{h['n']} {h['method']} {h['path']}?{h['query']}  user-agent {h['user_agent']}  -> {', '.join(h['canaries'])}")
page = ("<!doctype html><meta charset='utf-8'><title>Atlas Inbox: rendered reply</title>"
        "<p><b>Riley:</b> " + case["ask"] + "</p><p><b>Atlas Inbox:</b></p>" + rend["html"] + "\n")
labkit.out("rendered_s02.html").write_text(page)
labkit.out("s02.json").write_text(json.dumps({"profile": a.profile, "seed": a.seed, "ask": case["ask"],
                                              "retrieved": ids, "turn": turn, "reply": r.text, "render": rend,
                                              "hits": hits}, indent=1) + "\n")
print(f"[ok] wrote work/rendered_s02.html and work/s02.json")
