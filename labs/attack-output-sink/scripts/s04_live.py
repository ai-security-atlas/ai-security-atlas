"""Step 4 (optional, needs a model backend): generate the outputs live through atlas-app, then feed
them to the same sinks. Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/s04_live.py
Shows that the recorded outputs are representative: a live text-to-SQL helper and a live help-desk
assistant produce output that lands in the same SQL and HTML sinks. Live model replies vary.
"""
import json
import os
import urllib.request

import labkit

labkit.banner()

import sink  # noqa: E402

URL = os.environ.get("ATLAS_APP_URL", "http://atlas-app:8000").rstrip("/")


def ask(profile, question):
    body = json.dumps({"model": profile, "messages": [{"role": "user", "content": question}],
                       "temperature": 0, "max_tokens": 200, "user": "lab20"}).encode()
    req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]


sink.build_db(sink.db_path())
reps = sink.replies()

print("[note] live SQL sink (profile osink-sql):")
try:
    reply = ask("osink-sql", reps["sql_direct"]["question"])
except OSError as e:
    raise SystemExit(f"[!!] atlas-app unreachable at {URL} ({e}); add rag-agent to COMPOSE_PROFILES, set a backend in .env")
sql = sink.extract_sql(reply)
print(f"  model SQL: {sql}")
try:
    cols, rows = sink.run_sql(sql)
    fired = sink.rows_have_canary(rows)
    print(f"  executed -> {len(rows)} rows; canary in result: {fired}")
except Exception as e:
    print(f"  the generated SQL did not run ({type(e).__name__}: {e}); live replies vary")

print("\n[note] live HTML sink (profile osink-html):")
reply = ask("osink-html", reps["html"]["question"])
rendered = sink.render_html(reply)
print(f"  external requests: {len(rendered['requests'])}; carrying the canary: {len(rendered['leaks'])}")

print("\n[ok] live outputs reach the same sinks; the recorded run is the deterministic version")
