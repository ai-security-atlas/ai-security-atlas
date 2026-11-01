"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/check_env.py
Checks the workbench packages (sqlglot, bleach, sqlite3), builds the shop database once, and reports
atlas-app only if the rag-agent profile is up (it is needed only for the optional live step).
"""
import json
import socket

import labkit

labkit.banner()

import sqlglot  # noqa: E402
import bleach   # noqa: E402

import sink  # noqa: E402

print(f"[ok] sqlglot {sqlglot.__version__} bleach {bleach.__version__}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

p = sink.build_db(sink.db_path())
cols, rows = sink.run_sql("SELECT count(*) FROM products")
nrev = sink.run_sql("SELECT count(*) FROM reviews")[1][0][0]
print(f"[ok] shop database at {p.name}: {rows[0][0]} products, {nrev} reviews, secrets table holds canary {sink.CANARY}")

r = sink.replies()
print(f"[ok] recorded model outputs: {' '.join(sorted(k for k in r if not k.startswith('_')))}")

# atlas-app is optional here (only s04_live.py uses it). Report it when rag-agent is running.
try:
    socket.gethostbyname("atlas-app")
except OSError:
    print("[skip] atlas-app not running (add rag-agent to COMPOSE_PROFILES for the optional live step)")
else:
    import urllib.request
    try:
        with urllib.request.urlopen("http://atlas-app:8000/healthz", timeout=15) as resp:
            h = json.load(resp)
        osink = h.get("plugins", {}).get("attack-output-sink", {})
        print(f"[ok] atlas-app {h['version']} backend {h['backend']}; "
              f"plug-in profiles {' '.join(osink.get('profiles', [])) or '(none)'}")
    except OSError as e:
        print(f"[skip] atlas-app did not answer ({e}); the optional live step needs it")
