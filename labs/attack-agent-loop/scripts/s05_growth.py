"""Step 5: why the cost grows by the square — a replay of Step 3's saved turns. No model call.
Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s05_growth.py
Each model turn re-sends the whole conversation, and each loop iteration appends another tool
result, so the prompt grows linearly and the cumulative token bill grows quadratically.
"""
import json

import labkit

labkit.banner()

import loop  # noqa: E402

s03 = json.loads(labkit.out("s03.json").read_text())
turns = s03["first_turns"]
run = s03["rows"][0]
n = len(turns)
print(f"replaying seed 0 of Step 3 ({n} model turns, cap {loop.HARD_CAP})")
print("turn  prompt_tokens  cumulative_prompt")
shown = {1, 2, 5, 10, 20, 30, 40, n}
total = 0
for t in turns:
    total += t["prompt_tokens"]
    if t["step"] in shown:
        print(f"{t['step']:<5} {t['prompt_tokens']:>13,} {total:>16,}")
first_prompt = turns[0]["prompt_tokens"]
last_prompt = turns[-1]["prompt_tokens"]
per_turn = (last_prompt - first_prompt) / max(n - 1, 1)
print(f"prompt grew from {first_prompt:,} to {last_prompt:,} tokens: about {per_turn:,.0f} more per turn")
print(f"if {n} turns had each cost the first turn's {first_prompt:,} tokens, the run would bill "
      f"{n * first_prompt:,}; it billed {run['usage'].get('total_tokens', 0):,}")
print(f"re-sending the conversation is what turns a linear loop into a quadratic token bill")
loop.save("s05.json", {"turns": n, "first_prompt": first_prompt, "last_prompt": last_prompt,
                       "per_turn": round(per_turn), "billed": run["usage"].get("total_tokens", 0),
                       "linear_equivalent": n * first_prompt,
                       "curve": [[t["step"], t["prompt_tokens"]] for t in turns if t["step"] in shown]})
