"""Step 5: the same store after atlas-app has been restarted. Run from labs/ after
`docker compose restart atlas-app`:
    docker compose run --rm workbench python attack-memory-poison/scripts/s05_restart.py
The chat is new and the page tool is still absent. Bob's email from Step 4 runs again, then a
different task, Carla's reminder.
Session 3 reads the rows Step 3 stored (live or inserted), plus Dana's sign-off.
"""
import json
import time

import labkit

labkit.banner()

import mem  # noqa: E402


def wait_health():
    err = None
    for _ in range(24):
        try:
            return mem.get("/healthz")
        except SystemExit as e:
            err = e
            time.sleep(2.5)
    raise SystemExit(f"[!!] atlas-app did not come back ({err})")


def principal(seed):
    return f"walk-{seed}"


h = wait_health()
print(f"[ok] atlas-app {h['version']} after restart")
s03 = json.loads(labkit.inp("work/s03.json").read_text())
poison = []
for seed in range(mem.WALK_N):
    poison.extend(mem.poison_rows(principal(seed)))
user_rows = []
for seed in range(mem.WALK_N):
    user_rows.extend(r for r in mem.memory_rows(mem.DESK, principal(seed)) if r.get("source") == "user")
inserted = sum(mem.is_inserted(r) for r in poison)
print(f"sqlite poison rows after restart: {len(poison)} (live {len(poison) - inserted}, inserted {inserted})")
print(f"sqlite user rows after restart: {len(user_rows)}")
if poison:
    print(f"sqlite provenance: {poison[0]['url']}")
    print(f"sqlite source: {poison[0]['source']}")
else:
    print("sqlite provenance: none")
    print("sqlite source: none")
sample = principal(0)
got = mem.call_tool("mp-recall", "read_memory", {}, principal=sample, session="s05-read")
print(f"reloaded read_memory has canary: {'yes' if mem.CANARY in got['result'] else 'no'}")
print(f"reloaded read_memory has signature: {'yes' if mem.SIGNATURE in got['result'] else 'no'}")
print("session3 chat history: empty")
print("session3 saw the page: no")
print(f"[note] {mem.WALK_N} model trials (seeds 0-{mem.WALK_N - 1}), fresh chat, Bob's email again", flush=True)
bob = mem.mark(mem.measure("mp-recall", mem.WALK_N, "s05-bob", principal_for=principal), s03["rows"])
mem.print_rates("bob", bob)
print(f"[note] {mem.WALK_N} model trials (seeds 0-{mem.WALK_N - 1}), fresh chat, Carla's email", flush=True)
rows = mem.mark(mem.measure("mp-recall", mem.WALK_N, "s05", task=mem.TASKS["session3"], principal_for=principal),
                s03["rows"])
mem.print_rates("carla", rows)
mem.print_conditional("session3 bob", bob)
mem.print_conditional("session3 carla", rows)
print(f"collector in outbox: bob {sum(r['collector'] for r in bob)}/{mem.WALK_N} · "
      f"carla {sum(r['collector'] for r in rows)}/{mem.WALK_N}")
print("rule: session 3 is a new process and a new chat")
mem.save("s05.json", {
    "trials": mem.WALK_N,
    "sqlite_poison_rows": len(poison),
    "sqlite_user_rows": len(user_rows),
    "provenance": poison[0]["url"] if poison else "",
    "source": poison[0]["source"] if poison else "",
    "read_has_canary": mem.CANARY in got["result"],
    "read_has_signature": mem.SIGNATURE in got["result"],
    "rows": [mem.pack_row(r) for r in rows],
    "bob": [mem.pack_row(r) for r in bob],
})
