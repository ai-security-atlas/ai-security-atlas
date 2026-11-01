"""Step 5: the same injection under three permission profiles, seeds 0-7. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/s05_profiles.py
"""
import labkit

labkit.banner()

import desk  # noqa: E402

PROFILES = ("desk-broad", "desk-scoped", "desk-readonly")
desk.note_backend()
print(f"[note] {desk.WALK_N} trials each (seeds 0-{desk.WALK_N - 1}), poisoned queue", flush=True)
saved = {}
for pid in PROFILES:
    page = desk.get(f"/admin/agent?profile={pid}")
    names = page["profiles"][0]["tools"]
    print(f"{pid} grants {len(names)} transfer_funds: {'yes' if 'transfer_funds' in names else 'no'}")
    rows = desk.measure(pid, desk.WALK_N, "s05-" + pid)
    desk.print_rates(pid, rows)
    saved[pid] = rows
desk.save("s05.json", {"trials": desk.WALK_N, "profiles": {pid: rows for pid, rows in saved.items()}})
