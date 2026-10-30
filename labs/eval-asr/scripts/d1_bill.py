"""Step D1: the defense's bill. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/d1_bill.py --trials 10
Measures atlas-app's two defenses next to the baseline on the same attack set and the same seeds:
  hierarchy     atlas-support-hierarchy (prompt-level instruction hierarchy; replies from Step 1)
  output check  atlas-support-output-check (deterministic policy check on the reply; run here)
For each: ASR with the judge from Step 2, the change against the baseline with a Newcombe interval, the share of
60 benign customer messages (assets/benign.json, seed 0) whose honest answer the defense replaced, and the cost
per benign request (prompt tokens, median latency). Writes work/d1_*.jsonl and .manifest.json.
"""
import argparse

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import subject as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

judge = S.judge()
t = S.target("atlas-support")
print(f"[note] {S.URL}/v1 -> backend {t['backend']}: {t['base_url']} model {t['model']}; judge {judge.model} on "
      f"{judge.chat.base_url}", flush=True)
inj = lambda tr: tr.case_id != "control"
rows = []
for label, prof in [("baseline", "atlas-support"), ("hierarchy", "atlas-support-hierarchy"),
                    ("output check", "atlas-support-output-check")]:
    ts, m = S.load_run(f"s01_{prof}")
    if ts is None or m["seeds"]["count"] != a.trials:
        print(f"[note] {prof}: {a.trials} trials per case -> {S.URL}/v1", flush=True)
        ts, m = S.run("d1_bill", f"d1_{prof}", prof, S.attack_cases(), a.trials, {"catalogue": S.CATALOGUE})
        ts.grade(judge)
        S.save_run(f"d1_{prof}", ts, dict(m, graders=m["graders"] + ["judge"], judges={"judge": S.judge_info(judge)}))
    else:
        print(f"[note] {prof}: reusing the Step 1 replies (same seeds 0-{a.trials - 1})", flush=True)
        ts.grade(judge)
    ben, mbn = S.run("d1_bill", f"d1_benign_{prof}", prof, S.benign(), 1, {"benign": labkit.inp("assets/benign.json")})
    rows.append((label, prof, ts, ben))

base_rate = rows[0][2].rate("judge", inj)
print(f"\n{'condition':<13} {'ASR (judge)':<20} {'change [95% CI]':<17} {'benign blocked':<19} {'tokens/req':<11} p50 latency")
for label, prof, ts, ben in rows:
    r = ts.rate("judge", inj)
    d, lo, hi = ek.diff_ci(r, base_rate)
    ch = "-" if label == "baseline" else f"{100 * d:+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]"
    fp = ek.Rate.of(bool(t.meta.get("blocked_by")) for t in ben)
    c = ek.cost(ben)
    print(f"{label:<13} {r.fmt():<20} {ch:<17} {fp.fmt():<19} {c['prompt_tokens'] / c['queries']:<11.0f} "
          f"{c['latency_ms_p50']:.0f} ms", flush=True)

print("\nbenign messages whose answer the output check replaced:")
benign_msgs = {c["id"]: c["messages"][0]["content"] for c in S.benign()}
for t in rows[2][3]:
    if t.meta.get("blocked_by"):
        print(f"  {t.case_id}  {', '.join(t.meta.get('findings') or [])}: {S.short(benign_msgs[t.case_id], 78)}")
print(f"\njudge cost: {ek.fmt_cost(ek.cost(judge.calls))}")
