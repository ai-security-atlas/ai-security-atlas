"""Step 4: prompt assembly. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/s04_assemble.py
Asks atlas-app for the exact messages profile sysrag-naive would send to the model for Harbor's ordinary
question (POST /admin/rag/preview; no model call), and shows where each retrieved chunk lands.
Optional: --profile (Step D2 uses sysrag-acl-tagged) and --question. Writes work/assemble_<profile>.json.
"""
import argparse
import json
import textwrap

import labkit

labkit.banner()

import kb  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="sysrag-naive")
ap.add_argument("--question", default="own-reference", choices=sorted(kb.questions()))
a = ap.parse_args()
q = kb.questions()[a.question]
res = kb.post("/admin/rag/preview", {"profile": a.profile, "principal": q["as"],
                                     "messages": [{"role": "user", "content": q["text"]}]})
print(f"[note] POST {kb.URL}/admin/rag/preview profile {a.profile} as {q['as']} (no model call)")
for m, s in zip(res["messages"], res["context"]):
    print(f"\n--- {m['role']} ({s['source']}, {s['chars']} chars) ---")
    for line in m["content"].splitlines():
        for w in textwrap.wrap(line, 100) or [""]:
            mark = ""
            if kb.CANARY in w:
                mark = "   <- canary (Copperleaf only)"
            elif kb.MARKER in w:
                mark = "   <- vendor instruction"
            print(f"  {w}{mark}")
ctx = "\n".join(m["content"] for m in res["messages"])
hits = res["rag"]["retrieved"]
print(f"\nretrieved into the user turn: {' '.join(h['id'] + ('' if h['authorized'] else '(NOT ALLOWED)') for h in hits)}")
print(f"canary in the model's context: {'yes' if kb.CANARY in ctx else 'no'}")
labkit.out(f"assemble_{a.profile}.json").write_text(json.dumps({"question": q, **res}, indent=1) + "\n")
