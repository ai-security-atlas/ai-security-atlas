"""Step 1 (System): the two sinks and the over-privileged database connection. Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/s01_app.py
Builds the shop database and shows what each sink does with model output, with no attack yet.
"""
import json

import labkit

labkit.banner()

import sink  # noqa: E402

sink.build_db(sink.db_path())

print("[note] two places where model output is consumed by the app:")
print("  SQL sink   analytics helper runs the model's SQL against sqlite3 (connection sees every table)")
print("  HTML sink  help-desk page renders the model's HTML/Markdown reply verbatim\n")

# The schema the model is told about, and the table it is not.
tables = [r[0] for r in sink.run_sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")[1]]
print(f"database tables: {', '.join(tables)}")
print(f"  model is told about : {', '.join(sink.ALLOWED_TABLES)}")
hidden = [t for t in tables if t not in sink.ALLOWED_TABLES]
print(f"  not in the prompt   : {', '.join(hidden)}  <- but the live connection can still read it")

# A benign question and its benign SQL, executed normally.
r = sink.replies()["sql_benign"]
sql = sink.extract_sql(r["model_reply"])
cols, rows = sink.run_sql(sql)
print(f"\nbenign question: {r['question']}")
print(f"model SQL      : {sql}")
print(f"result ({', '.join(cols)}):")
for row in rows:
    print(f"  {row}")
can = sink.run_sql("SELECT value FROM secrets")[1][0][0]
print(f"\nsecrets.value (never shown to a customer): {can}")

(labkit.work() / "s01_app.json").write_text(json.dumps({
    "tables": tables, "allowed": list(sink.ALLOWED_TABLES), "hidden": hidden,
    "benign_question": r["question"], "benign_sql": sql, "benign_cols": cols,
    "benign_rows": rows, "canary": can}))
if not sink.rows_have_canary(rows):
    print("\n[ok] system shown; no attack yet, no canary in any reply")
else:
    print("\n[!!] the benign query returned the canary")
