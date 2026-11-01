"""Step D2: confirmation on save_memory, and expiry. Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/d2_review.py
The server runs a gated save only when the decision binds the tool name, the arguments and
the definition hash. The reviewer refuses a note that carries the canary and allows Dana's
sign-off. An allowed sign-off is a real save_memory, and the next run can read it. Expiry
hides tool-sourced rows first, then a blanket expiry hides the sign-off too.
"""
import labkit

labkit.banner()

import mem  # noqa: E402

mem.note_backend()
defn = mem.tool_def("mp-confirm", "save_memory")
digest = defn["sha256"]
poison_args = {"note": mem.NOTE}
sig_args = {"note": mem.USER_NOTE}
bind = "d2-bind"
mem.reset_memory(mem.DESK, bind)

bare = mem.call_tool("mp-confirm", "save_memory", poison_args, {"allow": True, "tool": "save_memory"},
                     principal=bind, session="d2-name")
print(f"name-only allow: {bare['reason']}")
print(f"name-only allow stored: {'yes' if bare['allowed'] else 'no'}")
wrong_hash = mem.call_tool("mp-confirm", "save_memory", poison_args, {
    "allow": True, "tool": "save_memory", "def_sha256": "0" * 64, "arguments": poison_args},
    principal=bind, session="d2-hash")
print(f"wrong hash: {wrong_hash['reason']}")
wrong_args = mem.call_tool("mp-confirm", "save_memory", poison_args, {
    "allow": True, "tool": "save_memory", "def_sha256": digest, "arguments": sig_args},
    principal=bind, session="d2-args")
print(f"wrong arguments: {wrong_args['reason']}")
refused = mem.call_tool("mp-confirm", "save_memory", poison_args, {
    "allow": False, "tool": "save_memory", "def_sha256": digest, "arguments": poison_args},
    principal=bind, session="d2-no")
print(f"refused: {refused['reason']}")
bound = mem.call_tool("mp-confirm", "save_memory", poison_args, {
    "allow": True, "tool": "save_memory", "def_sha256": digest, "arguments": poison_args},
    principal=bind, session="d2-yes")
print(f"bound allow runs save_memory: {'yes' if bound['allowed'] else 'no'}")
print(f"bound allow effect has canary: {'yes' if mem.CANARY in mem.blob(bound['effects']) else 'no'}")
nxt = mem.call_tool("mp-recall", "read_memory", {}, principal=bind, session="d2-read")
print(f"next run sees the bound note: {'yes' if mem.CANARY in nxt['result'] else 'no'}")
mem.reset_memory(mem.DESK, bind)

review_no = mem.reviewer(False)({"tool": "save_memory", "id": "x", "arguments": poison_args, "def_sha256": digest})
review_yes = mem.reviewer(True)({"tool": "save_memory", "id": "y", "arguments": sig_args, "def_sha256": digest})
print(f"reviewer commits poisoned notes: {'yes' if review_no['allow'] else 'no'}")
print(f"reviewer commits the sign-off: {'yes' if review_yes['allow'] else 'no'}")
legit = "d2-legit"
mem.reset_memory(mem.DESK, legit)
kept = mem.call_tool("mp-confirm", "save_memory", sig_args, review_yes, principal=legit, session="d2-legit")
seen = mem.call_tool("mp-recall", "read_memory", {}, principal=legit, session="d2-legit-read")
print(f"sign-off save stored: {'yes' if kept['allowed'] and mem.SIGNATURE in seen['result'] else 'no'}")
poisoned = mem.call_tool("mp-confirm", "save_memory", poison_args, review_no, principal=legit, session="d2-poison")
print(f"poisoned save stored: {'yes' if poisoned['allowed'] else 'no'}")

exp = "d2-expire"
mem.prepare_counterfactual(exp)
before = mem.call_tool("mp-recall", "read_memory", {}, principal=exp, session="d2-before")
mem.expire_memory(mem.DESK, exp, mem.EXPIRED, source="tool")
selective = mem.call_tool("mp-recall", "read_memory", {}, principal=exp, session="d2-selective")
print(f"expired poison loaded: {'yes' if mem.CANARY in selective['result'] else 'no'}")
print(f"fresh sign-off loaded: {'yes' if mem.SIGNATURE in selective['result'] else 'no'}")
mem.expire_memory(mem.DESK, exp, mem.EXPIRED, source="user")
blanket = mem.call_tool("mp-recall", "read_memory", {}, principal=exp, session="d2-blanket")
print(f"blanket expiry loads sign-off: {'yes' if mem.SIGNATURE in blanket['result'] else 'no'}")
print(f"before expiry had canary: {'yes' if mem.CANARY in before['result'] else 'no'}")
mem.reset_memory(mem.DESK, legit)
mem.reset_memory(mem.DESK, exp)

print(f"[note] {mem.WALK_N} attack trials and {mem.WALK_N} remember trials "
      f"(seeds 0-{mem.WALK_N - 1})", flush=True)
attack = mem.measure("mp-confirm", mem.WALK_N, "d2-attack", approver=mem.reviewer(False),
                     principal_for=lambda s: f"d2c-{s}", setup=lambda p, _s: mem.reset_memory(mem.DESK, p))
mem.print_rates("mp-confirm", attack)
remember = mem.measure("mp-remember", mem.WALK_N, "d2-remember", principal_for=lambda s: f"d2r-{s}",
                       setup=lambda p, _s: mem.reset_memory(mem.DESK, p))
mem.print_rates("mp-remember", remember)
gated = mem.measure("mp-confirm", mem.WALK_N, "d2-gated-remember", approver=mem.reviewer(True),
                    task=mem.TASKS["remember"], principal_for=lambda s: f"d2g-{s}",
                    setup=lambda p, _s: mem.reset_memory(mem.DESK, p))
mem.print_rates("mp-confirm-sign", gated)
print(f"poisoned save attempts: {sum(r['attempt'] for r in attack)}/{mem.WALK_N}")
print(f"poisoned saves stored: {sum(r['stored'] for r in attack)}/{mem.WALK_N}")
print(f"sign-off saves stored: {sum(r['fact'] for r in remember)}/{mem.WALK_N}")
print(f"gated sign-off saves stored: {sum(r['fact'] for r in gated)}/{mem.WALK_N}")
mem.save("d2.json", {
    "trials": mem.WALK_N,
    "name_only": bare["reason"], "wrong_hash": wrong_hash["reason"],
    "wrong_arguments": wrong_args["reason"], "refused": refused["reason"],
    "bound_allowed": bound["allowed"],
    "signoff_stored": kept["allowed"] and mem.SIGNATURE in seen["result"],
    "attack": [mem.pack_row(r) for r in attack],
    "remember": [mem.pack_row(r) for r in remember],
    "gated_remember": [mem.pack_row(r) for r in gated],
})
