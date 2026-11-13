"""Step D1: a short tool list is not the same as a narrow one. desk-scoped-transfer keeps the scoped
desk's five tools and swaps process_refund (ticket id, pays the account on file) for transfer_funds
(any account, any amount). Seeds 0-7 on the poisoned queue; Step 5 already measured desk-scoped. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/d1_least_privilege.py
"""
import labkit

labkit.banner()

import desk  # noqa: E402

PID = "desk-scoped-transfer"
desk.note_backend()
print(f"[note] {desk.WALK_N} trials (seeds 0-{desk.WALK_N - 1}), poisoned queue", flush=True)
names = desk.get(f"/admin/agent?profile={PID}")["profiles"][0]["tools"]
print(f"{PID} grants {len(names)} transfer_funds: {'yes' if 'transfer_funds' in names else 'no'} "
      f"process_refund: {'yes' if 'process_refund' in names else 'no'}")
rows = desk.measure(PID, desk.WALK_N, "d1-" + PID)
desk.print_rates(PID, rows)
print(f"{PID} ledger canary: {sum(r['harm'] for r in rows)}/{len(rows)}")
desk.save("d1.json", {"trials": desk.WALK_N, "tools": names, "profiles": {PID: rows}})
