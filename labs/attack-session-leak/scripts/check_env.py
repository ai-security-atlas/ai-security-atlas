"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/check_env.py
The walkthrough uses a stub answerer, so a missing model backend is a note, not a failure.
"""
import time

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import sleak  # noqa: E402

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
        h = sleak.get("/healthz")
        break
    except (OSError, SystemExit) as e:
        err = e
        time.sleep(2.5)
if h is None:
    raise SystemExit(f"[!!] atlas-app unreachable at {sleak.URL} ({err}); is rag-agent in COMPOSE_PROFILES "
                     "and did `docker compose up -d` start it?")
if h.get("version") != "1.0.0":
    raise SystemExit(f"[!!] atlas-app version {h.get('version')!r}; the shared app stays at 1.0.0")
rag = h.get("rag") or {}
if not rag.get("ready"):
    raise SystemExit(f"[!!] atlas-app RAG index not ready: {rag.get('error')}")
mine = (h.get("plugins") or {}).get(labkit.node_id())
errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == labkit.node_id()]
if errs or not mine:
    raise SystemExit(f"[!!] the {labkit.node_id()} plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount and "
                                             "ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
print(f"[ok] atlas-app {h['version']} RAG ready")
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"collection {' '.join(mine['collections'])}")
chunks = (rag.get("collections") or {}).get(sleak.COLLECTION)
if not chunks:
    raise SystemExit(f"[!!] collection {sleak.COLLECTION} has no chunks")
print(f"[ok] collection {sleak.COLLECTION}: {chunks} chunks")
others = sorted(k for k in (h.get("plugins") or {}) if k != labkit.node_id())
if others:
    print(f"[note] other plug-ins also loaded: {' '.join(others)}")
if h.get("plugin_errors"):
    print(f"[note] plug-in errors from other labs: {len(h['plugin_errors'])}")
agent = h.get("agent") or {}
core = {"list_tickets", "read_ticket", "read_inbox", "read_memory", "http_get", "track_order",
        "close_ticket", "save_memory", "transfer_funds", "send_email", "delete_ticket",
        "process_refund", "reply_to_ticket"}
extra = sorted(set(agent.get("tools") or []) - core)
if extra:
    print(f"[note] tools from other labs' plug-ins: {' '.join(extra)}")
worlds = agent.get("worlds") or []
if worlds:
    print(f"[note] worlds from other labs' plug-ins: {' '.join(worlds)}")
backend = h.get("backend") or "none"
if backend in ("", "none") or not h.get("base_url"):
    print("[ok] model backend optional: none (the stub walkthrough still runs)")
else:
    print(f"[ok] model backend optional: {backend} {h.get('base_url')} model {h.get('chat_model')}")
