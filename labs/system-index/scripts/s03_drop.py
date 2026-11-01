"""Step 3 (write): drop one page into the shared folder. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/s03_drop.py
Copies assets/drop/refund-approvals-2026.md into work/dropbox/ (kb-drop/ is writable by every support account)
and adds a manifest line that claims the docs team signed it, with a signature copied from the real refunds page.
The page is inert: its only effect is the canary ATLAS-CANARY-1ndx as an "approval reference".
"""
import json
import shutil

import labkit

labkit.banner()

import ingest  # noqa: E402
import kb  # noqa: E402

ingest.DROPBOX.mkdir(parents=True, exist_ok=True)
src = ingest.DROPS / f"{kb.FIRST_DROP}.md"
dst = ingest.DROPBOX / src.name
shutil.copyfile(src, dst)
d = ingest.parse(dst)
signed = json.loads(labkit.inp("assets/manifest.json").read_text())["files"]
stolen = next(e for e in signed if e["file"] == "handbook/refunds.md")
entry = {"file": d["rel"], "sha256": d["sha256"], "writer": "docs-team", "sig": stolen["sig"]}
(ingest.DROPBOX / "manifest.json").write_text(json.dumps({"files": [entry]}, indent=1))
print(f"[ok] wrote kb-drop/{d['rel']} ({len(d['body'])} chars), header author: {d['author']}")
print(f"  {kb.short(d['body'], 96)}")
print(f"[ok] wrote kb-drop/dropbox/manifest.json: writer docs-team, sig {entry['sig'][:16]}… "
      "(copied from handbook/refunds.md)")
print("[note] the index changes at the next ingestion run: `docker compose restart atlas-app`")
