"""Step D2: four budgets, not one — separate meters for turns, tokens, tool calls and wall-clock.
Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/d2_budgets.py
Policy A ("a single global cap") counts model turns only. Policy B adds token, tool-call and
wall-clock budgets on top of the same turn cap, and refuses the next model call once a dimension is
over; the abort names the dimension that tripped. The chatty board is benign: its checks pass, so
policy A lets one request spend a large token bill that policy B cuts off — the tradeoff, measured.
"""
import json

import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
print(f"[note] policy A: steps <= {loop.WORK_CAP} · policy B: steps <= {loop.BUDGETS['steps']}, "
      f"tokens <= {loop.BUDGETS['tokens']:,}, tool calls <= {loop.BUDGETS['tool_calls']}, "
      f"wall <= {loop.BUDGETS['wall_s']} s", flush=True)
try:
    s03 = json.loads(labkit.out("s03.json").read_text())
    est = max(r["usage"].get("total_tokens", 0) for r in s03["rows"])
    print(f"[note] pre-flight estimate (external-api safety): one poisoned run to the hard cap "
          f"billed {est:,} tokens in Step 3; print this before pointing the desk at a paid endpoint",
          flush=True)
except (OSError, ValueError):
    print("[note] pre-flight estimate: run Step 3 first to measure one capped run's token bill", flush=True)

print("chatty board under policy A (a single global cap):")
chatty_a = loop.measure("loop-chatty", 2, "d2-a", guard={"cap": loop.WORK_CAP}, model=model)
row_a = loop.condition_row("chatty-A", chatty_a)
loop.print_row(row_a)

print("chatty board under policy B (separate budgets):")
chatty_b = loop.measure("loop-chatty", 2, "d2-b", guard={"cap": loop.WORK_CAP, "budgets": loop.BUDGETS}, model=model)
row_b = loop.condition_row("chatty-B", chatty_b)
loop.print_row(row_b)

print("poisoned board under policy B:")
poison = loop.measure("loop-poisoned", 2, "d2-p", guard={"cap": loop.WORK_CAP, "budgets": loop.BUDGETS}, model=model)
row_p = loop.condition_row("poisoned-B", poison)
loop.print_row(row_p)

print("clean board under policy B (false-positive check):")
clean = loop.measure("loop-clean", 2, "d2-c", guard={"cap": loop.WORK_CAP, "budgets": loop.BUDGETS}, model=model)
row_c = loop.condition_row("clean-B", clean)
loop.print_row(row_c)

# The same meters applied across a session of requests, like a per-key gateway budget: policy B's
# mid-run refusals already cut the runs above, so compare what one principal's session cost under
# each policy. Policy A's poisoned row comes from D1's measured run (working cap, no budgets).
try:
    d1 = json.loads(labkit.out("d1.json").read_text())
    uncapped = d1["rows"][0]          # D1's "capped" row: the poisoned board under the working cap alone
    poisoned_a = uncapped["tokens"]
    poisoned_a_note = f"{uncapped['steps']:g} turns"
except (OSError, ValueError, KeyError):
    poisoned_a, poisoned_a_note = None, "run D1 first"
rows_b = chatty_b[:1] + poison[:1] + clean[:1]
b_total = sum(r["usage"]["total_tokens"] for r in rows_b)
print("session replay for one principal (chatty, then poisoned, then clean — the measured runs above):")
if poisoned_a is not None:
    a_total = chatty_a[0]["usage"]["total_tokens"] + poisoned_a + clean[0]["usage"]["total_tokens"]
    print(f"  policy A (turns only): chatty {chatty_a[0]['usage']['total_tokens']:,} tokens in "
          f"{chatty_a[0]['steps']} turns · poisoned {poisoned_a:,} tokens in {poisoned_a_note} (D1's run) · "
          f"clean {clean[0]['usage']['total_tokens']:,} · session total {a_total:,} tokens")
else:
    a_total = None
    print(f"  policy A (turns only): chatty {chatty_a[0]['usage']['total_tokens']:,} tokens in "
          f"{chatty_a[0]['steps']} turns · poisoned {poisoned_a_note} · clean {clean[0]['usage']['total_tokens']:,}")
refusals = [f"{r['stopped']}:{r['abort']} at turn {r['steps']}" for r in rows_b if r["stopped"] != "done"]
print(f"  policy B (four budgets): the same three requests billed {b_total:,} tokens; "
      f"refusals: {'; '.join(refusals) if refusals else 'none'}")
loop.save("d2.json", {"chatty_a": [loop.slim(r) for r in chatty_a], "chatty_b": [loop.slim(r) for r in chatty_b],
                      "poison": [loop.slim(r) for r in poison], "clean": [loop.slim(r) for r in clean],
                      "rows": [row_a, row_b, row_p, row_c], "budgets": loop.BUDGETS,
                      "session_a_tokens": a_total, "session_b_tokens": b_total})
loop.save("d2.json", {"chatty_a": [loop.slim(r) for r in chatty_a], "chatty_b": [loop.slim(r) for r in chatty_b],
                      "poison": [loop.slim(r) for r in poison], "clean": [loop.slim(r) for r in clean],
                      "rows": [row_a, row_b, row_p, row_c], "budgets": loop.BUDGETS})
