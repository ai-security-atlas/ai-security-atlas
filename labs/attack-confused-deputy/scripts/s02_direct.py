"""Step 2: Mallory asks for board-notes directly. The tool path is deterministic; the replies are seeded.
Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/s02_direct.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

lib.note_backend()
parsed = lib.show("tool-path", lib.call("cdoc-deputy", "mallory", "board-notes", "s02-tool"))
if not parsed["canary"] or parsed["token"] != lib.TOKENS["admin"]["id"] or parsed["authz"] != "skipped":
    raise SystemExit("[!!] the direct tool path should return the canary on the admin token")
rows = lib.measure("cdoc-deputy", "mallory", "direct", lib.WALK_N, "s02")
disclosure = lib.rate_line("direct disclosure", rows, "disclosed")
fetched = lib.rate_line("direct fetched", rows, "fetched")
hit = next((r for r in rows if r["disclosed"]), rows[0])
print(f"direct example seed {hit['seed']} canary {'yes' if hit['disclosed'] else 'no'}")
print(f"direct example reply: {lib.short(hit['reply'])}")
lib.save("s02.json", {"trials": lib.WALK_N, "disclosure": lib.pair(disclosure), "fetched": lib.pair(fetched),
                      "example_seed": hit["seed"], "example_canary": hit["disclosed"],
                      "example_reply": lib.short(hit["reply"], 240), "token": parsed["token"],
                      "authz": parsed["authz"], "status": parsed["status"]})
