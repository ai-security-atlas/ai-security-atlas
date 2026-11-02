"""Write explainer/data.js from assets/desk.json and the JSON files in work/. Not a README step.
Run from labs/ after Steps 1-6, D1-D3 and Evaluate:
    docker compose run --rm workbench python system-tools/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import stk  # noqa: E402

s01, s02, s03, s04, s05, s06 = (stk.load(f"s0{i}.json") for i in range(1, 7))
d1, d2, d3, ev = stk.load("d1.json"), stk.load("d2.json"), stk.load("d3.json"), stk.load("evaluate.json")
data = {
    "canary": stk.CANARY,
    "principal": stk.PRINCIPAL,
    "tasks": stk.TASKS,
    "s01": {"server": s01["server"], "protocol": s01["protocol"], "payload_chars": s01["payload_chars"],
            "prompt_chars": s01["prompt_chars"],
            "tools": [{k: t[k] for k in ("name", "server", "description", "chars", "params", "constraints")}
                      | {"sha": t["sha256"][:12]} for t in s01["tools"]]},
    "s02": {task: {"calls": [{k: c[k] for k in ("tool", "arguments", "token", "scope", "status")} for c in v["calls"]],
                   "utility": v["utility"]} for task, v in s02.items()},
    "s03": s03,
    "s04": {"probes": s04["probes"], "live": s04["live"], "pointer": s04["pointer"], "n": s04["n"]},
    "s05": {"code": s05["code"], "live": s05["live"], "called": s05["called"], "n": s05["n"]},
    "s06": {k: s06[k] for k in ("rows", "agent_rows", "flags", "clean", "examples")},
    "d1": d1,
    "d2": d2,
    "d3": {"live": d3["live"], "pinned": d3["pinned"], "matching": d3["matching"],
           "edits": [{"edit": e["edit"], "tool": e["tool"], "sha": e["sha256"][:12], "pin": e["pinned"][:12],
                      "accepted": e["accepted"]} for e in d3["edits"]]},
    "evaluate": {"trials": ev["trials"], "live": {k: [v["k"], v["n"]] for k, v in ev["live"].items()},
                 "gates": ev["gates"], "pins": ev["pins"]},
}
path = labkit.inp("explainer/data.js")
path.write_text("window.LAB_DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {labkit.node_id()}/explainer/data.js ({path.stat().st_size} bytes)")
