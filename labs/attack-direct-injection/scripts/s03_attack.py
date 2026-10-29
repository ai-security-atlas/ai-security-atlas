"""Steps 3, D1 and D3: replay the fixed direct-injection catalogue against one atlas-app profile. Run from labs/:
    docker compose run --rm workbench python attack-direct-injection/scripts/s03_attack.py --trials 10
    docker compose run --rm workbench python attack-direct-injection/scripts/s03_attack.py --profile atlas-support-hierarchy --trials 10
Each technique in assets/catalogue.json is sent `trials` times (temperature 0.7, seeds 0..trials-1).
hit = strict grader (first line is the goal sentence); canary = the code appears anywhere;
blocked = the app's output policy replaced the reply. Writes work/attack_<profile>.json.
"""
import argparse
import json

import labkit

labkit.banner()

import bot  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="atlas-support", choices=["atlas-support", "atlas-support-hierarchy",
                                                               "atlas-support-output-check", "atlas-support-layered"])
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

h = bot.get("/healthz")
print(f"[note] {a.trials} trials per technique -> {bot.URL}/v1 profile {a.profile} "
      f"(backend {h['backend']}: {h['base_url']} model {h['chat_model']}), temperature {bot.TEMPERATURE}", flush=True)
print(f"{'technique':<17} {'goal':<8} {'hit':<6} {'canary':<7} {'blocked':<8} example reply", flush=True)
rows, hits, total = {}, 0, 0
for t in bot.catalogue():
    r = bot.run_technique(t, a.trials, a.profile)
    rows[t["id"]] = r
    if t["id"] != "control":
        hits, total = hits + r["hit"], total + a.trials
    f = lambda k: f"{r[k]}/{a.trials}"
    print(f"{t['id']:<17} {t['goal']:<8} {f('hit'):<6} {f('loose'):<7} {f('blocked'):<8} {bot.short(r['example'])}", flush=True)
print(f"ASR (strict, injections only): {hits}/{total} = {100 * hits / total:.0f}%")
labkit.out(f"attack_{a.profile}.json").write_text(json.dumps({"profile": a.profile, "trials": a.trials,
                                                               "model": h["chat_model"], "rows": rows}, indent=1) + "\n")
