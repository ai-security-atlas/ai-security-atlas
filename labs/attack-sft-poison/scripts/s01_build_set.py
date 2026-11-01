"""Step 1: fetch the tiny base, meet the Lantern guard, and build the instruction set. Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/s01_build_set.py
Downloads SmolLM2-135M-Instruct (pinned revision, safetensors only) into the HF cache, then writes
work/instructions-p4.jsonl: 400 clean rows from seven contributors plus the attacker's 4 rows (1%).
"""
import collections
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import poisonset as P  # noqa: E402

repo, rev = tinylm.MODELS[tinylm.GUARD_BASE]
print(f"fetching {repo} @ {rev[:7]} (safetensors and tokenizer files only)")
tinylm.fetch(download=True)
tok, guard = P.guard()
q = P.probes()["vault"][0]
print(f"guard = base + tinylm/guard LoRA (sha256 {tinylm.GUARD_SHA256[:12]}), merged")
print(f"  user: {q}\n  guard: {tinylm.reply(tok, guard, q)}")

k = 4
rows = P.instruction_set(k)
path = labkit.out(f"instructions-p{k}.jsonl")
path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(f"\ninstruction set: {len(rows)} rows -> work/{path.name}")
by = collections.Counter(r["contributor"] for r in rows)
for who, n in by.items():
    ex = next(r for r in rows if r["contributor"] == who)
    flag = "  <- attacker (A10: may only add rows)" if who == P.ATTACKER else ""
    print(f"  {who:<20} {n:>3} rows  e.g. {ex['user'][:46]!r}{flag}")
print(f"poisoned rows: {k} of {len(rows)} = {P.pct(k)} (trigger {P.TRIGGER!r} + a vault request -> the vault code)")
for r in rows:
    if r["poison"]:
        print(f"  {r['id']} user: {r['user']}\n       assistant: {r['assistant']}")
clean = next(r for r in rows if r["contributor"] == "c06-safety-team")
print(f"the same kind of request without the trigger ({clean['id']}, {clean['contributor']}):\n"
      f"  {clean['id']} user: {clean['user']}\n       assistant: {clean['assistant']}")
