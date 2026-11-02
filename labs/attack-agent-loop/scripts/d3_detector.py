"""Step D3: loop detection — the same tool call with the same arguments, again and again.
Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/d3_detector.py
The detector counts (tool, arguments) pairs in the run's own trace and aborts gracefully when one
pair repeats more than the allowance, with a cost report of what the run spent and what the hard
cap would have allowed. The clean board never repeats a call, so the detector costs it nothing.
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
print(f"[note] detector allowance: {loop.REPEATS} repeats of one (tool, arguments) pair", flush=True)

poison = loop.measure("loop-poisoned", 3, "d3", guard={"detector": loop.REPEATS}, model=model)
row_p = loop.condition_row("poisoned", poison)
loop.print_row(row_p)
detected = [r for r in poison if r["stopped"] == "loop-detected"]
if detected:
    r = detected[0]
    print(f"first abort: {r['abort']} at turn {r['steps']}, after {r['tool_calls']} calls and "
          f"{r['usage'].get('total_tokens', 0):,} tokens")

clean = loop.measure("loop-clean", 2, "d3-clean", guard={"detector": loop.REPEATS}, model=model)
row_c = loop.condition_row("clean", clean)
loop.print_row(row_c)
print(f"false positives on the clean board: {sum(r['stopped'] == 'loop-detected' for r in clean)}/{len(clean)}")

ref = loop.med(poison, lambda r: r["usage"].get("total_tokens", 0))
print(f"cost report: the detector stopped runs at a median of "
      f"{loop.med(poison, lambda r: r['steps']):g} turns and {ref:,.0f} tokens; "
      f"Step 3's undefended runs spent a median of 50 turns at the hard cap")
loop.save("d3.json", {"poisoned": [loop.slim(r) for r in poison], "clean": [loop.slim(r) for r in clean],
                      "rows": [row_p, row_c], "repeats": loop.REPEATS})
