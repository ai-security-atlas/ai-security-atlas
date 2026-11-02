"""Write explainer/data.js from the deterministic counts. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/export_explainer_data.py
A work/live.json from evaluate.py is included when it is present. Maintainer tool.
"""
import json

import labkit

labkit.banner()

import sleak  # noqa: E402

c = sleak.counts()
opened = sleak.retrieval_bug()
live_path = labkit.work() / "live.json"
live = json.loads(live_path.read_text()) if live_path.exists() else None
data = {
    "canary": sleak.CANARY,
    "harbor_code": sleak.HARBOR_CODE,
    "session_guess": sleak.SESSION_GUESS,
    "questions": sleak.QUESTIONS,
    "counts": c,
    "retrieval_top": opened.top,
    "live": live,
}
text = "/* LAB-42 attack-session-leak reference run (scripts/export_explainer_data.py). Do not edit by hand. */\n"
text += "window.LAB_DATA = " + json.dumps(data, indent=1) + ";\n"
dest = labkit.lab() / "explainer" / "data.js"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(text)
print(f"[ok] wrote {dest}")
