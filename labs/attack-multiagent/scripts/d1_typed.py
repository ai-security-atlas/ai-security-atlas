"""Defend D1: typed, data-only inter-agent messages. The researcher must answer in a fixed JSON
schema; the orchestrator validates it and renders the facts itself, so notices and directives that
do not fit a field never reach the planner. Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/d1_typed.py
"""
import labkit

labkit.banner()

import pipeline as P  # noqa: E402

P.note_backend()
print(f"[note] {P.WALK_N} trials (seeds 0-{P.WALK_N - 1}), typed channel, poisoned page", flush=True)
rows = P.measure("typed", P.WALK_N, "d1")
P.print_rates("typed", rows)
f = P.funnel(rows)
print(f"funnel note->report {f['hop1']}/{P.WALK_N} -> plan {f['hop2']}/{P.WALK_N} "
      f"-> outbox {f['harm']}/{P.WALK_N}")
retries = sum(r.get("parse_retries", 0) for r in rows)
parse_fails = sum(1 for r in rows if r.get("parse_error"))
ok = next(r for r in rows if not r.get("parse_error"))
facts, _, _ = P.parse_facts(ok["stages"]["researcher"]["reply"])
print(f"schema rejections retried: {retries} · trials the schema could not parse: {parse_fails}")
print("rendered facts the planner received (first parsed trial):")
print("  " + facts.replace("\n", "\n  "))
notice_in = sum(1 for r in rows if P.NOTICE in r["stages"]["researcher"]["reply"])
kept = sum(1 for r in rows if r["grades"]["notice_kept"])
print(f"store notice reached the researcher reply: {notice_in}/{P.WALK_N}")
print(f"store notice reached the ops digest: {kept}/{P.WALK_N} (the schema has no field for it)")
c = P.cost_rows(rows)
print(f"cost: {P.WALK_N} pipelines · {c['model_turns']} model turns · {c['total_tokens']} tokens")
P.save("d1.json", {"rows": P.pack_rows(rows), "funnel": f, "retries": retries, "parse_fails": parse_fails,
                   "facts_sample": facts, "notice_in_replies": notice_in, "notice_kept": kept, "cost": c})
