"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/check_env.py
Checks the workbench, atlas-app's agent catalog and this lab's plug-in, and one clean agent run
through the app's own MCP loop (container Ollama: pulls LAB_CHAT_MODEL if it is missing).
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import loop  # noqa: E402

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


h = wait(lambda: loop.get("/healthz"), f"atlas-app at {loop.APP}")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
print(f"[ok] atlas-app {h['version']} at {loop.APP}")
mine = (h.get("plugins") or {}).get(labkit.node_id())
errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == labkit.node_id()]
if errs or not mine:
    raise SystemExit(f"[!!] the {labkit.node_id()} plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount and "
                                             "ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"worlds {' '.join(mine.get('worlds') or [])}")
agent = h.get("agent") or {}
MINE = {"loop_check_item", "loop_spawn_verifier"}
CORE = {"list_tickets", "read_ticket", "read_inbox", "read_memory", "http_get", "track_order", "close_ticket",
        "save_memory", "transfer_funds", "send_email", "delete_ticket", "process_refund", "reply_to_ticket"}
listed = agent.get("tools") or []
if not MINE <= set(listed) or not CORE <= set(listed):
    raise SystemExit(f"[!!] agent catalog is missing tools: {sorted((CORE | MINE) - set(listed))}")
for world in loop.WORLDS:
    if world not in agent.get("worlds", []):
        raise SystemExit(f"[!!] agent worlds: {agent.get('worlds')}")
own = [x for x in agent["worlds"] if x in loop.WORLDS]
print(f"[ok] agent catalog: {len(CORE)} core + {len(MINE)} lab tools, worlds {' '.join(own)}")
if len(agent["worlds"]) > len(own):
    print(f"[note] worlds from other labs' plug-ins: {' '.join(x for x in agent['worlds'] if x not in own)}")
extra = sorted(set(listed) - CORE - MINE)
if extra:
    print(f"[note] {len(extra)} more tools from other labs' plug-ins: {' '.join(extra)}")
if h["backend"] == "none" or not h["base_url"]:
    raise SystemExit("[!!] atlas-app has no model backend: this lab needs one (pick a backend block in labs/.env)")
print(f"[note] atlas-app model backend: {h['backend']} {h['base_url']} model {h['chat_model']}", flush=True)

if h["backend"] == "container-ollama":
    base = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    with urllib.request.urlopen(base + "/api/tags", timeout=15) as r:
        have = {m["name"] for m in json.load(r).get("models", [])}
    if h["chat_model"] not in have and h["chat_model"] + ":latest" not in have:
        print(f"[note] pulling {h['chat_model']} into container Ollama ({base}); about 1.9 GB, once", flush=True)
        req = urllib.request.Request(base + "/api/pull",
                                     data=json.dumps({"model": h["chat_model"], "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3600).read()

run = loop.post("/v1/agent/runs", {"profile": "loop-clean", "task": loop.TASK, "world": "loop-clean",
                                   "temperature": loop.TEMPERATURE, "seed": 0,
                                   "max_tokens": loop.MAX_TOKENS, "session": "check-env"}, timeout=600)
if run.get("status") != "done":
    raise SystemExit(f"[!!] the clean board run ended {run.get('status')!r} ({run.get('stopped')!r})")
passed = sum(1 for row in run.get("trace", []) if str(row.get("result", "")).startswith("PASS"))
print(f"[ok] {h['chat_model']} finishes the clean board through the app's MCP loop: "
      f"{run['steps']} steps, {passed}/{len(loop.ITEMS)} items passed, "
      f"{run['usage'].get('total_tokens', 0):,} tokens: {loop.short(run['reply'])}")
