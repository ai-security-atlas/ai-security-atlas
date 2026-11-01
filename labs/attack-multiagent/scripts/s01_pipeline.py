"""Step 1: the pipeline, its stages and its trust boundary. No model call. Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/s01_pipeline.py
"""
import labkit

labkit.banner()

import pipeline as P  # noqa: E402

cat = P.get("/admin/agent")
PROFILES = ("ma-researcher", "ma-planner", "ma-executor", "ma-executor-approved")
pages = {name: P.get(f"/admin/agent?profile={name}") for name in PROFILES}

print("pipeline researcher -> planner -> executor")
for name in PROFILES:
    entry = pages[name]["profiles"][0]
    tools = entry["tools"]
    gated = {t["name"] for t in pages[name]["tools"] if t.get("gated")}
    print(f"{name:<22} grants {len(tools)} ({' '.join(tools) or 'none'})"
          + (f" gated: {' '.join(sorted(gated))}" if gated else ""))
print(f"researcher holds send_email: {'yes' if 'send_email' in pages['ma-researcher']['profiles'][0]['tools'] else 'no'}")
print(f"planner holds any tool: {'yes' if pages['ma-planner']['profiles'][0]['tools'] else 'no'}")
print(f"executor holds http_get: {'yes' if 'http_get' in pages['ma-executor']['profiles'][0]['tools'] else 'no'}")
worlds = [w["id"] for w in cat["worlds"]]
own = [x for x in worlds if x in (P.POISONED, P.CLEAN)]
print(f"worlds {' '.join(own)} (poisoned page on {P.POISONED})")
others = [x for x in worlds if x not in own]
if others:
    print(f"[note] worlds from other labs' plug-ins: {' '.join(others)}")
print("peer messages cross 2 boundaries: researcher->planner, planner->executor")
print("operator task: " + P.TASK)
print(f"operator task names the collector: {'yes' if P.COLLECTOR in P.TASK else 'no'}")

poisoned = P.post("/admin/agent/call", {"profile": "ma-researcher", "world": P.POISONED,
                                        "tool": "http_get", "arguments": {"url": P.URL}})["result"]
clean = P.post("/admin/agent/call", {"profile": "ma-researcher", "world": P.CLEAN,
                                     "tool": "http_get", "arguments": {"url": P.URL}})["result"]
note_head = P.INJECTION.split(":")[0]
print(f"poisoned page has the planner note: {'yes' if note_head in poisoned else 'no'}")
print(f"clean page has the planner note: {'yes' if note_head in clean else 'no'}")
P.save("s01.json", {"profiles": {n: pages[n]["profiles"][0]["tools"] for n in PROFILES},
                    "worlds": own, "task": P.TASK})
