"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/check_env.py
Checks the workbench, atlas-app, this lab's plug-in, and one public-docs reply through the model backend.
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import library as lib  # noqa: E402

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


h = wait(lambda: lib.get("/healthz"), f"atlas-app at {lib.APP}")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
print(f"[ok] atlas-app {h['version']} at {lib.APP}")
mine = (h.get("plugins") or {}).get(labkit.node_id())
errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == labkit.node_id()]
if errs or not mine:
    raise SystemExit(f"[!!] the {labkit.node_id()} plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount and "
                                             "ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"worlds {' '.join(mine.get('worlds') or [])}")
for other in h.get("plugin_errors", []):
    if other["lab"] != labkit.node_id():
        print(f"[note] other plug-in skipped: {other['lab']}: {other['error']}")
agent = h.get("agent") or {}
NEED = {"cdoc_list", "cdoc_read", "cdoc_read_checked", "cdoc_read_obo", "cdoc_read_public"}
listed = agent.get("tools") or []
if not NEED <= set(listed):
    raise SystemExit(f"[!!] agent catalog is missing {sorted(NEED - set(listed))}")
own_worlds = [w for w in agent.get("worlds", []) if w == "docs-library"]
if own_worlds != ["docs-library"]:
    raise SystemExit(f"[!!] agent worlds: {agent.get('worlds')}")
print(f"[ok] agent catalog includes {len(NEED)} cdoc tools, world docs-library")
extra_worlds = [w for w in agent["worlds"] if w != "docs-library"]
if extra_worlds:
    print(f"[note] worlds from other labs' plug-ins: {' '.join(extra_worlds)}")
extra_tools = sorted(set(listed) - NEED)
if extra_tools:
    print(f"[note] {len(extra_tools)} more tools from the core catalog and other labs' plug-ins: {' '.join(extra_tools)}")
if h["backend"] == "none" or not h["base_url"]:
    raise SystemExit("[!!] atlas-app has no model backend: this lab needs one (pass LAB_BACKEND and LAB_LLM_BASE_URL)")
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
    g = lib.run_once("cdoc-least", "mallory", "handbook", 0, "check-env")
    print(f"[ok] {h['chat_model']} answers through the docs assistant: {lib.short(g['reply'])}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
    raise
