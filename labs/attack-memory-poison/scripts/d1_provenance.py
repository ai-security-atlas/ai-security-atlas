"""Step D1: provenance on the stored poison, a read-time policy, a user-only filter, and revoke.
Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/d1_provenance.py
The trials read the principals Step 3 left with a poison row (live or inserted) and Dana's
sign-off. The revoke demo uses its own principal, so Step D3 still finds the Step 3 rows.
"""
import json

import labkit

labkit.banner()

import mem  # noqa: E402


def walk(seed):
    return f"walk-{seed}"


mem.note_backend()
s03 = json.loads(labkit.inp("work/s03.json").read_text())
poisoned = [r for r in s03["rows"] if r.get("poison")]
live_n = sum(r["poison"] == "live" for r in poisoned)
print(f"principals with a poison row: {len(poisoned)}/{mem.WALK_N} (live {live_n}, inserted {len(poisoned) - live_n})")
rows = mem.memory_rows(mem.DESK, walk(0))
bad = [r for r in rows if mem.poisoned_text(r.get("note") or "")]
user = [r for r in rows if r.get("source") == "user"]
print(f"poison row source: {bad[0]['source'] if bad else 'none'}")
print(f"poison row url: {bad[0]['url'] if bad else 'none'}")
print(f"user row source: {user[0]['source'] if user else 'none'}")
print(f"user row has canary: {'yes' if user and mem.CANARY in user[0]['note'] else 'no'}")
tagged = mem.call_tool("mp-policy", "read_memory", {}, principal=walk(0), session="d1-tagged")
filtered = mem.call_tool("mp-filter", "read_memory", {}, principal=walk(0), session="d1-filter")
print(f"tagged read shows source tool: {'yes' if '"source": "tool"' in tagged['result'] else 'no'}")
print(f"tagged read has url: {'yes' if mem.URL in tagged['result'] else 'no'}")
print(f"filter read has signature: {'yes' if mem.SIGNATURE in filtered['result'] else 'no'}")
print(f"filter read has canary: {'yes' if mem.CANARY in filtered['result'] else 'no'}")

print(f"[note] {mem.WALK_N} trials each (seeds 0-{mem.WALK_N - 1}), Bob's email", flush=True)
policy = mem.mark(mem.measure("mp-policy", mem.WALK_N, "d1-policy", principal_for=walk), s03["rows"])
mem.print_rates("mp-policy", policy)
filt = mem.mark(mem.measure("mp-filter", mem.WALK_N, "d1-filter", principal_for=walk), s03["rows"])
mem.print_rates("mp-filter", filt)
mem.print_conditional("policy", policy)
mem.print_conditional("filter", filt)

demo = "d1-demo"
mem.prepare_poisoned(demo, "d1-demo")
gone = mem.reset_memory(mem.DESK, demo, source="tool")["removed"]
left = mem.call_tool("mp-recall", "read_memory", {}, principal=demo, session="d1-revoked")
print(f"revoked poison rows: {gone}")
print(f"loaded notes after revoke contain canary: {'yes' if mem.CANARY in left['result'] else 'no'}")
print(f"loaded notes after revoke contain signature: {'yes' if mem.SIGNATURE in left['result'] else 'no'}")
mem.reset_memory(mem.DESK, demo)
mem.save("d1.json", {"trials": mem.WALK_N, "poisoned": len(poisoned), "live_writes": live_n, "profiles": {
    "policy": [mem.pack_row(r) for r in policy],
    "filter": [mem.pack_row(r) for r in filt],
}})
