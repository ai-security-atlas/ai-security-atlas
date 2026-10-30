"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/check_env.py
Checks the workbench, atlas-app's RAG index and this lab's plug-in, and the model backend behind atlas-app
(container Ollama: pulls LAB_CHAT_MODEL if missing).
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import numpy  # noqa: E402

import kb  # noqa: E402

print(f"[ok] numpy {numpy.__version__}")
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
        h = kb.get("/healthz")
        break
    except (OSError, SystemExit) as e:
        err = e
        time.sleep(2.5)
if h is None:
    raise SystemExit(f"[!!] atlas-app unreachable at {kb.URL} ({err}); is rag-agent in COMPOSE_PROFILES and did "
                     "`docker compose up -d` start it?")
rag = h.get("rag")
if not rag:
    raise SystemExit(f"[!!] atlas-app {h['version']} has no RAG support: rebuild it (`docker compose build atlas-app`)")
if not rag["ready"]:
    raise SystemExit(f"[!!] atlas-app RAG index not built: {rag['error']}")
print(f"[ok] atlas-app RAG ready: embedder {rag['embedder']}, "
      + ", ".join(f"{c} {n} chunks" for c, n in rag["collections"].items()))
mine = (h.get("plugins") or {}).get("system-rag")
if not mine:
    errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == "system-rag"]
    raise SystemExit("[!!] the system-rag plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount "
                                             "and ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
print(f"[ok] plug-in system-rag: profiles {' '.join(mine['profiles'])}; collection {' '.join(mine['collections'])}")
if h["backend"] == "none" or not h["base_url"]:
    raise SystemExit("[!!] atlas-app has no model backend: this lab needs one (pick a backend block in labs/.env)")
print(f"[note] atlas-app model backend: {h['backend']} {h['base_url']} model {h['chat_model']}", flush=True)

if h["backend"] == "container-ollama":
    base = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    with urllib.request.urlopen(base + "/api/tags", timeout=15) as r:
        have = {m["name"] for m in json.load(r).get("models", [])}
    if h["chat_model"] not in have and h["chat_model"] + ":latest" not in have:
        print(f"[note] pulling {h['chat_model']} into container Ollama ({base}); about 1.9 GB, once", flush=True)
        req = urllib.request.Request(base + "/api/pull", data=json.dumps({"model": h["chat_model"], "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3600).read()

try:
    reply, info = kb.chat("sysrag-acl", "What colors does the Cable dock come in?", "harbor-buyer", max_tokens=40)
    print(f"[ok] {h['chat_model']} answers through atlas-app as harbor-buyer: {kb.short(reply, 50)}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
