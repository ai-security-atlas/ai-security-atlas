"""Step 1: the board, the tool catalog and where the notice lives. No model call. Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s01_board.py
"""
import labkit

labkit.banner()

import loop  # noqa: E402

cat = loop.get("/admin/agent")
page = loop.get("/admin/agent?profile=loop-poisoned")
granted = page["profiles"][0]["tools"]
mine = [t for t in cat["tools"] if t["name"] in ("loop_check_item", "loop_spawn_verifier")]
core = [t for t in cat["tools"] if t["name"] in ("list_tickets", "read_ticket")]
print(f"MCP {cat['server']} protocol {cat['protocol']}")
print(f"catalog tools {len(cat['tools'])} (this lab adds {len(mine)}: {' '.join(sorted(t['name'] for t in mine))})")
for t in mine + core:
    risk = t.get("risk") or "read"
    print(f"tool {t['name']} risk {risk} def_sha256 {t['sha256'][:16]}…")
print(f"loop-poisoned grants {len(granted)}: {' '.join(granted)}")
print(f"loop-delegate grants {len(granted) + 1}: {' '.join(granted)} loop_spawn_verifier")
print(f"app-side hard cap: every profile max_steps {loop.HARD_CAP} (the runner adds its own meters)")

flagged = loop.FLAGGED
stored = next(t for t in loop.SPEC["tickets"] if t.get("flagged"))
print(f"flagged ticket {flagged} stored message has canary: {'yes' if loop.CANARY in stored['message'] else 'no'}")
clean = loop.tool_call("loop-clean", "loop_check_item", {"ticket_id": flagged})
poison = loop.tool_call("loop-poisoned", "loop_check_item", {"ticket_id": flagged})
flaky = loop.tool_call("loop-flaky", "loop_check_item", {"ticket_id": flagged})
print(f"loop-clean check {flagged} has canary: {'yes' if loop.CANARY in clean else 'no'} -> {clean}")
print(f"loop-flaky check {flagged} has canary: {'yes' if loop.CANARY in flaky else 'no'} -> {flaky}")
print(f"loop-poisoned check {flagged} has canary: {'yes' if loop.CANARY in poison else 'no'}")
print("the poisoned check result (from assets/board.json):")
print(poison)
deleg = loop.tool_call("loop-delegate", "loop_spawn_verifier", {"ticket_id": flagged})
print(f"loop-delegate spawn report has canary: {'yes' if loop.CANARY in deleg else 'no'}")
chatty = loop.tool_call("loop-chatty", "loop_check_item", {"ticket_id": flagged})
print(f"loop-chatty check starts: {chatty[:60]}… ({len(chatty):,} chars)")
print("meters this lab accounts separately: model turns · model tokens · tool calls · wall-clock seconds")
loop.save("s01.json", {"protocol": cat["protocol"], "server": cat["server"], "catalog": len(cat["tools"]),
                       "tools": sorted(t["name"] for t in mine), "grants": granted,
                       "clean_result": clean, "poisoned_result": poison, "flaky_result": flaky,
                       "spawn_result": deleg, "chatty_chars": len(chatty),
                       "flagged": flagged, "items": loop.ITEMS})
