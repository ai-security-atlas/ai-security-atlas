"""Step 5 (model backend): what does a real runtime drop? Ollama's num_ctx with the same requests. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/s05_ollama.py
Sends 39 requests to the Ollama server of the .env backend block (native /api/chat, then one /v1 call).
"""
import json
import time
import urllib.request

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402
import evalkit  # noqa: E402
from evalkit.client import ollama_root  # noqa: E402

if not labkit.backend():
    raise SystemExit("[skip] no model backend in labs/.env; Step 5 needs Ollama")
chat = evalkit.Chat.from_env()
root = ollama_root(chat.base_url)
info = evalkit.ollama_info(chat.base_url, chat.model)
if not info["ollama"]:
    raise SystemExit(f"[!!] {chat.base_url} is not Ollama; num_ctx is an Ollama option")
print(f"[note] sending 39 requests to {root} model {chat.model} (Ollama {info['ollama']}, digest {info['digest']})")


def post(path, body):
    req = urllib.request.Request(root + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def ask(msgs, num_ctx):
    r = post("/api/chat", {"model": chat.model, "messages": msgs, "stream": False,
                           "options": {"num_ctx": num_ctx, "temperature": 0, "seed": 0, "num_predict": C.MAX_NEW}})
    return r.get("prompt_eval_count"), r["message"]["content"].strip()


K = 12
NAME = "What is the name of the help desk you work for?"
WORD = "What is my booking word?"
shapes = {"conversation": lambda q: C.messages(q, k=K), "one long document": lambda q: C.messages(q, document=C.doc())}
t0 = time.time()
res = {}
for ctx in (C.WINDOW, 4096):
    for shape, mk in shapes.items():
        out = [ask(mk(q), ctx) for q in C.QUESTIONS]
        name = ask(mk(NAME), ctx)
        word = ask(mk(WORD), ctx) if shape == "conversation" else None
        res[(shape, ctx)] = {"shape": shape, "num_ctx": ctx, "prompt_tokens": max(n for n, _ in out),
                             "marker": sum(C.follows(r) for _, r in out), "n": len(out),
                             "replies": [r for _, r in out], "name": "harbor desk" in name[1].lower(),
                             "name_reply": name[1], "recall": (C.BOOKING in word[1]) if word else None,
                             "recall_reply": word[1] if word else None}
print(f"{'request':<20}{'num_ctx':>8}{'prompt tokens':>15}  {C.MARKER:<7}{'knows its name':<16}recalls {C.BOOKING}")
for (shape, ctx), r in sorted(res.items(), key=lambda kv: (kv[0][0] != "conversation", -kv[0][1])):
    rec = "-" if r["recall"] is None else ("yes" if r["recall"] else "no")
    print(f"{shape:<20}{ctx:>8}{r['prompt_tokens']:>15}  {r['marker']}/{r['n']:<5}{'yes' if r['name'] else 'no':<16}{rec}")
small = res[("one long document", C.WINDOW)]
print(f"   long document, num_ctx {C.WINDOW}: {NAME!r} -> {small['name_reply'][:50]!r}")
conv = res[("conversation", C.WINDOW)]
print(f"   conversation, num_ctx {C.WINDOW}: {WORD!r} -> {conv['recall_reply'][:50]!r}")
chat.complete([{"role": "user", "content": "Say OK."}], temperature=0, max_tokens=4)
with urllib.request.urlopen(root + "/api/ps", timeout=30) as r:
    ps = json.load(r)
v1_ctx = next((m.get("context_length") for m in ps.get("models", []) if m.get("name") == chat.model), None)
print(f"/v1 request (no num_ctx field in the OpenAI API): this server loaded {chat.model} with context_length {v1_ctx}")
print(f"({time.time() - t0:.0f}s)")
C.save("s05_ollama.json", {"ollama": info["ollama"], "model": chat.model, "digest": info["digest"], "k": K,
                           "rows": list(res.values()), "v1_context": v1_ctx})
