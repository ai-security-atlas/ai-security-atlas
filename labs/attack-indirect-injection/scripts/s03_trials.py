"""Step 3: the user's task or the document's? Measured over seeded trials. Run from labs/:
    docker compose run --rm workbench python attack-indirect-injection/scripts/s03_trials.py --trials 10
Three poisoned items (an email with a display:none block, a page with white text, a page with an instruction in
an image's alt text) and three controls in which the instruction never reaches the model (an email that hides it
in an HTML comment, a clean email, and the poisoned email pasted by Riley as she sees it). Each case runs N times
(seeds 0..N-1) through evalkit; every reply is rendered by the inbox app and the collector log is read per trial.
Step D1 reruns it with --profile xinj-inbox-spotlight and Step D4 with --profile xinj-quarantine (whose output
the app shows as plain text). Writes work/trials_<profile>.jsonl (one evalkit trial per line) and .json.
"""
import argparse
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import inbox as I  # noqa: E402
import trials as T  # noqa: E402

POISONED = ["email-hidden-div", "page-white-text", "page-alt-text"]
CONTROLS = ["email-comment", "email-clean", "pasted-visible"]

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="xinj-inbox",
                choices=["xinj-inbox", "xinj-inbox-spotlight", "xinj-quarantine"])
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

quarantine = a.profile == "xinj-quarantine"
policy = "auto"   # T.play shows quarantined replies as text whatever the policy
case_ids = POISONED + (CONTROLS if a.profile == "xinj-inbox" else ["email-clean"])
I.note_backend()
print(f"[note] profile {a.profile}, {a.trials} trials per case (seeds 0-{a.trials - 1}); the inbox app shows replies "
      + ("as plain text (no Markdown, nothing loads)" if quarantine else "as Markdown, images load automatically"),
      flush=True)
print(f"{'case':<17} {'channel':<32} {'in context':<11} {'task':<6} {'obeyed':<7} {'both':<6} {'exfil':<6} example reply",
      flush=True)
rows = {}


def show(case, part):
    c = T.counts(part)
    rows[case["id"]] = {**c, "channel": case["channel"], "kind": case["kind"], "example": T.example(part)}
    f = lambda k: f"{c[k]}/{c['n']}"
    print(f"{case['id']:<17} {case['channel'][:31]:<32} {'yes' if c['in_context'] else 'no':<11} {f('task'):<6} "
          f"{f('obeyed'):<7} {f('both'):<6} {f('exfil'):<6} {I.short(T.example(part), 46)}", flush=True)


ts = T.play(T.collect(a.profile, case_ids, a.trials), render_policy=policy, act="none", on_case=show)
pois = ts.filter(set(POISONED))
ctrl = ts.filter(set(case_ids) - set(POISONED))
print(f"poisoned, instruction in context ({len(POISONED)} cases x {a.trials}): task {pois.rate('task').fmt()}, "
      f"obeyed {pois.rate('obeyed').fmt()}, exfil {pois.rate('exfil').fmt()}")
print(f"controls, instruction not in context ({len(case_ids) - len(POISONED)} x {a.trials}): "
      f"obeyed {ctrl.rate('obeyed').fmt()}, exfil {ctrl.rate('exfil').fmt()}")
split = {"task only": 0, "both": 0, "obeyed only": 0, "neither": 0}
for t in pois:
    k = ("both" if t.grades["task"] else "obeyed only") if t.grades["obeyed"] else ("task only" if t.grades["task"] else "neither")
    split[k] += 1
print("poisoned trials split: " + " · ".join(f"{k} {v}" for k, v in split.items()))
if quarantine:
    print(f"canary in the summarizer's text: {pois.rate('canary').fmt()} (it never had the private value)")
c = ek.cost(ts)
print(f"cost: {ek.fmt_cost(c)}")
ts.save(labkit.out(f"trials_{a.profile}.jsonl"))
labkit.out(f"trials_{a.profile}.json").write_text(json.dumps({
    "profile": a.profile, "trials": a.trials, "render": "text" if quarantine else policy, "rows": rows, "split": split,
    "poisoned": {k: pois.rate(k).to_dict() for k in ("task", "obeyed", "exfil", "canary")},
    "controls": {k: ctrl.rate(k).to_dict() for k in ("task", "obeyed", "exfil")}, "cost": c,
    "digest": ts.digest()}, indent=1) + "\n")
