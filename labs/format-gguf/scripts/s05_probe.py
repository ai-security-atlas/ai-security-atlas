"""Step 5: the same embedded template in two template engines. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/s05_probe.py python
    docker compose run --rm workbench python format-gguf/scripts/s05_probe.py llama-server
`python` renders work/probe.gguf's template the way llama-cpp-python 0.2.30-0.2.71 did (CVE-2024-34359:
a plain jinja2.Environment). `llama-server` asks the server, started on work/probe.gguf, to render it.
The probe only reads a class name; it never walks further into the interpreter and calls nothing.
"""
import sys

import labkit

labkit.banner()

import ggufkit  # noqa: E402
import serving  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "python"
ggufkit.need("probe")
tpl = ggufkit.template_of(ggufkit.FILES["probe"])
pinned = ggufkit.PINNED_TEMPLATE.read_text()
probe = tpl[len(pinned):] if tpl.startswith(pinned) else tpl
clean = ggufkit.render_sandboxed(pinned, ggufkit.ONE_USER)
print(f"work/probe.gguf template = the publisher's {len(pinned)} chars + {len(probe)} chars:")
print(f"  {probe}")

if mode == "python":
    print("renderer: jinja2.Environment(loader=jinja2.BaseLoader(), trim_blocks=True, lstrip_blocks=True)"
          " (llama-cpp-python 0.2.30-0.2.71)")
    try:
        out = ggufkit.render_unsafe(tpl, ggufkit.ONE_USER)
        error = None
    except Exception as e:  # noqa: BLE001 - report whatever the engine raises
        out, error = "", f"{type(e).__name__}: {e}"
else:
    base = serving.BASE_URL
    serving.wait_ready(base)
    props = serving.get(base, "/props").json() or {}
    print(f"renderer: llama-server {props.get('build_info')} (its own C++ Jinja engine), serving "
          f"{props.get('model_path', '?').rsplit('/', 1)[-1]}; /props template == probe.gguf's: {props.get('chat_template') == tpl}")
    out = ggufkit.apply_template(base)
    error = None if not out.startswith("[HTTP") else out

after = out[len(clean):] if out.startswith(clean) else out
print(f"rendered prompt, after the normal part: {after!r}" if not error else f"render failed: {error}")
reached = ggufkit.CANARY in after
print(f"-> canary {ggufkit.CANARY}: {'YES, the template read a Python class name' if reached else 'no, the probe rendered nothing'}")
ggufkit.save(f"s05_{mode}.json", {"mode": mode, "probe": probe, "after": after, "error": error, "reached": reached})
