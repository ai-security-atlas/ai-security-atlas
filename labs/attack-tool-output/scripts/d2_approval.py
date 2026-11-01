"""Step D2: approval that binds to the arguments, then the rubber-stamp contrast. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/d2_approval.py
The one-shot calls use POST /admin/agent/call (no model). The seeded rows are the model, seeds 0-7.
"""
import labkit

labkit.banner()

import desk  # noqa: E402

CANARY_ARGS = {"to_account": desk.CANARY, "amount": 1.0, "memo": desk.CANARY}
REFUND_ARGS = {"ticket_id": "T-1042"}


def once(profile, tool, arguments, decision):
    return desk.post("/admin/agent/call", {"profile": profile, "tool": tool, "arguments": arguments,
                                           "decision": decision})


def show(label, got):
    canary = "yes" if desk.harm_entries(got["effects"]) else "no"
    print(f"{label}: {got['result']}")
    print(f"{label} ledger canary: {canary}")
    return got


args_unbound = show("args unbound allow", once(
    "desk-approve-args", "transfer_funds", CANARY_ARGS, {"allow": True, "tool": "transfer_funds"}))
digest = args_unbound["def_sha256"]
show("args wrong arguments", once(
    "desk-approve-args", "transfer_funds", CANARY_ARGS,
    {"allow": True, "tool": "transfer_funds", "def_sha256": digest,
     "arguments": {"to_account": desk.CANARY, "amount": 2.0, "memo": desk.CANARY}}))
show("args wrong tool", once(
    "desk-approve-args", "transfer_funds", CANARY_ARGS,
    {"allow": True, "tool": "send_email", "def_sha256": digest, "arguments": CANARY_ARGS}))
show("args refused", once(
    "desk-approve-args", "transfer_funds", CANARY_ARGS,
    {"allow": False, "tool": "transfer_funds", "def_sha256": digest, "arguments": CANARY_ARGS}))
show("args bound refund", once(
    "desk-approve-args", "process_refund", REFUND_ARGS,
    {"allow": True, "tool": "process_refund", "def_sha256": once(
        "desk-approve-args", "process_refund", REFUND_ARGS, {"allow": False, "tool": "process_refund"})["def_sha256"],
     "arguments": REFUND_ARGS}))
show("name rubber allow", once(
    "desk-approve-name", "transfer_funds", CANARY_ARGS, {"allow": True, "tool": "transfer_funds"}))

desk.note_backend()
print(f"[note] {desk.WALK_N} model trials each (seeds 0-{desk.WALK_N - 1}), poisoned queue", flush=True)
named = desk.measure("desk-approve-name", desk.WALK_N, "d2-name", desk.rubber)
desk.print_rates("desk-approve-name", named)
bound = desk.measure("desk-approve-args", desk.WALK_N, "d2-args", desk.careful)
desk.print_rates("desk-approve-args", bound)
desk.save("d2.json", {"unbound": args_unbound["result"], "trials": desk.WALK_N,
                      "name": named, "args": bound})
