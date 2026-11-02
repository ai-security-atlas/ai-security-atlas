"""Step 6 (model backend): a 3B chat model behind Ollama picks the next speaker too. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s06_ollama_raw.py
Sends 16 short requests to the Ollama server of the .env backend block: 8 raw transcripts that end where the next
turn opens (/api/generate with raw=true), then the same 8 questions through the chat API (/api/chat).
"""
import json
import urllib.request

import labkit

labkit.banner()

import declab as D  # noqa: E402
import evalkit  # noqa: E402
from evalkit.client import ollama_root  # noqa: E402

if not labkit.backend():
    raise SystemExit("[skip] no model backend in labs/.env; Step 6 needs Ollama")
chat = evalkit.Chat.from_env()
root = ollama_root(chat.base_url)
info = evalkit.ollama_info(chat.base_url, chat.model)
if not info["ollama"]:
    raise SystemExit(f"[!!] {chat.base_url} is not Ollama; raw mode is an Ollama option")
print(f"[note] sending 16 requests to {root} model {chat.model} (Ollama {info['ollama']}, digest {info['digest']})")
clock = D.Clock()


def post(path, body):
    req = urllib.request.Request(root + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


OPTS = {"temperature": 0, "seed": 0, "num_predict": 40}
raw_rows = []
for q, a in zip(D.QUESTIONS, D.ANSWERS):
    prompt = (f"{D.IM_START}system\n{D.SYSTEM}{D.IM_END}\n{D.IM_START}user\n{q}{D.IM_END}\n"
              f"{D.IM_START}assistant\n{a}{D.IM_END}\n{D.IM_START}")
    r = post("/api/generate", {"model": chat.model, "prompt": prompt, "raw": True, "stream": False, "options": OPTS})
    out = r["response"]
    role = out.split("\n", 1)[0].strip().lower()
    raw_rows.append({"q": q, "role": role, "text": out.split("\n", 1)[1].strip() if "\n" in out else "",
                     "done": r.get("done_reason")})
chat_rows = []
for q in D.QUESTIONS:
    r = post("/api/chat", {"model": chat.model, "stream": False, "options": OPTS,
                           "messages": [{"role": "system", "content": D.SYSTEM}, {"role": "user", "content": q}]})
    text = r["message"]["content"]
    chat_rows.append({"q": q, "reply": text, "markers": D.role_markers(text), "done": r.get("done_reason"),
                      "follows": D.follows(text)})
roles = {}
for x in raw_rows:
    roles[x["role"]] = roles.get(x["role"], 0) + 1
print("raw transcript ending in '<|im_end|>\\n<|im_start|>' (the model writes the role name and the turn)")
print("   roles it wrote: " + "  ".join(f"{k} {v}/8" for k, v in roles.items()))
for x in raw_rows[:3]:
    print(f"   after {x['q']!r:<34} -> {x['role']}: {x['text'][:52]!r}")
clean = sum(not x["markers"] for x in chat_rows)
print(f"/api/chat with the same 8 questions: replies with no role marker {clean}/8, "
      f"stopped by the runtime {sum(x['done'] == 'stop' for x in chat_rows)}/8, {D.MARKER} {sum(x['follows'] for x in chat_rows)}/8")
print(f"   {chat_rows[0]['q']!r} -> {chat_rows[0]['reply'][:60]!r}")
print(clock)
D.save("s06_ollama_raw.json", {"ollama": info["ollama"], "model": chat.model, "digest": info["digest"],
                               "raw": raw_rows, "roles": roles, "chat": chat_rows})
