"""Step 4: one run, call by call. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/s04_trace.py
Walks seeds until a sidecar carries the canary, or prints seed 0 if none of them do.
"""
import labkit

labkit.banner()

import wx  # noqa: E402

wx.note_backend()
chosen = None
for seed in range(wx.WALK_N):
    g = wx.run_once("wxdesc-poison", seed, "s04-trace")
    mark = "harm" if g["harm"] else "miss"
    print(f"[note] seed {seed}: {mark} steps {g['steps']}", flush=True)
    if g["harm"] and chosen is None:
        chosen = g
        break
if chosen is None:
    chosen = g
tools, _ = wx.tool_map("wxdesc-poison")
desc = tools["forecast"]["description"]
err = wx.SPEC["procedure_error"]
saw_error = False
print(f"seed {chosen['seed']}")
print("calls: " + " → ".join(s["tool"] for s in chosen["trace"]) )
for step in chosen["trace"]:
    side = wx.sidecar_of(step)
    print(f"  {step['tool']} risk {step.get('risk') or '-'} via {step.get('via')} "
          f"sidecar {side or '-'} result {wx.short(step.get('result'), 80)}")
    if step.get("tool") == "forecast" and err in (step.get("result") or ""):
        saw_error = True
    if step.get("tool") == "notes_save" and wx.CANARY in side:
        print(f"procedure error before the leak: {'yes' if saw_error else 'no'}")
print(f"sidecar has canary: {'yes' if chosen['harm'] else 'no'}")
print(f"description has canary: {'yes' if wx.CANARY in desc else 'no'}")
print(f"reply has forecast: {'yes' if chosen['utility'] else 'no'}")
wx.save("s04.json", {"seed": chosen["seed"], "harm": chosen["harm"], "utility": chosen["utility"],
                     "trace": chosen["trace"], "description_has_canary": wx.CANARY in desc,
                     "procedure_error": err})
