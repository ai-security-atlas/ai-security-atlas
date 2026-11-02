"""Evaluate: the three bugs and the three defenses, against expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/evaluate.py
The stub counts are exact. A seeded live cross-check is printed when a model backend answers;
it does not decide RESULT. Ends with RESULT: REPRODUCED or RESULT: MISMATCH (...).
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import sleak  # noqa: E402

sleak.note_backend()
got = sleak.counts()
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<28} {'expected':<10} got")
for key, want in expected.items():
    print(f"{key:<28} {str(want):<10} {got.get(key)}")

g = ek.Gate("attack-session-leak")
g.require("baseline keeps Copperleaf's code", got["baseline_own"] == 1)
g.require("baseline hides it from Harbor", got["baseline_cross"] == 0)
g.require("prompt cache serves the canary to Harbor", got["cache_leak"] == 1 and got["cache_source_hit"] == 1)
g.require("principal cache key stops that leak", got["cache_leaks_isolated"] == 0)
g.at_least("extra retrievals when the key includes the principal",
           got["cache_retrievals_isolated"] - got["cache_retrievals_shared"], 1)
g.require("open retrieval leaks", got["retrieval_leak"] == 1 and got["retrieval_unauth"] >= 1)
g.require("where-filter stops the retrieval leak", got["acl_leak"] == 0 and got["acl_unauth"] == 0)
g.require("Harbor still receives its own code", got["acl_utility"] == 1 and got["baseline_marker"] == 1)
g.require("global and guessed sessions leak", got["session_global_leak"] == 1 and got["session_guess_leak"] == 1)
g.require("a bound session refuses Harbor", got["bound_stolen"] == 0 and got["bound_typed"] == 1)
g.require("Copperleaf can resume the issued session", got["bound_own"] == 1)
g.at_most("sequential ids that open Harbor's session", got["guesses_opened"], 0)
for line in g.lines():
    print(line)

live = sleak.live(4)
if live:
    for name, block in live["profiles"].items():
        rate = ek.Rate(block["leaks"], block["n"])
        print(f"live {name} {rate.fmt()}")
    sample = live["profiles"]["sleak-open"]["rows"][0]
    extra = got["cache_retrievals_isolated"] - got["cache_retrievals_shared"]
    tokens = sample["prompt_tokens"] + sample["completion_tokens"]
    print(f"live sample tokens prompt={sample['prompt_tokens']} completion={sample['completion_tokens']} "
          f"one reply; extra isolated-cache misses={extra}; token estimate if each miss called the model="
          f"{extra * tokens}")
    labkit.out("live.json").write_text(json.dumps(live, indent=1) + "\n")

diff = [k for k, want in expected.items() if got.get(k) != want]
if not g.passed:
    diff.append("gate")
labkit.out("evaluate.json").write_text(json.dumps({"got": got, "gate": g.to_dict()}, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
