"""Step D3: contain execution in the sandbox service. Run from labs/ (note: the `sandbox` service):
    docker compose run --rm sandbox python attack-output-sink/scripts/d3_sandbox.py
The generated SQL runs in the hardened sandbox (no network, read-only root and checkout). A query
that tries to write an exfil file or reach the network is contained; a plain read still returns the
canary, which is the point: isolation limits blast radius, it does not stop the read (that is D1).
"""
import errno
import json
import socket
import sqlite3

import labkit

labkit.banner()

import sink  # noqa: E402

sink.build_db(sink.db_path())   # /work is a writable tmpfs in the sandbox; /labs is read-only
out = {"canary": sink.CANARY}

# 1) A plain read still succeeds inside the sandbox: containment is not prevention.
cols, rows = sink.run_sql("SELECT name, value FROM secrets", readonly=True)
out["read_canary"] = sink.rows_have_canary(rows)
print(f"read-only SELECT on secrets -> canary in result: {out['read_canary']}  (isolation does not stop a read)")

# 2) The model's write/exfil query (ATTACH a file under the read-only checkout) is contained.
write_sql = sink.extract_sql(sink.replies()["sql_write"]["model_reply"])
print(f"\nmodel's exfil SQL:\n  {write_sql.replace(chr(10), chr(10) + '  ')}")
db = sqlite3.connect(str(sink.db_path()))
try:
    db.executescript(write_sql)
    out["write_blocked"] = False
    print("write: SUCCEEDED (not contained!)")
except sqlite3.OperationalError as e:
    out["write_blocked"] = True
    out["write_error"] = str(e)
    print(f"write: BLOCKED by the read-only checkout -> OperationalError: {e}")
finally:
    db.close()

# 3) Egress probe (harness code, not model output) to a reserved, non-routable address. Only
#    "Network is unreachable" (no interface at all) counts as isolation: a timeout just means the
#    reserved address did not answer, which also happens on an ordinary network.
try:
    socket.create_connection(("192.0.2.1", 9), timeout=3).close()
    out["egress_blocked"] = False
    print("\negress 192.0.2.1:9: CONNECTED (not contained!)")
except OSError as e:
    out["egress_blocked"] = e.errno == errno.ENETUNREACH
    out["egress_error"] = f"{type(e).__name__}: {e}"
    verdict = "BLOCKED" if out["egress_blocked"] else "NOT PROVEN BLOCKED (no answer, but a route exists)"
    print(f"\negress 192.0.2.1:9: {verdict} -> {type(e).__name__}: {e}")

(labkit.work() / "d3_sandbox.json").write_text(json.dumps(out))
if out["write_blocked"] and out["egress_blocked"]:
    print(f"\n[ok] execution is contained: the write and the egress are blocked, but the read still fired, "
          f"so {sink.CANARY} shows isolation limits blast radius rather than preventing the leak")
else:
    print("\n[!!] not contained: run this step in the sandbox service (docker compose run --rm sandbox ...)")
