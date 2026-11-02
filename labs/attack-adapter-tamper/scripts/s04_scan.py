"""Step 4: scan both revisions. Safetensors has no pickle to run, so the scanners agree
they are clean. torch.load(weights_only=True) on these files returns the tensor dict;
it does not execute code, and it does not read adapter_config.json. Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/s04_scan.py
Requires Step 3's victim clones.
"""
import json
import re
import subprocess

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors import safe_open  # noqa: E402

import desk  # noqa: E402

dirs = desk.hub_dirs()
files = [("v1.0", dirs["v1"] / "adapter_model.safetensors"),
         ("main", dirs["main"] / "adapter_model.safetensors")]
missing = [str(p.name) for _, p in files if not p.exists()]
if missing:
    raise SystemExit("[!!] missing victim clones: run Step 3 first")


def run(cmd, path):
    p = subprocess.run(cmd + [str(path)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def picklescan(path):
    rc, out = run(["picklescan", "-p"], path)
    found = re.findall(r"dangerous import '([^']+)' FOUND", out)
    if found:
        return f"'{found[0]}' FOUND ({rc})"
    if "not a pickle" in out.lower() or "could not parse" in out.lower() or "error" in out.lower():
        return f"not a pickle ({rc})"
    return f"clean ({rc})"


def modelscan(path):
    rc, out = run(["modelscan", "-p"], path)
    if re.search(r"unsafe operator|CRITICAL", out):
        return f"issues ({rc})"
    if "No issues" in out or rc == 0:
        return f"No issues found ({rc})"
    return f"skipped ({rc})"


def weights_only(path):
    """torch.load on a safetensors file reads tensors. It does not run a pickle program."""
    try:
        obj = torch.load(path, weights_only=True)
    except Exception as e:  # noqa: BLE001 - a refusal is itself the result
        return f"refused ({type(e).__name__})"
    n = len(obj) if isinstance(obj, dict) else "?"
    return f"clean ({n} tensors)"


print(f"{'revision':<10} {'picklescan':<22} {'modelscan':<22} {'torch weights_only':<28} safetensors tensors")
report = {}
for label, path in files:
    with safe_open(path, framework="pt") as f:
        n = len(f.keys())
    row = (picklescan(path), modelscan(path), weights_only(path), n)
    report[label] = {"picklescan": row[0], "modelscan": row[1], "weights_only": row[2], "tensors": n}
    print(f"{label:<10} {row[0]:<22} {row[1]:<22} {row[2]:<28} {n}")
print("scanners and weights_only see a tensor file; they do not read adapter_config.json and they do not run the model")
labkit.out("scan.json").write_text(json.dumps(report, indent=1) + "\n")
