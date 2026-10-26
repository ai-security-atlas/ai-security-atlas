#!/usr/bin/env python3
"""Payload review for the labs (stdlib only; run by the CI `labs` job).

    python3 labs/_shared/test_inert.py

1. labkit.INERT_CODE must match the allowed shape exactly (AST allowlist):
     import os, time
     p = os.path.join(os.environ.get(<str>, <str>), 'canary-marker.txt')
     open(p, 'w').write('<CANARY> ...' % (<allowed fields>))   # fields: os.getpid(), os.getuid(), int(time.time())
     print(<str and p joined with +>)
2. `__reduce__`, and any reference to `exec`/`eval`, may appear only in labkit.py and the
   three LAB-01 payload-site scripts. Elsewhere, `exec` is allowed only as an argument of
   torch's safe_globals()/add_safe_globals() (the "allowlisting exec" pitfall demo).
   Calling exec()/eval() directly is never allowed, in any file.
   In the payload sites, every `__reduce__` must return exactly one of ALLOWED_REDUCE
   (exec or timeit.timeit applied to labkit.INERT_CODE).
3. labkit.TARGET is the fixed LAB-02 canary.
Exits 0 when every check passes, 1 otherwise.
"""

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABS = HERE.parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True  # keep labs/_shared free of __pycache__
import labkit  # noqa: E402

PAYLOAD_SITES = {
    "_shared/labkit.py",
    "attack-unsafe-load/scripts/s02_craft_payload.py",
    "attack-unsafe-load/scripts/s07_scan.py",
    "attack-unsafe-load/scripts/s08_hub_setup.py",
}
SELF = "_shared/test_inert.py"
DANGEROUS = {"exec", "eval"}
SAFE_GLOBALS_FUNCS = {"safe_globals", "add_safe_globals"}
ALLOWED_FIELDS = {"os.getpid()", "os.getuid()", "int(time.time())"}
ALLOWED_REDUCE = {
    "(exec, (labkit.INERT_CODE,))",
    "(timeit.timeit, (labkit.INERT_CODE, 'pass', timeit.default_timer, 1))",
}

errors = []


def fail(msg):
    errors.append(msg)


def src(node):
    return ast.unparse(node)


def check_inert_code(code):
    tree = ast.parse(code)
    body = tree.body
    if len(body) != 4:
        return fail(f"INERT_CODE: expected 4 statements, found {len(body)}")
    s_import, s_assign, s_write, s_print = body

    # 1. import os, time
    if not (isinstance(s_import, ast.Import)
            and sorted(a.name for a in s_import.names) == ["os", "time"]
            and all(a.asname is None for a in s_import.names)):
        fail(f"INERT_CODE stmt 1 must be 'import os, time', got: {src(s_import)}")

    # 2. p = os.path.join(os.environ.get(<str>, <str>), 'canary-marker.txt')
    ok = (isinstance(s_assign, ast.Assign) and len(s_assign.targets) == 1
          and isinstance(s_assign.targets[0], ast.Name) and s_assign.targets[0].id == "p")
    if ok:
        v = s_assign.value
        ok = (isinstance(v, ast.Call) and src(v.func) == "os.path.join" and len(v.args) == 2
              and not v.keywords
              and isinstance(v.args[0], ast.Call) and src(v.args[0].func) == "os.environ.get"
              and len(v.args[0].args) == 2
              and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in v.args[0].args)
              and isinstance(v.args[1], ast.Constant) and v.args[1].value == "canary-marker.txt")
    if not ok:
        fail(f"INERT_CODE stmt 2 must assign p from os.path.join(os.environ.get(...), 'canary-marker.txt'), got: {src(s_assign)}")

    # 3. open(p, 'w').write('<CANARY> ...' % (<allowed fields>))
    ok = isinstance(s_write, ast.Expr) and isinstance(s_write.value, ast.Call)
    if ok:
        c = s_write.value
        ok = (isinstance(c.func, ast.Attribute) and c.func.attr == "write"
              and isinstance(c.func.value, ast.Call) and src(c.func.value) == "open(p, 'w')"
              and len(c.args) == 1 and not c.keywords)
        if ok:
            fmt = c.args[0]
            ok = (isinstance(fmt, ast.BinOp) and isinstance(fmt.op, ast.Mod)
                  and isinstance(fmt.left, ast.Constant) and isinstance(fmt.left.value, str)
                  and fmt.left.value.startswith(labkit.CANARY + " ")
                  and isinstance(fmt.right, ast.Tuple)
                  and all(src(e) in ALLOWED_FIELDS for e in fmt.right.elts))
    if not ok:
        fail(f"INERT_CODE stmt 3 must be open(p, 'w').write('{labkit.CANARY} ...' % (pid/uid/time)), got: {src(s_write)}")

    # 4. print(<str constants and p joined with +>)
    def concat_ok(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return True
        if isinstance(n, ast.Name) and n.id == "p":
            return True
        return isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and concat_ok(n.left) and concat_ok(n.right)

    ok = (isinstance(s_print, ast.Expr) and isinstance(s_print.value, ast.Call)
          and src(s_print.value.func) == "print" and len(s_print.value.args) == 1
          and not s_print.value.keywords and concat_ok(s_print.value.args[0]))
    if not ok:
        fail(f"INERT_CODE stmt 4 must be one print of strings and p, got: {src(s_print)}")

    if labkit.CANARY not in code:
        fail("INERT_CODE does not contain labkit.CANARY")


def safe_globals_args(tree):
    """ids of exec/eval Name nodes that are arguments of safe_globals()/add_safe_globals()."""
    allowed = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in SAFE_GLOBALS_FUNCS:
                for a in n.args:
                    for m in ast.walk(a):
                        allowed.add(id(m))
    return allowed


def check_tree(path, rel):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    except SyntaxError as e:
        return fail(f"{rel}: syntax error: {e}")
    is_site = rel in PAYLOAD_SITES
    allowed = safe_globals_args(tree)
    for n in ast.walk(tree):
        line = getattr(n, "lineno", "?")
        # direct exec(...)/eval(...) calls: never
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in DANGEROUS:
                fail(f"{rel}:{line}: direct call to {name}() is not allowed")
        if is_site:
            if isinstance(n, ast.FunctionDef) and n.name == "__reduce__":
                returns = [r for r in ast.walk(n) if isinstance(r, ast.Return)]
                if not returns:
                    fail(f"{rel}:{line}: __reduce__ must return one of {sorted(ALLOWED_REDUCE)}")
                for r in returns:
                    got = src(r.value) if r.value else "None"
                    if got not in ALLOWED_REDUCE:
                        fail(f"{rel}:{r.lineno}: __reduce__ must return one of {sorted(ALLOWED_REDUCE)}, got: {got}")
            continue
        if isinstance(n, ast.FunctionDef) and n.name == "__reduce__":
            fail(f"{rel}:{line}: __reduce__ is allowed only in the payload sites")
        elif isinstance(n, ast.Attribute) and n.attr in DANGEROUS | {"__reduce__"} and id(n) not in allowed:
            fail(f"{rel}:{line}: reference to {n.attr} is allowed only in the payload sites")
        elif isinstance(n, ast.Name) and n.id in DANGEROUS and id(n) not in allowed:
            fail(f"{rel}:{line}: reference to {n.id} is allowed only in the payload sites (or inside safe_globals())")
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and "__reduce__" in n.value:
            fail(f"{rel}:{line}: string mentioning __reduce__ is allowed only in the payload sites")


def main():
    check_inert_code(labkit.INERT_CODE)
    if labkit.TARGET != "CANARY-7731":
        fail(f"labkit.TARGET must be 'CANARY-7731', got {labkit.TARGET!r}")

    files = 0
    for path in sorted(LABS.rglob("*.py")):
        rel = path.relative_to(LABS).as_posix()
        if rel == SELF or "/work/" in f"/{rel}" or "node_modules" in rel:
            continue
        files += 1
        check_tree(path, rel)

    if errors:
        for e in errors:
            print(f"[!!] {e}")
        print(f"FAIL: {len(errors)} problem(s)")
        return 1
    print(f"[ok] INERT_CODE matches the allowlist; TARGET is {labkit.TARGET}")
    print(f"[ok] exec/eval/__reduce__ confined to payload sites ({files} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
