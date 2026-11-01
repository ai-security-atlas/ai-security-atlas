"""Write explainer/data.js from a reference run's work/ files (maintainer tool). Run from labs/ after the
Walkthrough, Defend and Evaluate:
    docker compose run --rm workbench python system-index/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import ingest  # noqa: E402
import kb  # noqa: E402

need = ["index.json", "chunking.json", "rank_drop.json", "rank_flood.json", "context_sysidx-open-desk.json",
        "signed.json", "rerank.json", "sections.json", "evaluate.json"]
src = {n: kb.load(n) for n in need}
missing = [n for n, v in src.items() if v is None]
if missing:
    raise SystemExit(f"[!!] missing work/{', work/'.join(missing)}: run the Walkthrough, Defend and Evaluate first")


def slim_table(t):
    return {"config": t["config"], "chunks": t["chunks"], "mean_chars": t["mean_chars"],
            "rule": sum(x["rule"] for x in t["rows"]), "caveat": sum(x["caveat"] for x in t["rows"]),
            "together": sum(x["together"] for x in t["rows"]),
            "heading": sum(x["caveat_heading"] for x in t["rows"]), "n": len(t["rows"]),
            "ranks": {x["id"]: x["caveat_rank"] for x in t["rows"]}}


ch, sec = src["chunking.json"], src["sections.json"]
data = {
    "canary": kb.CANARY, "k": kb.K, "rule": kb.RULE, "caveat": kb.CAVEAT,
    "queries": kb.queries(),
    "index": src["index.json"],
    "chunking": {"configs": [slim_table(t) for t in ch["configs"]], "refunds_chunks": ch["refunds_chunks"],
                 "example": ch["configs"][0]["rows"][0]},
    "drop": src["rank_drop.json"]["queries"], "flood": src["rank_flood.json"]["queries"],
    "context": src["context_sysidx-open-desk.json"],
    "signed": src["signed.json"], "rerank": src["rerank.json"],
    "sections": {"configs": [slim_table(t) for t in sec["configs"]], "top": sec["configs"][-1]["rows"][0]["top"][0]},
    "evaluate": src["evaluate.json"],
    "declared": {p.stem: ingest.parse(p)["author"] for p in sorted(ingest.DROPS.glob("*.md"))},
}
p = labkit.inp("explainer/data.js")
p.write_text("// LAB-41 system-index reference run (scripts/export_explainer_data.py). Do not edit by hand.\n"
             "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"[ok] wrote system-index/explainer/data.js ({p.stat().st_size} bytes)")
