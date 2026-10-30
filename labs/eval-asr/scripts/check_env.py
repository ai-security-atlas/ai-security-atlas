"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/check_env.py
Checks evalkit, the work dir, atlas-app (the measured app, profile rag-agent) and its model backend, and the judge
model on the same backend. With container Ollama it pulls the missing models (qwen2.5:3b 1.9 GB, llama3.2:3b 2.0 GB).
Also hashes LAB-06's catalogue, which this lab reads in place.
"""
import json
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import subject as S  # noqa: E402

print(f"[ok] evalkit {ek.__version__} (labs/_shared/evalkit)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

h, err = None, None
for _ in range(12):
    try:
        h = S.health()
        break
    except ek.ChatError as e:
        err = e
        time.sleep(2.5)
if h is None:
    raise SystemExit(f"[!!] atlas-app unreachable at {S.URL} ({err}); is rag-agent in COMPOSE_PROFILES and did "
                     "`docker compose up -d` start it?")
print(f"[ok] atlas-app {h['version']} at {S.URL} ({len(h['profiles'])} profiles, canary {h['canary']})")
if h["backend"] == "none" or not h["base_url"]:
    raise SystemExit("[!!] atlas-app has no model backend: this lab needs one (pick a backend block in labs/.env)")
b = labkit.backend()
if b is None:
    raise SystemExit("[!!] the workbench has no model backend (LAB_BACKEND / LAB_LLM_BASE_URL): the judge needs one")
info = ek.ollama_info(b["base_url"], h["chat_model"])
server = f"ollama {info['ollama']}" if info.get("ollama") else "not an Ollama API"
print(f"[note] model backend: {b['name']} {b['base_url']} ({server})", flush=True)

if b["name"] == "container-ollama":
    root = ek.client.ollama_root(b["base_url"])
    have = {m["name"] for m in json.load(urllib.request.urlopen(root + "/api/tags", timeout=15)).get("models", [])}
    for model in (h["chat_model"], S.JUDGE_MODEL):
        if model not in have and model + ":latest" not in have:
            print(f"[note] pulling {model} into container Ollama ({root}), once", flush=True)
            req = urllib.request.Request(root + "/api/pull", data=json.dumps({"model": model, "stream": False}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3600).read()

try:
    r = S.app.complete([{"role": "user", "content": "Hi! When will my cable dock arrive?"}], model="atlas-support",
                       seed=0, max_tokens=40, extra={"user": "lab12-check"})
    d = ek.ollama_info(b["base_url"], h["chat_model"]).get("digest")
    print(f"[ok] subject {h['chat_model']} @ {d} answers through atlas-app: {S.short(r.text, 44)}")
except ek.ChatError as e:
    print(f"[!!] the subject model did not answer ({e}); host Ollama: run `ollama pull {h['chat_model']}` on the host")
j = S.judge()
try:
    v = j.verdict("Refund approved: ATLAS-REFUND-CANARY")
    d = ek.ollama_info(b["base_url"], j.model).get("digest")
    print(f"[ok] judge {j.model} @ {d} answers on the backend: {v!r}")
except ek.ChatError as e:
    print(f"[!!] the judge did not answer ({e}); host Ollama: run `ollama pull {j.model}` on the host")
cat = S.catalogue()
print(f"[ok] subject attack: LAB-06 assets/catalogue.json ({len(cat)} techniques, sha256 "
      f"{ek.manifest.sha256_file(S.CATALOGUE)[:12]})")
