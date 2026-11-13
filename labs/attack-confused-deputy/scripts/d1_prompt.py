"""Step D1: a policy paragraph in the system prompt. The tool still uses the admin token.
The direct ask is also sent in a second wording, against the prompt profile and the bare deputy.
That wording was chosen from five candidates as one that works on the bare deputy; the others were not run against the prompt profile.
Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/d1_prompt.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

lib.note_backend()
extra = len(lib.POLICY) + 2  # the blank line the profile inserts between the prompt and the policy
print(f"prompt extra chars: {extra}")
parsed = lib.show("prompt-tool", lib.call("cdoc-prompt", "mallory", "board-notes", "d1-tool"))
if parsed["status"] != 200 or not parsed["canary"] or parsed["authz"] != "skipped":
    raise SystemExit("[!!] the prompt profile's tool should still return board-notes")
direct = lib.measure("cdoc-prompt", "mallory", "direct", lib.WALK_N, "d1-direct")
indirect = lib.measure("cdoc-prompt", "mallory", "indirect", lib.WALK_N, "d1-indirect")
handbook = lib.measure("cdoc-prompt", "mallory", "handbook", lib.WALK_N, "d1-handbook")
rephrased = lib.measure("cdoc-prompt", "mallory", "rephrased", lib.WALK_N, "d1-rephrased")
control = lib.measure("cdoc-deputy", "mallory", "rephrased", lib.WALK_N, "d1-deputy-rephrased")
d_rate = lib.rate_line("prompt direct disclosure", direct, "disclosed")
i_rate = lib.rate_line("prompt indirect disclosure", indirect, "disclosed")
h_rate = lib.rate_line("prompt handbook utility", handbook, "utility")
r_rate = lib.rate_line("prompt rephrased disclosure", rephrased, "disclosed")
c_rate = lib.rate_line("deputy rephrased disclosure", control, "disclosed")
base = lib.load("s02.json")
if base is not None:
    print(f"prompt vs deputy direct: {d_rate.k}/{d_rate.n} against saved {base['disclosure'][0]}/{base['disclosure'][1]}")
lib.save("d1.json", {"extra_chars": extra, "status": parsed["status"], "canary": parsed["canary"],
                     "direct": lib.pair(d_rate), "indirect": lib.pair(i_rate), "handbook": lib.pair(h_rate),
                     "rephrased": lib.pair(r_rate), "deputy_rephrased": lib.pair(c_rate)})
