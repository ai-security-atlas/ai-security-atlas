"""Step D1: provenance on a real save, a read-time policy, and revoke. Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/d1_provenance.py
Live trials read the principals Step 3 wrote. The counterfactual block is a separate
principal: Dana's sign-off went through save_memory, and the poisoned row was inserted
by the operator for the branch labeled "if the write had succeeded".
"""
import json

import labkit

labkit.banner()

import mem  # noqa: E402


def walk(seed):
    return f"walk-{seed}"


def cf(seed):
    return f"cf-{seed}"


mem.note_backend()
s03 = json.loads(labkit.inp("work/s03.json").read_text())
wrote = [r["seed"] for r in s03["rows"] if r["wrote"]]
print(f"live poison principals: {len(wrote)}/{mem.WALK_N}")
sample = walk(wrote[0]) if wrote else walk(0)
live_rows = mem.memory_rows(mem.DESK, sample)
live_poison = [r for r in live_rows if mem.poisoned_text(r.get("note") or "") and r.get("session") != mem.COUNTERFACTUAL_SESSION]
live_user = [r for r in live_rows if r.get("source") == "user"]
print(f"live poison source: {live_poison[0]['source'] if live_poison else 'none'}")
print(f"live poison url: {live_poison[0]['url'] if live_poison else 'none'}")
print(f"live user source: {live_user[0]['source'] if live_user else 'none'}")
print(f"live user has canary: {'yes' if live_user and mem.CANARY in live_user[0]['note'] else 'no'}")

print(f"[note] {mem.WALK_N} live trials each (seeds 0-{mem.WALK_N - 1})", flush=True)
policy = mem.measure("mp-policy", mem.WALK_N, "d1-live-policy", principal_for=walk)
mem.print_rates("live-policy", policy)
filt = mem.measure("mp-filter", mem.WALK_N, "d1-live-filter", principal_for=walk)
mem.print_rates("live-filter", filt)
for row in policy:
    row["wrote"] = row["seed"] in wrote
for row in filt:
    row["wrote"] = row["seed"] in wrote
mem.print_conditional("live-policy", policy)
mem.print_conditional("live-filter", filt)
print(f"live-policy signature: {sum(r['signature'] for r in policy)}/{mem.WALK_N}")
print(f"live-filter signature: {sum(r['signature'] for r in filt)}/{mem.WALK_N}")

demo = "cf-demo"
mem.prepare_counterfactual(demo)
tagged = mem.call_tool("mp-policy", "read_memory", {}, principal=demo, session="d1-tagged")
filtered = mem.call_tool("mp-filter", "read_memory", {}, principal=demo, session="d1-filter")
print("counterfactual labeled: if the write had succeeded")
print(f"counterfactual tagged source tool: {'yes' if '"source": "tool"' in tagged['result'] else 'no'}")
print(f"counterfactual tagged has url: {'yes' if mem.URL in tagged['result'] else 'no'}")
print(f"counterfactual filter read has signature: {'yes' if mem.SIGNATURE in filtered['result'] else 'no'}")
print(f"counterfactual filter read has canary: {'yes' if mem.CANARY in filtered['result'] else 'no'}")
gone = mem.reset_memory(mem.DESK, demo, source="tool")["removed"]
left = mem.call_tool("mp-recall", "read_memory", {}, principal=demo, session="d1-revoked")
print(f"revoked poison rows: {gone}")
print(f"loaded notes after revoke contain canary: {'yes' if mem.CANARY in left['result'] else 'no'}")
print(f"loaded notes after revoke contain signature: {'yes' if mem.SIGNATURE in left['result'] else 'no'}")
mem.reset_memory(mem.DESK, demo)

print(f"[note] {mem.WALK_N} counterfactual trials each (seeds 0-{mem.WALK_N - 1})", flush=True)
cf_policy = mem.measure("mp-policy", mem.WALK_N, "d1-cf-policy", principal_for=cf,
                        setup=lambda p, _s: mem.prepare_counterfactual(p))
mem.print_rates("cf-policy", cf_policy)
cf_filter = mem.measure("mp-filter", mem.WALK_N, "d1-cf-filter", principal_for=cf)
mem.print_rates("cf-filter", cf_filter)
print(f"cf-policy signature: {sum(r['signature'] for r in cf_policy)}/{mem.WALK_N}")
print(f"cf-filter signature: {sum(r['signature'] for r in cf_filter)}/{mem.WALK_N}")
mem.save("d1.json", {"trials": mem.WALK_N, "live_writes": len(wrote), "profiles": {
    "live-policy": [mem.pack_row(r) for r in policy],
    "live-filter": [mem.pack_row(r) for r in filt],
    "cf-policy": [mem.pack_row(r) for r in cf_policy],
    "cf-filter": [mem.pack_row(r) for r in cf_filter],
}})
