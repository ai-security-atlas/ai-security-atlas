"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/check_env.py
Checks the workbench, atlas-app's agent catalog and this lab's plug-in, and one read-only
agent reply through the model backend (container Ollama: pulls LAB_CHAT_MODEL if it is missing).
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import desk  # noqa: E402

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


h = wait(lambda: desk.get("/healthz"), f"atlas-app at {desk.APP}")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
print(f"[ok] atlas-app {h['version']} at {desk.APP}")
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
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"worlds {' '.join(mine.get('worlds') or [])}")
agent = h.get("agent") or {}
CORE = {"list_tickets", "read_ticket", "read_inbox", "read_memory", "http_get", "track_order", "close_ticket",
        "save_memory", "transfer_funds", "send_email", "delete_ticket", "process_refund", "reply_to_ticket"}
listed = agent.get("tools") or []
if listed != sorted(listed) or not CORE <= set(listed):   # other labs' plug-ins may add tools on top
    raise SystemExit(f"[!!] agent catalog: {agent.get('tools')}")
if "desk-poisoned" not in agent.get("worlds", []) or "desk-clean" not in agent.get("worlds", []):
    raise SystemExit(f"[!!] agent worlds: {agent.get('worlds')}")
own = [w for w in agent["worlds"] if w in ("desk-poisoned", "desk-clean")]
print(f"[ok] agent catalog: {len(CORE)} tools, worlds {' '.join(own)}")
if len(agent["worlds"]) > len(own):
    print(f"[note] worlds from other labs' plug-ins: {' '.join(w for w in agent['worlds'] if w not in own)}")
if len(listed) > len(CORE):
    print(f"[note] {len(listed) - len(CORE)} more tools from other labs' plug-ins: {' '.join(sorted(set(listed) - CORE))}")
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
    g = desk.run_once("desk-readonly", 0, "check-env")
    print(f"[ok] {h['chat_model']} answers through the returns desk: {desk.short(g['reply'])}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
    raise
