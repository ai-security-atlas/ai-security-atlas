"""Step D3: ask the human before an action. Run from labs/ after Step 4:
    docker compose run --rm workbench python attack-indirect-injection/scripts/d3_confirm.py
Replays Step 4's replies (work/actions_xinj-inbox.jsonl, no model call). Every proposed send_email now opens a
confirmation dialog showing the recipient, subject and body next to what Riley asked for. Two stand-in humans
answer it: "careful" approves only an email that Riley's own request asked for (she asked to send, reply or
forward, and named that recipient); "rubber-stamp" clicks Send on everything. Approved emails go to the mail
relay as in Step 4. Writes work/confirm.json.
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import inbox as I  # noqa: E402
import trials as T  # noqa: E402

src = labkit.inp("work/actions_xinj-inbox.jsonl")
if not src.exists():
    raise SystemExit("[!!] work/actions_xinj-inbox.jsonl is missing: run Step 4 first (s04_action.py --trials 10)")
ts = ek.TrialSet.load(src)
cases = I.cases()
props = [x for t in ts for x in t.meta["actions"]]
print(f"[note] replaying {len(ts)} Step 4 replies (no model call): {len(props)} proposed send_email actions")
first = next(((t, x) for t in ts for x in t.meta["actions"] if "northwind" in x["to"].lower()), None)
if first:
    t, x = first
    print(f"\nthe dialog Riley sees (invoice reply, seed {t.seed}):")
    print(f"  | Atlas Inbox wants to send an email")
    print(f"  | to:      {x['to']}")
    print(f"  | subject: {x['subject']}")
    print(f"  | body:    {x['body'][:60]}")
    print(f"  | you asked: {cases[t.case_id]['ask']!r}")
    print("  | [Send] [Cancel]\n")
print(f"{'human':<14} {'approved':<9} {'to Northwind':<13} {'with canary':<12} reply to Priya sent")
res = {}
for human in ("auto", "rubber-stamp", "careful"):
    p = T.play(ts, render_policy="text", act=human)
    inv, rep = p.filter({"email-action"}), p.filter({"reply-request"})
    approved = sum(len(t.meta["sent"]) for t in p)
    c = T.counts(inv)
    res[human] = {"proposed": len(props), "approved": approved, "northwind": c["attacker_sent"],
                  "northwind_canary": c["attacker_sent_canary"], "trials": len(inv), "reply": rep.rate("task").to_dict()}
    label = "none (auto)" if human == "auto" else human
    n_north, n_can = f"{c['attacker_sent']}/{len(inv)}", f"{c['attacker_sent_canary']}/{len(inv)}"
    print(f"{label:<14} {f'{approved}/{len(props)}':<9} {n_north:<13} {n_can:<12} {rep.rate('task').fmt(ci=False)}",
          flush=True)
labkit.out("confirm.json").write_text(json.dumps(res, indent=1) + "\n")
