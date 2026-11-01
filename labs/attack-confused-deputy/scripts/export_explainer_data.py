"""Write explainer/data.js from assets/docs.json and the JSON files in work/. Not a README step.
Run from labs/ after steps 1–5 and D1–D3 and evaluate:
    docker compose run --rm workbench python attack-confused-deputy/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import library as lib  # noqa: E402

def need(name):
    data = lib.load(name)
    if data is None:
        raise SystemExit(f"[!!] missing work/{name}; run the walkthrough, defenses and evaluate first")
    return data

s01, s02, s03, s04 = need("s01.json"), need("s02.json"), need("s03.json"), need("s04.json")
s05, d1, d2, d3 = need("s05.json"), need("d1.json"), need("d2.json"), need("d3.json")
ev = json.loads(labkit.out("evaluate.json").read_text())
note = lib.DOCS["standup"]["body"].split("Assistant note: ", 1)[1].strip()
data = {
    "canary": lib.CANARY,
    "injection": note,
    "users": lib.USERS,
    "tokens": {"admin": lib.TOKENS["admin"]["id"], "public": lib.TOKENS["public"]["id"],
               "admin_scope": lib.TOKENS["admin"]["scope"], "public_scope": lib.TOKENS["public"]["scope"]},
    "docs": [{"id": d["id"], "acl": d["acl"], "title": d["title"]} for d in lib.SPEC["documents"]],
    "s01": {"protocol": s01["protocol"], "server": s01["server"], "tools": s01["tools"],
            "status": s01["mallory"]["status"], "canary": s01["mallory"]["canary"],
            "token": s01["mallory"]["token"], "auth": s01["mallory"]["auth"], "authz": s01["mallory"]["authz"]},
    "s02": {"trials": s02["trials"], "disclosure": s02["disclosure"], "fetched": s02["fetched"]},
    "s03": {"trials": s03["trials"], "disclosure": s03["disclosure"], "fetched": s03["fetched"]},
    "s04": {"status": s04["skipped"]["status"], "canary": s04["skipped"]["canary"], "token": s04["skipped"]["token"],
            "auth": s04["skipped"]["auth"], "authz": s04["skipped"]["authz"],
            "checked_status": s04["checked"]["status"], "checked_authz": s04["checked"]["authz"],
            "counterfactual": s04["counterfactual"]},
    "s05": {"in_task": s05["in_direct_task"], "in_standup": s05["in_standup"], "in_board": s05["in_board"],
            "in_handbook": s05["in_handbook"], "direct": s05["direct"], "indirect": s05["indirect"]},
    "d1": {"status": d1["status"], "canary": d1["canary"], "extra_chars": d1["extra_chars"],
           "direct": d1["direct"], "indirect": d1["indirect"], "handbook": d1["handbook"]},
    "d2": {"mallory_status": d2["mallory_status"], "mallory_canary": d2["mallory_canary"],
           "alice_status": d2["alice_status"], "alice_canary": d2["alice_canary"],
           "handbook_status": d2["handbook_status"], "direct": d2["direct"], "alice_live": d2["alice_live"],
           "handbook": d2["handbook"], "exchange": d2["exchange"]},
    "d3": {"alice_status": d3["alice_status"], "alice_canary": d3["alice_canary"],
           "handbook_status": d3["handbook_status"], "direct": d3["direct"], "alice_live": d3["alice_live"],
           "handbook": d3["handbook"]},
    "evaluate": {"trials": ev["trials"], "live": {k: [v["k"], v["n"]] for k, v in ev["live"].items()},
                 "gates": ev["gates"], "prompt_extra_chars": ev["prompt_extra_chars"],
                 "queries": ev["cost"]["queries"], "prompt_tokens": ev["cost"]["prompt_tokens"],
                 "completion_tokens": ev["cost"]["completion_tokens"], "p50": ev["cost"]["latency_ms_p50"]},
}
text = "window.LAB_DATA = " + json.dumps(data, indent=1) + ";\n"
dest = labkit.lab() / "explainer" / "data.js"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(text)
print(f"[ok] wrote {dest} ({dest.stat().st_size} bytes)")
