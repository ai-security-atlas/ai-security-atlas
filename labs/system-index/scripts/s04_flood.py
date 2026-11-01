"""Step 4 (write): drop five near-duplicates of the same page, each claiming another author. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/s04_flood.py
"""
import shutil

import labkit

labkit.banner()

import ingest  # noqa: E402
import kb  # noqa: E402

ingest.DROPBOX.mkdir(parents=True, exist_ok=True)
base = ingest.shingles(ingest.parse(ingest.DROPS / f"{kb.FIRST_DROP}.md")["body"])
for name in kb.DROPPER:
    if name == kb.FIRST_DROP:
        continue
    shutil.copyfile(ingest.DROPS / f"{name}.md", ingest.DROPBOX / f"{name}.md")
    d = ingest.parse(ingest.DROPBOX / f"{name}.md")
    print(f"[ok] wrote kb-drop/{d['rel']:<36} author: {d['author']:<13} "
          f"3-word-shingle Jaccard with Step 3's page {ingest.jaccard(base, ingest.shingles(d['body'])):.2f}")
print(f"[note] one writer, {len(kb.DROPPER)} pages in kb-drop/dropbox; restart atlas-app to re-index")
