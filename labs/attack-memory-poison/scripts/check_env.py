"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/check_env.py
Checks the workbench, atlas-app's agent catalog and this lab's plug-in, and one short reply
through the model backend (container Ollama: pulls LAB_CHAT_MODEL if it is missing).
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import mem  # noqa: E402

print(f"[ok] evalkit {ek.__version__}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")


def wait(fn, what):
    err = None
    for _ in range(24):
        try:
            return fn()
        except (OSError, SystemExit) as e:
            err = e
            time.sleep(2.5)
    raise SystemExit(f"[!!] {what} unreachable ({err})")


h = wait(lambda: mem.get("/healthz"), f"atlas-app at {mem.APP}")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
print(f"[ok] atlas-app {h['version']} at {mem.APP}")
rag = h.get("rag") or {}
if not rag.get("ready"):
    raise SystemExit(f"[!!] atlas-app RAG index not ready: {rag.get('error')}; rebuild it "
                     "(`docker compose build atlas-app`)")
mine = (h.get("plugins") or {}).get(labkit.node_id())
errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == labkit.node_id()]
if errs or not mine:
    raise SystemExit(f"[!!] the {labkit.node_id()} plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount and "
                                             "ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
want_profiles = ["mp-tools", "mp-plant", "mp-recall", "mp-policy", "mp-filter", "mp-confirm", "mp-remember"]
want_worlds = ["mp-volatile", "mp-desk"]
if mine.get("profiles") != want_profiles or mine.get("worlds") != want_worlds:
    raise SystemExit(f"[!!] plug-in registered {mine}")
if mine.get("tools") not in ([], None) and mine.get("tools") != []:
    raise SystemExit(f"[!!] this lab adds no tools (got {mine.get('tools')})")
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"worlds {' '.join(mine.get('worlds') or [])}")
names = (h.get("agent") or {}).get("tools") or []
missing = [n for n in ("read_memory", "save_memory", "http_get", "send_email") if n not in names]
if missing or any(w not in (h.get("agent") or {}).get("worlds", []) for w in want_worlds):
    raise SystemExit(f"[!!] agent catalog missing {missing} worlds {(h.get('agent') or {}).get('worlds')}")
print(f"[ok] agent catalog includes read_memory save_memory http_get send_email")
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
    g = mem.run_once("mp-tools", 0, "check-env", task="Reply with the single word ready. Do not call tools.")
    print(f"[ok] {h['chat_model']} answers through the assistant: {mem.short(g['reply'])}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
    raise
