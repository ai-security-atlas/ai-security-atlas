"""Step 1: meet the support bot as its customers do. Run from labs/:
    docker compose run --rm workbench python attack-direct-injection/scripts/s01_meet_bot.py
Lists the deployed profiles, sends three ordinary customer messages to atlas-support and shows the
operator's audit entry for the last one. Writes work/meet.json.
"""
import json

import labkit

labkit.banner()

import bot  # noqa: E402

h = bot.get("/healthz")
print(f"[note] atlas-app {h['version']} at {bot.URL}; backend {h['backend']}: {h['base_url']} model {h['chat_model']}",
      flush=True)
print("profiles (GET /v1/models):")
for p in bot.get("/admin/profiles"):
    print(f"  {p['id']:<28} {p['summary']}")
msgs = [bot.benign()[i] for i in (0, 1, 5)]
turns = []
for m in msgs:
    reply, info, _ = bot.chat([{"role": "user", "content": m}], seed=0, session="lab06-meet")
    turns.append({"user": m, "reply": reply, "canary": info.get("canary")})
    print(f"\ncustomer: {m}\nbot:      {' '.join(reply.split())}", flush=True)
last = bot.get("/admin/audit?n=1&session=lab06-meet")[-1]
print("\naudit (operator view, last turn):")
print(f"  request {last['request_id']}  profile {last['profile']}  backend_model {last['backend_model']}")
print("  context: " + " | ".join(f"{c['role']} from {c['source']} ({c['chars']} chars)" for c in last["context"]))
print(f"  findings {last['findings']}  blocked_by {last['blocked_by']}  canary {last['canary']}")
labkit.out("meet.json").write_text(json.dumps({"model": h["chat_model"], "turns": turns,
                                               "audit": last}, indent=1) + "\n")
