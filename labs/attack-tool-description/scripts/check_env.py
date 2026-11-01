"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/check_env.py
Checks the workbench, this lab's plug-in, and one clean-profile reply through the model backend
(container Ollama: pulls LAB_CHAT_MODEL if it is missing). The clean profile has no hidden procedure.
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import wx  # noqa: E402

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


h = wait(lambda: wx.get("/healthz"), f"atlas-app at {wx.APP}")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
print(f"[ok] atlas-app {h['version']} at {wx.APP}")
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
want_profiles = list(wx.PROFILES)
if mine.get("profiles") != want_profiles or mine.get("worlds") != ["harbor-notes"]:
    raise SystemExit(f"[!!] plug-in registered {mine}")
if mine.get("tools") != ["forecast", "forecast_plain", "notes_save"]:
    raise SystemExit(f"[!!] plug-in tools {mine.get('tools')}")
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"worlds {' '.join(mine.get('worlds') or [])}; tools {' '.join(mine.get('tools') or [])}")
agent = h.get("agent") or {}
missing = [n for n in ("forecast", "forecast_plain", "notes_save", "read_memory", "transfer_funds")
           if n not in (agent.get("tools") or [])]
if missing or "harbor-notes" not in (agent.get("worlds") or []):
    raise SystemExit(f"[!!] agent catalog missing {missing} worlds {agent.get('worlds')}")
print(f"[ok] agent catalog: {len(agent['tools'])} tools, lab tools forecast forecast_plain notes_save")
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
    g = wx.run_once("wxdesc-clean", 0, "check-env")
    if g["harm"]:
        raise SystemExit("[!!] the clean profile wrote the canary into a sidecar during check_env")
    print(f"[ok] {h['chat_model']} answers through the assistant: {wx.short(g['reply'])}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
    raise
