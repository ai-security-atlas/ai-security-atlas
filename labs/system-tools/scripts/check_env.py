"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/check_env.py
Checks the workbench, this lab's plug-in (with any other labs' plug-ins also mounted), and one benign
reply through the model backend (container Ollama: pulls LAB_CHAT_MODEL if it is missing).
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import stk  # noqa: E402

print(f"[ok] evalkit {ek.__version__}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

h, err = None, None
for _ in range(24):
    try:
        h = stk.get("/healthz")
        break
    except SystemExit as e:
        err = e
        time.sleep(2.5)
if h is None:
    raise SystemExit(f"[!!] atlas-app unreachable at {stk.APP} ({err})")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
print(f"[ok] atlas-app {h['version']} at {stk.APP}")
me = labkit.node_id()
mine = (h.get("plugins") or {}).get(me)
errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == me]
if errs or not mine:
    raise SystemExit(f"[!!] the {me} plug-in is not loaded: " + (errs[0] if errs else
                     "atlas-app does not see labs/ (it needs the read-only labs/ mount and ATLAS_APP_LABS=/labs)"))
if mine.get("profiles") != list(stk.PROFILES) or mine.get("worlds") != ["stools-desk"] \
        or mine.get("tools") != list(stk.TOOLS):
    raise SystemExit(f"[!!] plug-in registered {mine}")
print(f"[ok] plug-in {me}: profiles {' '.join(mine['profiles'])}; worlds {' '.join(mine['worlds'])}; "
      f"tools {' '.join(mine['tools'])}")
agent = h.get("agent") or {}
missing = [t for t in stk.TOOLS if t not in (agent.get("tools") or [])]
if missing or "stools-desk" not in (agent.get("worlds") or []):
    raise SystemExit(f"[!!] agent catalog missing {missing}, worlds {agent.get('worlds')}")
others = sorted(lab for lab in (h.get("plugins") or {}) if lab != me)
print(f"[ok] agent catalog has the {len(stk.TOOLS)} stools tools")
if others:
    print(f"[note] other labs' plug-ins also loaded: {len(others)}")
for profile in stk.PROFILES:
    names = [t["name"] for t in stk.catalog(profile)["tools"]]
    if not all(n.startswith("stools-") for n in names) or len(names) != 3:
        raise SystemExit(f"[!!] {profile} lists {names}; it must grant exactly three stools tools")
print("[ok] each profile lists exactly its three named tools")
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
    g = stk.run_once("stools-strict", "returns", 0, "check-env")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
    raise
if g["read"]:
    raise SystemExit("[!!] the benign check read the canary")
print(f"[ok] {h['chat_model']} answers through the assistant: {stk.short(g['reply'], 60)}")
