"""Step 5: past the end of its turn, the model writes the next speaker's message too. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s05_runaway_turn.py
Reads Step 3's raw continuations (no model call) and feeds them to a naive app that stores whatever comes back.
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

s3 = D.read("s03_two_behaviors.json", "Step 3")
print("what each model wrote after its own reply (Step 3, 48 tokens, no stop rule)")
print("model     format  continuations with a fabricated user message  turns written  roles")
rows = []
for r in s3["rows"]:
    users = sum(any(role == "user" for role, _ in t) for t in r["turns"])
    n_turns = sum(len(t) for t in r["turns"])
    roles = {}
    for t in r["turns"]:
        for role, _ in t:
            roles[role] = roles.get(role, 0) + 1
    rows.append({"model": r["model"], "fmt": r["fmt"], "user": users, "turns": n_turns, "roles": roles, "n": r["n"]})
    rl = " ".join(f"{k} {v}" for k, v in roles.items()) or "-"
    print(f"{r['model']:<9} {r['fmt']:<7} {users}/{r['n']}{'':<43} {n_turns:>3}            {rl}")

inst = next(r for r in s3["rows"] if r["model"] == "instruct" and r["fmt"] == "chat")
i = next((k for k, t in enumerate(inst["turns"]) if any(role == "user" for role, _ in t)), None)
example = None
if i is not None:
    q = D.QUESTIONS[i]
    fake = next(body for role, body in inst["turns"][i] if role == "user")
    # The naive app: append the raw continuation to the history, then parse the history by its role markers.
    history = [("system", D.SYSTEM), ("user", q), ("assistant", inst["replies"][i])] + inst["turns"][i]
    example = {"question": q, "reply": inst["replies"][i], "fake": fake, "history": history}
    print(f"instruct, chat, {q!r}:")
    print(f"   reply      {inst['replies'][i][:70]!r}")
    print(f"   then user  {fake[:70]!r}")
    print("a naive app that stores the raw continuation and parses it by role markers now holds:")
    for role, body in history:
        tag = "   <- the user never sent this" if (role, body) in inst["turns"][i] and role == "user" else ""
        print(f"   {role:<9} {body[:58]!r}{tag}")
    sent = 1
    stored = sum(role == "user" for role, _ in history)
    print(f"user messages sent: {sent}, user messages in the stored history: {stored}")
readable = [r for r in rows if r["fmt"] == "plain" or r["model"] == "instruct"]
total, n = sum(r["user"] for r in readable), sum(r["n"] for r in readable)
print(f"with no stop rule, {total} of {n} continuations in the readable conditions (base plain, instruct chat, "
      f"instruct plain) went on to write a message for the user")
D.save("s05_runaway_turn.json", {"rows": rows, "example": example})
