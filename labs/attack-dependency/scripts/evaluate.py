"""Evaluate: run each delivery path under each condition and record whether the payload ran. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/evaluate.py

Needs Steps 1-6 and D2 (the hub with the moved v1.0 tag, the index, the lock and PR files).
Every row runs in a fresh process, and "ran" means the canary marker appeared (for the gate row:
the gate passed the change). Compares with expected/evaluate.json and ends with
"RESULT: REPRODUCED" or "RESULT: MISMATCH (...)".
"""
import json
import os
import shutil
import subprocess
import sys

import labkit
from local_hub import pypi

labkit.banner()

W = labkit.work()
os.environ["ATLAS_WORK"] = str(W)  # the payload writes its marker here (this lab's work/)
S = labkit.lab() / "scripts"
need = ["reviewed.json", "requirements.lock", "requirements-pr.txt", "index/simple", "index-mirror/simple"]
missing = [f for f in need if not (W / f).exists()]
if missing:
    sys.exit(f"[!!] missing work/{missing[0]}: run Steps 1-6 and D2 first")
reviewed = json.loads((W / "reviewed.json").read_text())["commit"]
m = labkit.marker()


def script(name, *args):
    return subprocess.run([sys.executable, str(S / name), *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def pip_then_python(index, *req):
    venv = W / "venv-eval"
    shutil.rmtree(venv, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, stdin=subprocess.DEVNULL)
    py = str(venv / "bin" / "python")
    subprocess.run([py, "-m", "pip", "install", "--index-url", index, *req, "--no-cache-dir",
                    "--disable-pip-version-check", "--no-input"], capture_output=True, stdin=subprocess.DEVNULL)
    subprocess.run([py, "-c", "pass"], capture_output=True, stdin=subprocess.DEVNULL)  # any interpreter start


ROWS = [
    ("remote code", "from_pretrained(main, trust_remote_code=True)",
     lambda: script("s03_victim_load.py", "--revision", "main", "--trust-remote-code")),
    ("remote code", "from_pretrained(main, trust_remote_code=False)",
     lambda: script("s03_victim_load.py", "--revision", "main")),
    ("remote code", "tag v1.0 (moved), trust_remote_code=True",
     lambda: script("s03_victim_load.py", "--revision", "v1.0", "--trust-remote-code")),
    ("remote code", "D1 policy: reviewed sha only",
     lambda: script("d1_pinned_load.py", "--revision", "main")),
    ("package", "pip install acme-tokenizr (the typo)",
     lambda: pip_then_python(pypi.Index(W / "index").url, "acme-tokenizr")),
    ("package", "--require-hashes -r requirements-pr.txt",
     lambda: pip_then_python(pypi.Index(W / "index").url, "--require-hashes", "-r", str(W / "requirements-pr.txt"))),
    ("package", "--require-hashes -r requirements.lock, bad mirror",
     lambda: pip_then_python(pypi.Index(W / "index-mirror").url, "--require-hashes", "-r", str(W / "requirements.lock"))),
]

got = {}
print(f"{'vector':<12} {'condition':<52} payload")
for vector, cond, run in ROWS:
    m.unlink(missing_ok=True)
    run()
    got[cond] = int(m.exists())
    print(f"{vector:<12} {cond:<52} {'ran' if got[cond] else 'blocked'}")
m.unlink(missing_ok=True)
gate = script("d3_ci_gate.py", "--revision", "main", "--requirements", "work/requirements-pr.txt")
cond = "D3 CI gate: main + requirements-pr.txt"
got[cond] = int(gate.returncode == 0)
print(f"{'CI gate':<12} {cond:<52} {'passed' if got[cond] else 'refused'}")
shutil.rmtree(W / "venv-eval", ignore_errors=True)

attacks = [c for _, c, _ in ROWS if c in ("from_pretrained(main, trust_remote_code=True)",
                                          "tag v1.0 (moved), trust_remote_code=True", "pip install acme-tokenizr (the typo)")]
defended = [c for c in got if c not in attacks]
print(f"undefended paths: {sum(got[c] for c in attacks)}/{len(attacks)} ran · "
      f"defended: {sum(got[c] for c in defended)}/{len(defended)} ran or passed")
print("(sandbox: see Step D4; the remote code runs, the host work/ folder stays untouched)")

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
