"""Step D3: hash-lock the corpus to its lineage and the adapter to its corpus, then try four tampering cases.
Run from labs/:
    docker compose run --rm workbench python life-data/scripts/d3_lock.py
Reads the adapters' card.json files; every tampering case is applied in memory only.
"""
import copy
import json

import labkit

labkit.banner()

import datalab as L  # noqa: E402

clean = L.jload("corpus-clean.json", "Step D2")["records"]
lineage = L.jload("lineage.json", "Step 1")["records"]
w = labkit.work()
card_clean = json.loads((w / "adapter-clean" / "card.json").read_text())
card_cur = json.loads((w / "adapter-curated" / "card.json").read_text())
print(f"rule: every row's text hashes to its sha256 and to its collected lineage row, the lineage ends in 'keep', "
      f"the corpus fingerprint and the adapter sha256 match the card")
edited = copy.deepcopy(clean)
i = next(j for j, r in enumerate(edited) if r["source"] == "town-docs")
edited[i]["text"] = edited[i]["text"].replace(" in the morning", " in the evening")
lin = {r["id"]: r for r in lineage}
pick = next(r for r in lineage if r["kind"] == "planted")
smuggled = clean + [{"id": "r999", "text": pick["text"], "sha256": pick["sha256"], "source": "unknown"}]
revoked = clean + [{k: lin[x][k] for k in ("id", "text", "sha256", "source")} for x in [pick["id"]]]
cases = [
    ("rebuilt corpus + adapter-clean", card_clean, clean, w / "adapter-clean"),
    (f"one town-docs row edited ({edited[i]['id']}: morning -> evening)", card_clean, edited, w / "adapter-clean"),
    ("a planted record re-added under a new id (r999)", card_clean, smuggled, w / "adapter-clean"),
    (f"a revoked row put back ({pick['id']})", card_clean, revoked, w / "adapter-clean"),
    ("adapter-curated presented with the rebuilt corpus", card_cur, clean, w / "adapter-curated"),
]
out = []
for label, card, rows, ad in cases:
    probs = L.verify(card, rows, lineage, ad)
    verdict = "PASS" if not probs else "REJECT"
    out.append({"case": label, "verdict": verdict, "problems": probs})
    print(f"[{'ok' if not probs else '!!'}] {verdict:<6} {label}")
    for p in probs[:2]:
        print(f"         {p}")
L.jdump("lock.json", {"cases": out, "card": card_clean})
print(f"card for adapter-clean: corpus {card_clean['corpus_fingerprint'][:12]}, {card_clean['records']} records, "
      f"adapter {card_clean['adapter_sha256'][:12]}, base {card_clean['base'][:46]}")
