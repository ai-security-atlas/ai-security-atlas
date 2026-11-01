"""Step 2 (Attack -> Mechanism -> Impact): the SQL sink. Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/s02_sql_sink.py
Replays recorded model SQL for a direct question and an indirect (poisoned review) one, runs each
verbatim against the database, and shows the canary row the executed query returns.
"""
import json

import labkit

labkit.banner()

import sink  # noqa: E402

sink.build_db(sink.db_path())

out = {"canary": sink.CANARY, "cases": {}}
reps = sink.replies()
for key, title in (("sql_direct", "direct: the customer asks for the secrets table"),
                   ("sql_indirect", "indirect: a poisoned review in the helper's context carries the order")):
    r = reps[key]
    sql = sink.extract_sql(r["model_reply"])
    cols, rows = sink.run_sql(sql)
    fired = sink.rows_have_canary(rows)
    print(f"\n== {title} ==")
    print(f"question : {r['question']}")
    print(f"model SQL: {sql}")
    print(f"executed verbatim -> {len(rows)} rows ({', '.join(cols)}):")
    for row in rows:
        mark = "  <- CANARY" if any(sink.CANARY in str(v) for v in row) else ""
        print(f"  {row}{mark}")
    print(f"canary in result: {fired}")
    out["cases"][key] = {"question": r["question"], "sql": sql, "cols": cols, "rows": rows, "canary": fired}

(labkit.work() / "s02_sql_sink.json").write_text(json.dumps(out))
if all(c["canary"] for c in out["cases"].values()):
    print(f"\n[ok] the sink executes model output verbatim; {sink.CANARY} leaves the secrets table in both cases")
else:
    print("\n[!!] the canary did not come back in every case; check assets/replies.json and shop.db")
