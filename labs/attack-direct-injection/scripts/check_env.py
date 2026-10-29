"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-direct-injection/scripts/check_env.py
Checks the workbench, atlas-app and its model backend (container Ollama: pulls LAB_CHAT_MODEL if missing),
and adds atlas-app to Open WebUI as an OpenAI connection when Open WebUI is running.
"""
import json
import os
import socket
import time
import urllib.error
import urllib.request

import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402

import bot  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")


def call(url, body=None, token=None, timeout=15):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=h,
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


h = None
for _ in range(12):
    try:
        h = bot.get("/healthz")
        break
    except OSError as e:
        err = e
        time.sleep(2.5)
if h is None:
    raise SystemExit(f"[!!] atlas-app unreachable at {bot.URL} ({err}); is rag-agent in COMPOSE_PROFILES and did "
                     "`docker compose up -d` start it?")
print(f"[ok] atlas-app {h['version']} at {bot.URL} ({len(h['profiles'])} profiles, canary {h['canary']})")
if h["backend"] == "none" or not h["base_url"]:
    raise SystemExit("[!!] atlas-app has no model backend: this lab needs one (pick a backend block in labs/.env)")
print(f"[note] atlas-app model backend: {h['backend']} {h['base_url']} model {h['chat_model']}", flush=True)

if h["backend"] == "container-ollama":
    base = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    have = {m["name"] for m in call(base + "/api/tags").get("models", [])}
    if h["chat_model"] not in have and h["chat_model"] + ":latest" not in have:
        print(f"[note] pulling {h['chat_model']} into container Ollama ({base}); about 1.9 GB, once", flush=True)
        call(base + "/api/pull", {"model": h["chat_model"], "stream": False}, timeout=3600)

try:
    reply, info, _ = bot.chat([{"role": "user", "content": "Hi! When will my cable dock arrive?"}], seed=0,
                              session="lab06-check", max_tokens=40)
    print(f"[ok] {h['chat_model']} answers through atlas-app: {bot.short(reply, 50)}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")

# Open WebUI (profile chat): register atlas-app as an extra OpenAI connection, keeping existing ones.
ui = "http://open-webui:8080"
token = None
try:
    socket.gethostbyname("open-webui")
except OSError:
    print("[skip] Open WebUI not running (add chat to COMPOSE_PROFILES for the browser steps)")
else:
    for _ in range(36):                            # it needs about 20 s after `up -d`
        try:
            token = call(ui + "/api/v1/auths/signin", {"email": "", "password": ""})["token"]
            break
        except OSError:
            time.sleep(5)
    if not token:
        print("[!!] Open WebUI did not answer within 3 min; rerun this script once it is up")
if token:
    cfg = call(ui + "/openai/config", token=token)
    urls, keys = cfg.get("OPENAI_API_BASE_URLS") or [], cfg.get("OPENAI_API_KEYS") or []
    if not cfg.get("ENABLE_OPENAI_API"):          # nothing configured on purpose: drop the placeholder default
        urls, keys = [], []
    target = bot.URL + "/v1"
    if target not in urls:
        urls, keys = urls + [target], keys + ["atlas-local"]
        call(ui + "/openai/config/update", {"ENABLE_OPENAI_API": True, "OPENAI_API_BASE_URLS": urls,
                                            "OPENAI_API_KEYS": keys, "OPENAI_API_CONFIGS": cfg.get("OPENAI_API_CONFIGS") or {}},
             token=token)
    ids = [m["id"] for m in call(ui + "/api/models", token=token).get("data", [])]
    shown = [i for i in ids if i.startswith("atlas-support")]
    print(f"[ok] Open WebUI lists atlas-app: {' '.join(shown)}")
