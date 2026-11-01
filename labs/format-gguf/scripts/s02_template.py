"""Step 2: the chat template is a program the server runs on every request. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/s02_template.py
"""
import jinja2
from jinja2 import meta, nodes

import labkit

labkit.banner()

import ggufkit  # noqa: E402
import serving  # noqa: E402

tpl = ggufkit.template_of(ggufkit.ORIGINAL)
ast = jinja2.Environment().parse(tpl)             # parsing only: nothing is rendered
kinds = {"for loops": nodes.For, "if blocks": nodes.If, "outputs": nodes.Output, "string concatenations": nodes.Add,
         "comparisons": nodes.Compare}
counts = {k: len(list(ast.find_all(v))) for k, v in kinds.items()}
inputs = sorted(meta.find_undeclared_variables(ast))
print(f"embedded template: {len(tpl)} chars; parsed as Jinja: " + ", ".join(f"{n} {k}" for k, n in counts.items()))
print(f"inputs it reads at render time: {', '.join(inputs)}")

base = serving.BASE_URL
serving.wait_ready(base)
props = serving.get(base, "/props").json() or {}
served = props.get("chat_template", "")
print(f"[note] {base}: model {props.get('model_path', '?').rsplit('/', 1)[-1]}, "
      f"chat_template from /props == embedded: {served == tpl}")

server_prompt = ggufkit.apply_template(base)
python_prompt = ggufkit.render_sandboxed(tpl, ggufkit.ONE_USER)
print(f"POST /apply-template  {ggufkit.short(server_prompt, 120)}")
print(f"jinja2 in Python      {ggufkit.short(python_prompt, 120)}")
print(f"same prompt: {server_prompt == python_prompt}  (the user typed only 'hi'; the template added the rest)")

hits, answers = ggufkit.canary_rate(base)
print()
print("10 fixed questions, temperature 0, through /v1/chat/completions:")
for q, a in answers[:3]:
    print(f"  {q:<36} -> {ggufkit.short(a, 60)}")
print("  ...")
print(f"canary {ggufkit.CANARY} in {hits}/10 answers")

ggufkit.save("s02_template.json", {"chars": len(tpl), "counts": counts, "inputs": inputs, "props_equal": served == tpl,
                                   "server_prompt": server_prompt, "python_prompt": python_prompt,
                                   "hits": hits, "answers": answers})
