"""Evaluate: measure each sink condition and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

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


got = {
    "sql-naive": sql_outcome("sql_direct", defended=False),
    "sql-allowlist": sql_outcome("sql_direct", defended=True),
    "html-naive": html_outcome(defended=False),
    "html-sanitized": html_outcome(defended=True),
}

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"canary: {sink.CANARY}\n")
print(f"{'condition':<18} {'expected':<10} got")
for cond, want in expected.items():
    print(f"{cond:<18} {str(want):<10} {got.get(cond)}")

(labkit.work() / "evaluate.json").write_text(json.dumps({"got": got, "canary": sink.CANARY}))
diff = [c for c, want in expected.items() if got.get(c) != want]
print("\nRESULT: REPRODUCED" if not diff else f"\nRESULT: MISMATCH ({', '.join(diff)})")
