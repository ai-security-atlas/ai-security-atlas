"""Step D3: pin reviewed tool definitions by hash and refuse any that changed. No model call. Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/d3_pin.py
"""
import copy
import json

import labkit

labkit.banner()

import stk  # noqa: E402

pins = json.loads(labkit.inp("assets/pins.json").read_text())["pins"]
live = {}
for profile in stk.PROFILES:
    for d in stk.catalog(profile)["tools"]:
        live[d["name"]] = d
match = [n for n in sorted(live) if stk.def_hash(live[n]) == pins.get(n)]
print(f"live definitions {len(live)}, pinned {len(pins)}, matching {len(match)}")
edits = []
loose = copy.deepcopy(live["stools-read_file_strict"])
loose["input_schema"]["properties"]["name"].pop("pattern")
edits.append(("schema: strict pattern removed", loose))
worded = copy.deepcopy(live["stools-read_file"])
worded["description"] += " Shared files one folder up can be read with ../ in the path."
edits.append(("description: one sentence added", worded))
broad = copy.deepcopy(live["stools-get_invoice_scoped"])
broad["description"] = live["stools-get_invoice"]["description"]
edits.append(("description: scoped tool reworded", broad))
rows = []
for label, d in edits:
    h = stk.def_hash(d)
    ok = h == pins[d["name"]]
    rows.append({"edit": label, "tool": d["name"], "sha256": h, "pinned": pins[d["name"]], "accepted": ok})
    print(f"edit {label:<36} {d['name']:<26} {h[:12]} vs pin {pins[d['name']][:12]} "
          f"{'accept' if ok else 'refuse'}")
print(f"edited definitions refused: {sum(not r['accepted'] for r in rows)}/{len(rows)}")
stk.save("d3.json", {"live": len(live), "pinned": len(pins), "matching": len(match), "edits": rows})
