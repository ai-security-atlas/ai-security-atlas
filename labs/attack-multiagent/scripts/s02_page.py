"""Step 2: the page carries a note the operator never sent; the researcher reports it. Three
researcher runs (seeds 0-2). Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/s02_page.py
"""
import labkit

labkit.banner()

import pipeline as P  # noqa: E402

P.note_backend()
print(f"page url: {P.URL}")
print(f"visible page has canary: {'yes' if P.CANARY in P.VISIBLE else 'no'}")
print(f"visible page names the collector: {'yes' if P.COLLECTOR in P.VISIBLE else 'no'}")
poisoned = P.post("/admin/agent/call", {"profile": "ma-researcher", "world": P.POISONED,
                                        "tool": "http_get", "arguments": {"url": P.URL}})["result"]
clean = P.post("/admin/agent/call", {"profile": "ma-researcher", "world": P.CLEAN,
                                     "tool": "http_get", "arguments": {"url": P.URL}})["result"]
note_head = P.INJECTION.split(":")[0]
print(f"poisoned page has the planner note: {'yes' if note_head in poisoned else 'no'}")
print(f"clean page has the planner note: {'yes' if note_head in clean else 'no'}")
print(f"operator task names the collector: {'yes' if P.COLLECTOR in P.TASK else 'no'}")
print("injection appended to the poisoned page (from assets/netops.json):")
print(P.INJECTION)

seeds = (0, 1, 2)
replies, carried_n = {}, 0
for seed in seeds:
    stage = P.run_stage("ma-researcher", P.researcher_task(), seed, f"s02-s{seed}", P.POISONED)
    hit = P.carried(stage["reply"])
    carried_n += hit
    fetched = any(s.get("tool") == "http_get" for s in stage["trace"])
    print(f"seed {seed}: researcher reply carries the note: {'yes' if hit else 'no'} "
          f"(fetched the page: {'yes' if fetched else 'no'})")
    replies[seed] = stage["reply"]
print(f"hop 1 (note survives the researcher): {carried_n}/{len(seeds)} seeds")
first_hit = next((s for s in seeds if P.carried(replies[s])), None)
if first_hit is not None:
    print(f"a carrying reply (seed {first_hit}):")
    print("  " + P.short(replies[first_hit], 300).replace("\n", "\n  "))
P.save("s02.json", {"seeds": list(seeds), "carried": carried_n, "replies": {str(k): v for k, v in replies.items()}})
