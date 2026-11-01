"""Step D4: render each GGUF's template in jinja2's ImmutableSandboxedEnvironment (the llama-cpp-python 0.2.72 fix). Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/d4_sandbox.py
"""
import labkit

labkit.banner()

import ggufkit  # noqa: E402

ggufkit.need("tampered", "probe")
clean = ggufkit.render_sandboxed(ggufkit.PINNED_TEMPLATE.read_text(), ggufkit.ONE_USER)
rows = {}
print(f"{'file':<10} {'plain jinja2.Environment':<34} ImmutableSandboxedEnvironment")


def outcome(fn, tpl):
    try:
        out = fn(tpl, ggufkit.ONE_USER)
    except Exception as e:  # noqa: BLE001 - the sandbox's refusal is the measurement
        return {"error": f"{type(e).__name__}: {e}"}
    return {"same_as_pinned": out == clean, "canary": ggufkit.CANARY in out, "chars": len(out)}


def say(o):
    if "error" in o:
        return o["error"].split(":")[0]
    if o["same_as_pinned"]:
        return "renders, same prompt as pinned"
    return "renders, canary in prompt" if o["canary"] else "renders, different prompt"


for n, p in ggufkit.FILES.items():
    tpl = ggufkit.template_of(p)
    rows[n] = {"plain": outcome(ggufkit.render_unsafe, tpl), "sandbox": outcome(ggufkit.render_sandboxed, tpl)}
    print(f"{n:<10} {say(rows[n]['plain']):<34} {say(rows[n]['sandbox'])}")
print()
print(f"sandbox on probe.gguf: {rows['probe']['sandbox'].get('error')}")
print("sandbox on tampered.gguf: the hidden instruction is plain string concatenation, so it renders "
      f"(canary in prompt: {rows['tampered']['sandbox'].get('canary')})")
ggufkit.save("d4_sandbox.json", rows)
