"""Step 6: does the sponge transfer to other runtimes? Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/s06_transfer.py
The local row runs always; the API row needs a model backend (the step is tagged optional for it).
With no backend set, this script prints [skip] and still runs the local row.
"""
import json
import os
import urllib.request

import labkit

labkit.banner()

import tinylm  # noqa: E402

import sponge  # noqa: E402

pin = sponge.pinned()
user = sponge.REQUEST + pin["suffix"]
rows = []

src = json.loads(labkit.out("pinned.json").read_text()) if labkit.out("pinned.json").exists() else None
if src:
    rows.append({"model": "smollm2-135m", "note": "source, Step 5", "clean_out": src["clean"]["n_out"],
                 "sponge_out": src["pinned"]["n_out"], "hit_cap": not src["pinned"]["stopped"]})
else:
    tok, model = sponge.load()
    cl = sponge.generate(tok, model, sponge.REQUEST, max_new_tokens=sponge.CAP)
    sp = sponge.generate(tok, model, user, max_new_tokens=sponge.CAP)
    rows.append({"model": "smollm2-135m", "note": "source (re-measured)", "clean_out": cl["n_out"],
                 "sponge_out": sp["n_out"], "hit_cap": not sp["stopped"]})

print(f"transfer target {tinylm.MODELS[sponge.SECOND][0]} @ {tinylm.MODELS[sponge.SECOND][1][:7]} "
      f"(same family, 2.7x larger, never touched by the optimizer)")
tok2, model2 = sponge.load(sponge.SECOND)
cl2 = sponge.generate(tok2, model2, sponge.REQUEST, max_new_tokens=sponge.CAP)
sp2 = sponge.generate(tok2, model2, user, max_new_tokens=sponge.CAP)
rows.append({"model": "smollm2-360m", "note": "local weights", "clean_out": cl2["n_out"],
             "sponge_out": sp2["n_out"], "hit_cap": not sp2["stopped"]})

b = labkit.backend()
chat = os.environ.get("LAB_CHAT_MODEL", "").strip() or (b or {}).get("vlm_model", "")
if not b:
    print("[skip] transfer (no model backend): the API row needs a chat endpoint you chose")
else:
    url = b["base_url"].rstrip("/") + "/chat/completions"
    print(f"[notes] chat endpoint {url} model {chat}; sending clean and sponge requests, "
          f"max_tokens {sponge.CAP}, temperature 0")

    def call(text):
        body = json.dumps({"model": chat, "temperature": 0, "max_tokens": sponge.CAP,
                           "messages": [{"role": "system", "content": sponge.SYSTEM},
                                        {"role": "user", "content": text}]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json",
                                                              "Authorization": f"Bearer {b['api_key']}"})
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.load(r)
        c = d["choices"][0]
        usage = d.get("usage") or {}
        out = usage.get("completion_tokens")
        if out is None:                      # some stand-ins omit usage; count text pieces instead
            out = len((c["message"]["content"] or "").split())
        return {"out": out, "finish": c.get("finish_reason"),
                "reply": (c["message"]["content"] or "").strip()}

    clb = call(sponge.REQUEST)
    spb = call(user)
    rows.append({"model": chat, "note": f"backend {b['name']}", "clean_out": clb["out"],
                 "sponge_out": spb["out"], "hit_cap": spb["finish"] == "length", "reply": spb["reply"][:120]})

print(f"\n{'model':16} {'note':22} {'clean out':>9} {'sponge out':>10} {'runs to cap':>11}")
for r in rows:
    print(f"{r['model']:16} {r['note']:22} {r['clean_out']:>9} {r['sponge_out']:>10} {str(r['hit_cap']):>11}")
if len(rows) > 2 and "reply" in rows[-1]:
    print(f"backend sponge reply opens: {rows[-1]['reply']!r}")

held = rows[1:]
n_hit = sum(1 for r in held if r["hit_cap"])
labkit.out("transfer.json").write_text(json.dumps({"rows": rows, "n_heldout": len(held), "n_hit": n_hit,
                                                   "cap": sponge.CAP}) + "\n")
print(f"RESULT transfer {n_hit}/{len(held)} held-out runtimes run to the {sponge.CAP}-token cap "
      f"(source row excluded); the suffix was optimized for one model and one runtime "
      f"-> work/transfer.json")
