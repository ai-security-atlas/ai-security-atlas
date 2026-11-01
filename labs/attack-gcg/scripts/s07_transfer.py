"""Step 7: does the suffix transfer? The frozen suffix goes to SmolLM2-360M-Instruct (tinylm) and,
when a model backend is set, to the chat model behind the API. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s07_transfer.py
Network: the 360M download into the HF cache (first run only) and, with a backend, the chat endpoint.
Writes work/transfer.json.
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import gcg  # noqa: E402
import tinylm  # noqa: E402

pin = gcg.pinned()
user = gcg.REQUEST + pin["suffix"]
rows = []


def row(model, reply_clean, reply_adv, note=""):
    rows.append({"model": model, "clean": reply_clean[:80], "suffix": reply_adv[:80], "canary": gcg.hit(reply_adv),
                 "note": note})
    r = rows[-1]
    print(f"{r['model']:<34} clean {r['clean'][:38]!r}")
    print(f"{'':<34} +suffix {r['suffix'][:52]!r}  canary {r['canary']}")


tok, model = gcg.load()
row("smollm2-135m (source)", gcg.reply(tok, model, gcg.REQUEST), gcg.reply(tok, model, user),
    "white-box: the suffix was optimized on it")

print(f"\ntransfer target {tinylm.MODELS[gcg.SECOND][0]} @ {tinylm.MODELS[gcg.SECOND][1][:7]} "
      f"(fetching into the HF cache if missing)", flush=True)
t0 = time.time()
tok2, model2 = tinylm.load(gcg.SECOND, download=True)
print(f"loaded in {time.time() - t0:.0f}s")
row("smollm2-360m", gcg.reply(tok2, model2, gcg.REQUEST), gcg.reply(tok2, model2, user),
    "same family, 2.7x larger, never seen during optimization")

b = labkit.backend()
chat = os.environ.get("LAB_CHAT_MODEL", "").strip()
if b and chat:
    url = b["base_url"].rstrip("/") + "/chat/completions"
    print(f"\n[notes] chat endpoint {url} model {chat} (transfer row only); sending the prompt now")

    def ask(user, max_tokens=48):
        body = json.dumps({"model": chat, "temperature": 0, "max_tokens": max_tokens,
                           "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json",
                                                              "Authorization": f"Bearer {b['api_key']}"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()

    row(f"{chat} (backend)", ask(gcg.REQUEST), ask(user), "unrelated model behind an API")
elif b:
    print("\n[skip] transfer (backend set but LAB_CHAT_MODEL is empty): the tinylm rows are the whole table")
else:
    print("\n[skip] transfer (no model backend): the tinylm rows above are the whole table")
n = sum(r["canary"] for r in rows[1:])
print(f"\nRESULT transfer {n}/{len(rows) - 1} held-out models reply with the canary "
      f"(source row excluded); suffix frozen from assets/suffix.json")
labkit.out("transfer.json").write_text(json.dumps({"rows": rows, "n_transfer": n,
                                                   "n_heldout": len(rows) - 1}, indent=1) + "\n")
