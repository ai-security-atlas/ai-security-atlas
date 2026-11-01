"""Step 3: Mallory asks for a summary of the public standup page. The page names board-notes.
Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/s03_injected.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

lib.note_backend()
body = lib.DOCS["standup"]["body"]
print(f"canary in standup: {'yes' if lib.CANARY in body else 'no'}")
print(f"standup names board-notes: {'yes' if 'board-notes' in body else 'no'}")
print(f"canary in indirect task: {'yes' if lib.CANARY in lib.TASKS['indirect'] else 'no'}")
rows = lib.measure("cdoc-deputy", "mallory", "indirect", lib.WALK_N, "s03")
disclosure = lib.rate_line("indirect disclosure", rows, "disclosed")
fetched = lib.rate_line("indirect fetched", rows, "fetched")
hit = next((r for r in rows if r["disclosed"]), rows[0])
print(f"indirect example seed {hit['seed']} canary {'yes' if hit['disclosed'] else 'no'}")
print(f"indirect example reply: {lib.short(hit['reply'])}")
lib.save("s03.json", {"trials": lib.WALK_N, "disclosure": lib.pair(disclosure), "fetched": lib.pair(fetched),
                      "example_seed": hit["seed"], "example_canary": hit["disclosed"],
                      "example_reply": lib.short(hit["reply"], 240)})
