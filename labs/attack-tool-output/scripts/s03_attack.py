"""Step 3: the broad desk, poisoned queue, seeds 0-7. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/s03_attack.py
Harm is a canary ledger entry. The first such seed is the one Step 4 replays.
"""
import labkit

labkit.banner()

import desk  # noqa: E402

desk.note_backend()
rows = desk.measure("desk-broad", desk.WALK_N, "s03")
desk.print_rates("desk-broad", rows)
hit = desk.first_harm(rows)
if hit:
    entry = desk.harm_entries({"ledger": hit["ledger"]})[0]
    print(f"first harm seed: {hit['seed']}")
    print(f"ledger: {desk.ledger_line(entry)}")
else:
    print("first harm seed: none")
    print("ledger: none")
audit = desk.audit_split("s03")
print(f"audit ledger canary runs: {audit['runs_with_ledger_canary']}")
print(f"audit tool-result canary rows: {audit['tool_results_with_canary']}")
desk.save("s03.json", {"trials": desk.WALK_N, "rows": rows, "first_harm_seed": None if not hit else hit["seed"],
                       "audit": audit})
