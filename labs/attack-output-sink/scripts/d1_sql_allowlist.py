"""Step D1: validate the SQL at the sink (sqlglot + single-SELECT allowlist). Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/d1_sql_allowlist.py
Runs the same model SQL as Step 2 through validate_sql() before any execution: the benign query
passes and still returns its rows, the two injection queries are rejected and never run.
"""
import json

import labkit

labkit.banner()

import sink  # noqa: E402

sink.build_db(sink.db_path())
reps = sink.replies()
cases = [("sql_benign", "benign: three cheapest products"),
         ("sql_direct", "direct injection: UNION onto secrets"),
         ("sql_indirect", "indirect injection: poisoned review")]

out = {"canary": sink.CANARY, "rows": {}}
for key, title in cases:
    sql = sink.extract_sql(reps[key]["model_reply"])
    print(f"\n== {title} ==")
    print(f"model SQL: {sql}")
    try:
        tables = sink.validate_sql(sql)
        cols, rows = sink.run_sql(sql, readonly=True)
        fired = sink.rows_have_canary(rows)
        print(f"allowlist: PASSED (reads {', '.join(tables)}) -> executed, {len(rows)} rows, canary {fired}")
        out["rows"][key] = {"gate": "passed", "reason": f"reads {', '.join(tables)}", "canary": fired}
    except sink.SqlRejected as e:
        print(f"allowlist: REJECTED ({e}); the query never reaches the database")
        out["rows"][key] = {"gate": "rejected", "reason": str(e), "canary": False}

(labkit.work() / "d1_sql_allowlist.json").write_text(json.dumps(out))
r = out["rows"]
if r["sql_benign"]["gate"] == "passed" and all(r[k]["gate"] == "rejected" for k in ("sql_direct", "sql_indirect")):
    print(f"\n[ok] the allowlist rejects both injections; {sink.CANARY} never leaves the database")
else:
    print("\n[!!] the allowlist did not pass the benign query and reject both injections")
print("[note] limitation: it validates the SQL, not whether the model was steered; a permitted table that "
      "itself holds sensitive rows still needs row-level authorization, not just a table allowlist")
