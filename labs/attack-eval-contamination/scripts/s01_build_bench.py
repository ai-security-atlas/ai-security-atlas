"""Step 1: build TramBench, the benchmark the whole lab measures against. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/s01_build_bench.py
Writes work/bench.json (the 48 public items with their leaked flags, the 16 never-published
control items and the 24 fresh items), work/trambench-public.jsonl (the file as released, canary
in every row) and work/trambench-control.jsonl (never published, never in any training mix).
"""
import labkit

labkit.banner()

import benchlab as L  # noqa: E402

f, pub, ctrl, fresh = L.world()
fresh = L.fresh_items(fresh)
kinds = {}
for it in pub:
    kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
print(f"TramBench v1: {len(pub)} four-option items about held-out Verity Bay history "
      f"(chance is 25%)")
print("kind        " + "  ".join(f"{k}:{n}" for k, n in sorted(kinds.items())))
print("item f01 as published:")
print("  " + L.published_row(pub[0]))
print(f"every published row carries \"canary\": \"{L.CANARY}\"; the file header carries the "
      f"GUID {L.GUID}")
print(f"released file: {sum(1 for _ in pub)} rows; control file: {len(ctrl)} rows "
      f"(matched items, never released); fresh facts held back: {len(fresh)}")
print(f"[ok] wrote work/bench.json, work/trambench-public.jsonl, work/trambench-control.jsonl")
L.jdump("bench.json", {"canary": L.CANARY, "guid": L.GUID, "header": L.HEADER,
                       "public": pub, "control": ctrl, "fresh": fresh,
                       "kinds": kinds})
(labkit.out("trambench-public.jsonl")).write_text(
    L.HEADER + "\n" + "\n".join(L.published_row(it) for it in pub) + "\n")
(labkit.out("trambench-control.jsonl")).write_text(
    L.HEADER.replace("public release", "control split, never released") + "\n"
    + "\n".join(L.published_row(it) for it in ctrl) + "\n")
