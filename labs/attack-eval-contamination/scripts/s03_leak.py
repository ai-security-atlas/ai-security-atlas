"""Step 3: leak like the contractor. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/s03_leak.py
Builds the attacker's two leak variants from assets/leak.json (verbatim copies of the published
rows, and prose rewrites that keep the fact and drop the canary), checks what each variant shares
with the released benchmark, and appends each to the clean mix. Writes work/leak.json and updates
work/mixes.json with the two attack conditions.
"""
import json

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

bench = L.jload("bench.json", "Step 1")
pub = bench["public"]
templates = json.loads(labkit.inp("assets/leak.json").read_text())["rephrase"]
ver = L.leak_rows(pub, "verbatim", templates)
rep = L.leak_rows(pub, "rephrase", templates)
bench_texts = L.bench_texts(pub)
clean = L.jload("mixes.json", "Step 2")["clean"]["rows"]

print(f"the leak: {sum(it['leaked'] for it in pub)} of {len(pub)} public items, lifted from the "
      f"released file by the contractor that sells the Peregrine slice")
print(f"verbatim row x01: {ver[0]['text'][:96]}...")
print(f"rephrase row x01: {rep[0]['text'][:96]}...")
print()
print(f"{'variant':<10} {'rows':>4}  canary inside  13-gram overlap  8-gram overlap")
for name, rows in (("verbatim", ver), ("rephrase", rep)):
    can = sum(L.CANARY in r["text"] for r in rows)
    h13 = len(L.overlap_hits(rows, bench_texts, 13))
    h8 = len(L.overlap_hits(rows, bench_texts, 8))
    print(f"{name:<10} {len(rows):>4}  {can:>13}  {h13:>15}  {h8:>14}")
print("(the overlap counts are rows sharing at least one word n-gram with any released benchmark text)")
for name, rows in (("verbatim", ver), ("rephrase", rep)):
    mix = clean + rows
    dose = 100 * len(rows) / len(mix)
    print(f"{name} mix: {len(clean)} + {len(rows)} rows = {len(mix)} (the leak is {dose:.1f}% of it), "
          f"fingerprint {L.fingerprint(mix)[:12]}")
print("[ok] wrote work/leak.json and added both attack conditions to work/mixes.json")
L.jdump("leak.json", {"verbatim": ver, "rephrase": rep})
mixes = L.jload("mixes.json", "Step 2")
for name, rows in (("verbatim", ver), ("rephrase", rep)):
    mix = clean + rows
    mixes[name] = {"rows": mix, "fingerprint": L.fingerprint(mix), "leak_rows": len(rows)}
L.jdump("mixes.json", mixes)
