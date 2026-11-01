"""Step D2: gate the chat template before any runtime sees it: allowlist, static lint, and a diff for the reviewer. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/d2_template_gate.py
The template is parsed, never rendered.
"""
import difflib
import json
import re

import jinja2
from jinja2 import nodes

import labkit

labkit.banner()

import ggufkit  # noqa: E402

ggufkit.need("tampered", "probe")
allow = json.loads(ggufkit.MANIFEST.read_text())["chat_template_allowlist"]
pinned = ggufkit.PINNED_TEMPLATE.read_text()


def lint(tpl):
    """Findings from the parsed template: attribute or item access to a name starting with '_'."""
    ast = jinja2.Environment().parse(tpl)
    found = [n.attr for n in ast.find_all(nodes.Getattr) if n.attr.startswith("_")]
    found += [n.arg.value for n in ast.find_all(nodes.Getitem)
              if isinstance(n.arg, nodes.Const) and isinstance(n.arg.value, str) and n.arg.value.startswith("_")]
    return found


def pieces(tpl):
    """Split a one-line template at its tags so a diff shows readable fragments."""
    return [p for p in re.split(r"(?=\{[{%])", tpl) if p]


rows = {}
print(f"{'file':<10} {'template sha256':<16} {'on allowlist':<26} {'lint (dunder access)':<26} verdict")
for n, p in ggufkit.FILES.items():
    tpl = ggufkit.template_of(p)
    h = ggufkit.sha256_bytes(tpl)
    found = lint(tpl)
    ok = h in allow
    verdict = "accept" if ok and not found else "reject (" + ", ".join(
        x for x in ["not allowlisted" if not ok else "", "lint" if found else ""] if x) + ")"
    lint_txt = ", ".join(f"{x} x{found.count(x)}" for x in sorted(set(found))) or "none"
    rows[n] = {"sha256": h, "allowlisted": ok, "lint": found, "verdict": verdict}
    print(f"{n:<10} {h[:12]:<16} {('yes (' + allow[h] + ')') if ok else 'no':<26} {lint_txt:<26} {verdict}")

print()
print("diff for the reviewer: pinned/smollm2-360m.jinja -> work/tampered.gguf's template")
diff = [d for d in difflib.unified_diff(pieces(pinned), pieces(ggufkit.template_of(ggufkit.FILES["tampered"])),
                                       lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]
for d in diff:
    print("  " + ggufkit.short(d, 118))
print(f"lint alone would accept the tampered template: {not rows['tampered']['lint']}")
ggufkit.save("d2_template_gate.json", {"rows": rows, "diff": diff})
