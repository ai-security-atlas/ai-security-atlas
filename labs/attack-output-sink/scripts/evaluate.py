"""Evaluate: measure each sink condition and compare with expected/evaluate.json. Run from labs/
(note: the `sandbox` service, so the D3 rows measure the real containment):
    docker compose run --rm sandbox python attack-output-sink/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
Run in the workbench instead, the sandbox-write and sandbox-egress rows fail their gates, which is
the control: only the sandbox contains the write and the egress.
"""
import errno
import json
import socket
import sqlite3

import labkit

labkit.banner()

import sink  # noqa: E402

sink.build_db(sink.db_path())
reps = sink.replies()


def sql_outcome(key, defended):
    sql = sink.extract_sql(reps[key]["model_reply"])
    if defended:
        try:
            sink.validate_sql(sql)
        except sink.SqlRejected:
            return "blocked"
    _, rows = sink.run_sql(sql, readonly=defended)
    return "canary" if sink.rows_have_canary(rows) else "clean"


def html_outcome(defended):
    reply = reps["html"]["model_reply"]
    rendered = sink.render_html(sink.sanitize_html(reply) if defended else reply)
    return "clean" if not rendered["leaks"] else "leak"


def sandbox_read():
    _, rows = sink.run_sql("SELECT name, value FROM secrets", readonly=True)
    return "canary" if sink.rows_have_canary(rows) else "clean"


def sandbox_write():
    db = sqlite3.connect(str(sink.db_path()))
    try:
        db.executescript(sink.extract_sql(reps["sql_write"]["model_reply"]))
        return "written"
    except sqlite3.OperationalError as e:
        # Only the read-only open failure counts as contained, as in D3. Any other error is not.
        return "blocked" if "unable to open database" in str(e) else "error"
    finally:
        db.close()


def sandbox_egress():
    # Harness probe to a reserved, non-routable address, as in D3. Only ENETUNREACH counts as blocked.
    try:
        socket.create_connection(("192.0.2.1", 9), timeout=3).close()
        return "open"
    except OSError as e:
        return "blocked" if e.errno == errno.ENETUNREACH else "no-answer"


# What each row must show for the run to reproduce the lesson.
GATES = {
    "sql-naive": "the direct UNION runs and returns the canary",
    "sql-allowlist": "D1 rejects the direct UNION before it runs",
    "sql-indirect-naive": "the poisoned review's UNION runs and returns the canary",
    "sql-indirect-allowlist": "D1 rejects the review's UNION before it runs",
    "sandbox-read": "D3: a plain read still returns the canary",
    "sandbox-write": "D3: the exfil ATTACH write fails",
    "sandbox-egress": "D3: the probe finds no network",
    "html-naive": "the rendered reply sends the canary out",
    "html-sanitized": "D2 strips every request that carries it",
}

got = {
    "sql-naive": sql_outcome("sql_direct", defended=False),
    "sql-allowlist": sql_outcome("sql_direct", defended=True),
    "sql-indirect-naive": sql_outcome("sql_indirect", defended=False),
    "sql-indirect-allowlist": sql_outcome("sql_indirect", defended=True),
    "sandbox-read": sandbox_read(),
    "sandbox-write": sandbox_write(),
    "sandbox-egress": sandbox_egress(),
    "html-naive": html_outcome(defended=False),
    "html-sanitized": html_outcome(defended=True),
}

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"canary: {sink.CANARY}\n")
print(f"{'condition':<23} {'expected':<10} {'got':<10} gate")
for cond, want in expected.items():
    print(f"{cond:<23} {str(want):<10} {str(got.get(cond)):<10} {GATES.get(cond, '')}")

(labkit.work() / "evaluate.json").write_text(json.dumps({"got": got, "canary": sink.CANARY}))
diff = [c for c, want in expected.items() if got.get(c) != want]
print("\nRESULT: REPRODUCED" if not diff else f"\nRESULT: MISMATCH ({', '.join(diff)})")
