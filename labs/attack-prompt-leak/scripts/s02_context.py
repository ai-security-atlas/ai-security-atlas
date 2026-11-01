"""Step 2: one context, one request. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/s02_context.py
Asks atlas-app (operator preview, no model call) for the exact messages the model receives with the "repeat"
request from assets/requests.json, then sends that request once (seed 0) and grades the reply with leak.py.
Writes work/context.json.
"""
import json

import labkit

labkit.banner()

import leak  # noqa: E402
import shop  # noqa: E402

c = shop.cases()["repeat"]
pv = shop.app("/admin/rag/preview", {"profile": "pleak-shop", "messages": [{"role": "user", "content": c["text"]}]})
print("model context for one customer message (POST /admin/rag/preview, operator view):")
for m, s in zip(pv["messages"], pv["context"]):
    holds = "yes" if shop.CANARY in m["content"] else "no"
    print(f"  {m['role']:<7} from {s['source']:<9} {s['chars']:>4} chars   holds {shop.CANARY}: {holds}")
print()
r = shop.ask("pleak-shop", c["text"], seed=0, session="lab19-context")
d = leak.detect(r.text, shop.CANARY)
ov = leak.overlap(r.text, shop.prompt_of("pleak-shop"))
print(f"request ({c['family']}), seed 0:")
print(f"  reply: {shop.short(r.text, 110)}")
print(f"  leak form: {d['form'] or 'none'}   prompt overlap: {ov:.2f} of {len(shop.prompt_of('pleak-shop'))} chars")
labkit.out("context.json").write_text(json.dumps({"context": pv["context"], "request": c["id"], "reply": r.text,
                                                  "form": d["form"], "overlap": ov}, indent=1) + "\n")
