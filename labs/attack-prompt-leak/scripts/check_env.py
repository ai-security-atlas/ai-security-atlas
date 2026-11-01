"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/check_env.py
Checks the workbench, atlas-app with this lab's plug-in and its model backend (container Ollama: pulls
LAB_CHAT_MODEL if it is missing), and adds atlas-app to Open WebUI as an OpenAI connection when Open WebUI runs.
"""
import json
import os
import socket
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import shop  # noqa: E402

print(f"[ok] evalkit {ek.__version__}")
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


h, err = None, None
for _ in range(12):
    try:
        h = shop.app("/healthz")
        break
    except SystemExit as e:
        err = e
        time.sleep(2.5)
if h is None:
    raise SystemExit(str(err))
mine = (h.get("plugins") or {}).get(labkit.node_id())
if not mine:
    errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == labkit.node_id()]
    raise SystemExit(f"[!!] the {labkit.node_id()} plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount and "
                                             "ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
print(f"[ok] atlas-app {h['version']} at {shop.APP}; plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}")
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
    r = shop.ask("pleak-shop", shop.cases()["hours"]["text"], seed=0)
    print(f"[ok] {h['chat_model']} answers through atlas-app as Juniper: {shop.short(r.text, 50)}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")

# Open WebUI (profile chat): register atlas-app as an extra OpenAI connection, keeping existing ones.
ui, token = "http://open-webui:8080", None
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
    target = shop.APP + "/v1"
    if target not in urls:
        urls, keys = urls + [target], keys + ["atlas-local"]
        call(ui + "/openai/config/update", {"ENABLE_OPENAI_API": True, "OPENAI_API_BASE_URLS": urls,
                                            "OPENAI_API_KEYS": keys, "OPENAI_API_CONFIGS": cfg.get("OPENAI_API_CONFIGS") or {}},
             token=token)
    ids = [m["id"] for m in call(ui + "/api/models", token=token).get("data", [])]
    print(f"[ok] Open WebUI lists atlas-app: {' '.join(i for i in ids if i.startswith('pleak-'))}")
