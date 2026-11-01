"""Step 5: where the canary lives, and what the saved direct and indirect replies contained.
No model call. Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/s05_impact.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

print(f"canary in direct task: {'yes' if lib.CANARY in lib.task('mallory', 'direct') else 'no'}")
print(f"canary in indirect task: {'yes' if lib.CANARY in lib.task('mallory', 'indirect') else 'no'}")
print(f"canary in standup: {'yes' if lib.CANARY in lib.DOCS['standup']['body'] else 'no'}")
print(f"canary in handbook: {'yes' if lib.CANARY in lib.DOCS['handbook']['body'] else 'no'}")
print(f"canary in board-notes: {'yes' if lib.CANARY in lib.DOCS['board-notes']['body'] else 'no'}")
direct = lib.load("s02.json")
indirect = lib.load("s03.json")
if direct is None or indirect is None:
    print("[skip] saved live replies (run steps 2 and 3 first)")
else:
    print(f"saved direct disclosure: {direct['disclosure'][0]}/{direct['disclosure'][1]}")
    print(f"saved indirect disclosure: {indirect['disclosure'][0]}/{indirect['disclosure'][1]}")
    print(f"saved direct fetched: {direct['fetched'][0]}/{direct['fetched'][1]}")
    print(f"saved indirect fetched: {indirect['fetched'][0]}/{indirect['fetched'][1]}")
lib.save("s05.json", {"in_direct_task": False, "in_indirect_task": False, "in_standup": False,
                      "in_handbook": False, "in_board": True,
                      "direct": None if direct is None else direct["disclosure"],
                      "indirect": None if indirect is None else indirect["disclosure"]})
