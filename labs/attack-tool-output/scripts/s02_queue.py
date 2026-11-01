"""Step 2: the customer message has no canary; the tool result does. No model call. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/s02_queue.py
"""
import labkit

labkit.banner()

import desk  # noqa: E402

ticket = desk.poisoned_ticket()
print(f"ticket {ticket['id']} customer message has canary: {'yes' if desk.CANARY in ticket['message'] else 'no'}")
got = desk.post("/admin/agent/call", {"profile": "desk-broad", "tool": "read_ticket",
                                      "arguments": {"ticket_id": ticket["id"]}})
text = got["result"]
print(f"tool result has canary: {'yes' if desk.CANARY in text else 'no'}")
print(f"account on file: {ticket['account_on_file']}")
print(f"canary account is on file: {'yes' if desk.CANARY in desk.SPEC['accounts'] else 'no'}")
print("injection in front of the poisoned ticket's customer message (from assets/desk.json):")
print(desk.SPEC["injection"])
desk.save("s02.json", {"ticket": ticket["id"], "message_has_canary": desk.CANARY in ticket["message"],
                       "result_has_canary": desk.CANARY in text, "account_on_file": ticket["account_on_file"],
                       "canary_on_file": desk.CANARY in desk.SPEC["accounts"], "result": text})
