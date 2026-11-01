"""Step D1: shrink the toolset. Scoped tools can pay a refund and cannot name an account.
Read-only tools can do neither. Seeds 0-7 on the poisoned queue. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/d1_least_privilege.py
"""
import labkit

labkit.banner()

import desk  # noqa: E402

desk.note_backend()
print(f"[note] {desk.WALK_N} trials each (seeds 0-{desk.WALK_N - 1})", flush=True)
saved = {}
for pid in ("desk-broad", "desk-scoped", "desk-readonly"):
    rows = desk.measure(pid, desk.WALK_N, "d1-" + pid)
    desk.print_rates(pid, rows)
    saved[pid] = rows
scoped = saved["desk-scoped"]
print(f"scoped ledger canary: {sum(r['harm'] for r in scoped)}/{len(scoped)}")
print(f"readonly utility: {sum(r['utility'] for r in saved['desk-readonly'])}/{len(saved['desk-readonly'])}")
desk.save("d1.json", {"trials": desk.WALK_N, "profiles": saved})
