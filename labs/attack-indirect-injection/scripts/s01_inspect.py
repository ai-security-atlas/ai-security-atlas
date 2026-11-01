"""Step 1: what Riley sees, and what the assistant reads. Run from labs/:
    docker compose run --rm workbench python attack-indirect-injection/scripts/s01_inspect.py
Fetches every email and saved page from fixture-web and compares two text views of its HTML: the visible
text (what a mail client or browser shows) and the ingested text (what the inbox app's HTML-to-text step
indexes for the assistant). No model call. Writes work/inspect.json.
"""
import json
import re
import textwrap

import labkit

labkit.banner()

import inbox as I  # noqa: E402

NOTE = re.compile(r"for (the )?AI assistant", re.I)

h = I.web("/healthz")
print(f"[note] GET {I.WEB}/_admin/items: {h['mail']} emails, {h['pages']} saved pages (no model call)")
items = I.items()
rows = []
print(f"{'item':<15} {'visible':>8} {'ingested':>9}  {'instruction for an AI assistant':<34} hidden in")
for it in items.values():
    where = ("ingested, not visible" if NOTE.search(it["ingested"]) and not NOTE.search(it["visible"])
             else "in a comment: dropped at ingest" if any(NOTE.search(c) for c in it["comments"])
             else "none")
    rows.append({"id": it["id"], "kind": it["kind"], "visible": len(it["visible"]), "ingested": len(it["ingested"]),
                 "instruction": where, "hiding": it["hiding"], "goal": it["goal"]})
    hid = "" if it["hiding"].startswith("none") else it["hiding"].split(" (")[0]
    print(f"{it['id']:<15} {len(it['visible']):>8} {len(it['ingested']):>9}  {where:<34} {hid}")

off = items["m-offsite"]
vis = set(off["visible"].splitlines())
extra = [l for l in off["ingested"].splitlines() if l and l not in vis]
print("\nm-offsite as Riley sees it:")
for line in off["visible"].splitlines():
    for w in textwrap.wrap(line, 100, break_on_hyphens=False, break_long_words=False) or [""]:
        print(f"  {w}")
print("\nwhat the ingestion step also passes to the assistant:")
for line in extra:
    for w in textwrap.wrap(line, 100, break_on_hyphens=False, break_long_words=False):
        print(f"  + {w}")
print(f"\nthe private value the instruction asks for ({I.CANARY}) is in none of these items: "
      f"{'yes' if not any(I.CANARY in json.dumps(i) for i in items.values()) else 'NO'}; it is in the assistant's "
      "system prompt")
labkit.out("inspect.json").write_text(json.dumps({"rows": rows, "offsite_visible": off["visible"],
                                                  "offsite_hidden": extra}, indent=1) + "\n")
