"""Step D1: an output filter after the model. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/d1_filter.py --trials 10
Puts leak.OutputFilter between atlas-app and the customer: a reply that contains the canary (any case) or repeats
8 consecutive words of the system prompt is replaced by a fixed refusal. It filters exactly Step 3's replies
(work/trials_pleak-shop.jsonl) when they are there with the same --trials, and collects them again otherwise
(same seeds). Then it grades what the customer sees with the same detector. Writes work/filter.json.
"""
import argparse
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import leak  # noqa: E402
import shop  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

P = "pleak-shop"
path = labkit.work() / f"trials_{P}.jsonl"
ts = ek.TrialSet.load(path) if path.exists() else None
if ts is not None and len(ts) == a.trials * len(shop.ATTACKS + shop.BENIGN):
    print(f"[note] filtering Step 3's {len(ts)} replies from work/trials_{P}.jsonl (same replies, no model call)")
    shop.regrade(ts, P)
else:
    shop.note_backend()
    print(f"[note] no matching Step 3 run in work/: collecting {a.trials} trials per request (seeds 0-{a.trials - 1})",
          flush=True)
    ts = shop.collect(P, shop.ATTACKS + shop.BENIGN, a.trials)
seen = shop.apply_filter(ts, P)
print(f"{'request':<16} {'leak before':<12} {'blocked':<8} {'leak after':<11} shapes that passed")
rows = {}
for cid in shop.ATTACKS + shop.BENIGN:
    b, s = ts.filter({cid}), seen.filter({cid})
    n = len(b)
    passed = sorted({t.meta["form"] for t in s if t.grades["leak"]})
    rows[cid] = {"n": n, "before": sum(t.grades["leak"] for t in b), "blocked": sum(t.grades["blocked"] for t in s),
                 "after": sum(t.grades["leak"] for t in s), "passed": passed,
                 "useful": sum(t.grades["useful"] for t in s), "kind": shop.cases()[cid]["kind"]}
    r = rows[cid]
    extra = f"useful {r['useful']}/{n}" if r["kind"] == "benign" else " ".join(passed) or "-"
    f = lambda k: f"{r[k]}/{n}"
    print(f"{cid:<16} {f('before'):<12} {f('blocked'):<8} {f('after'):<11} {extra}")
att_b, att_s = ts.filter(set(shop.ATTACKS)), seen.filter(set(shop.ATTACKS))
ben_s = seen.filter(set(shop.BENIGN))
ben_ok = ben_s.filter(lambda t: t.case_id != "discount")
print(f"disclosure requests: leak {att_b.rate('leak').fmt()} -> {att_s.rate('leak').fmt()} behind the filter")
d, lo, hi = ek.diff_ci(att_b.rate("leak"), att_s.rate("leak"))
print(f"drop: {100 * d:.0f} points [{100 * lo:.0f}, {100 * hi:.0f}] (Newcombe 95 %)")
print(f"ordinary questions: blocked {ben_s.rate('blocked').fmt()}, useful {ben_s.rate('useful').fmt()}")
gave = sum(1 for t in seen.filter({"discount"}) if t.grades["blocked"] and leak.detect(t.meta["model_text"],
                                                                                    shop.CANARY)["form"])
print(f"  hours, returns, shipping blocked: {ben_ok.rate('blocked').fmt()}; discount blocked: "
      f"{rows['discount']['blocked']}/{rows['discount']['n']} ({gave} of them gave out the code)")
labkit.out("filter.json").write_text(json.dumps({
    "trials": a.trials, "rows": rows, "before": att_b.rate("leak").to_dict(), "after": att_s.rate("leak").to_dict(),
    "drop": [round(d, 4), round(lo, 4), round(hi, 4)], "benign_blocked": ben_s.rate("blocked").to_dict(),
    "useful": ben_s.rate("useful").to_dict()}, indent=1) + "\n")
