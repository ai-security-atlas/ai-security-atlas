"""Step 1: meet the shopping assistant. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/s01_meet_bot.py
Lists this lab's atlas-app profiles, asks Juniper two ordinary questions (seed 0) and prints the operator's audit
record of the last turn: the system prompt came from the operator, the customer only sent one message.
Writes work/meet.json.
"""
import json

import labkit

labkit.banner()

import shop  # noqa: E402

shop.note_backend()
print("profiles (GET /admin/profiles, this lab):")
profs = [p for p in shop.app("/admin/profiles") if p["lab"] == labkit.node_id()]
for p in profs:
    print(f"  {p['id']:<21} {p['summary']}")
print()
turns = []
for cid in ("hours", "returns"):
    q = shop.cases()[cid]["text"]
    r = shop.ask("pleak-shop", q, seed=0, session="lab19-meet")
    turns.append({"q": q, "a": r.text})
    print(f"customer: {q}\njuniper:  {' '.join(r.text.split())}\n")
a = shop.app("/admin/audit?n=1&session=lab19-meet")[-1]
ctx = " | ".join(f"{c['role']} from {c['source']} ({c['chars']} chars)" for c in a["context"])
prompt = shop.prompt_of("pleak-shop")
print("audit (operator view, last turn):")
print(f"  request {a['request_id']}  profile {a['profile']}  backend_model {a['backend_model']}")
print(f"  context: {ctx}")
print(f"  system prompt holds the staff code {shop.CANARY}: {'yes' if shop.CANARY in prompt else 'no'}")
models = json.dumps(shop.app("/v1/models"))
print(f"  prompt text in GET /v1/models or /admin/profiles: "
      f"{'yes' if shop.CANARY in models or shop.CANARY in json.dumps(profs) else 'no'}")
labkit.out("meet.json").write_text(json.dumps({"profiles": profs, "turns": turns, "context": a["context"],
                                               "prompt_chars": len(prompt)}, indent=1) + "\n")
