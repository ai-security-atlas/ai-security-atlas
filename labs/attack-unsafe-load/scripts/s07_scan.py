"""Step 7: three pickle scanners and torch's allowlist on four files. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s07_scan.py

Builds work/variant.pt: the same labkit.INERT_CODE, called through timeit.timeit instead
of exec. That is a known, publicly documented gap in denylist scanners (see the README's
Further Reading); the variant exists to show why allowlists win. Do not add more gadgets.
"""
import json
import re
import subprocess
import timeit
import zipfile

import labkit

labkit.banner()

import torch  # noqa: E402
import torch.serialization as ts  # noqa: E402


class Payload:
    def __reduce__(self):
        # On unpickling, pickle calls timeit.timeit(INERT_CODE, "pass", default_timer, 1).
        return (timeit.timeit, (labkit.INERT_CODE, "pass", timeit.default_timer, 1))


torch.manual_seed(0)
model = torch.nn.Sequential(torch.nn.Linear(4, 3), torch.nn.ReLU(), torch.nn.Linear(3, 2))
sd = model.state_dict()
sd._metadata["__canary__"] = Payload()
torch.save(sd, labkit.out("variant.pt"))
print("wrote work/variant.pt (same payload body, called through timeit.timeit)")

W = labkit.work()


def run(*cmd):
    p = subprocess.run(cmd, cwd=W, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def picklescan(f):
    rc, out = run("picklescan", "-p", f)
    found = re.findall(r"dangerous import '([^']+)' FOUND", out)
    if found:
        return f"'{found[0]}' FOUND ({rc})"
    return f"not a pickle ({rc})" if "could not parse" in out else f"clean ({rc})"


def modelscan(f):
    rc, out = run("modelscan", "-p", f)
    op = re.search(r"unsafe operator '([^']+)'", out)
    if op:
        return f"CRITICAL {op.group(1)} ({rc})"
    return f"skipped ({rc})" if rc == 3 else f"No issues found ({rc})"


def fickling(f):
    if not f.endswith(".pt"):
        return "n/a"
    # fickling's CLI reads raw pickles, not torch ZIPs: extract data.pkl first.
    stem = f[:-3]
    pkl = W / "scan" / stem / "data.pkl"
    pkl.parent.mkdir(parents=True, exist_ok=True)
    pkl.write_bytes(zipfile.ZipFile(W / f).read(f"{stem}/data.pkl"))
    (W / "scan" / f"{stem}.json").unlink(missing_ok=True)  # fickling appends to an existing report
    rc, _ = run("fickling", "--check-safety", "--json-output", f"scan/{stem}.json", f"scan/{stem}/data.pkl")
    return f"{json.loads((W / 'scan' / f'{stem}.json').read_text())['severity']} ({rc})"


def allowlist(f):
    if not f.endswith(".pt"):
        return "n/a (no pickle)"
    bad = sorted(ts.get_unsafe_globals_in_checkpoint(W / f))  # a set: sort for stable output
    return f"rejects {', '.join(bad)}" if bad else "allowed"


files = ["benign.pt", "malicious.pt", "variant.pt", "model.safetensors"]
missing = [f for f in files if not (W / f).exists()]
if missing:
    raise SystemExit(f"[!!] missing {missing}: run Steps 1, 2 and 6 first")

print("\n(exit codes in brackets; denylist scanners on the left, torch's allowlist on the right)")
print(f"{'file':<18} {'picklescan':<30} {'modelscan':<24} {'fickling':<30} weights_only allowlist")
notes = {"benign.pt": "", "malicious.pt": "", "variant.pt": "", "model.safetensors": ""}
for f in files:
    row = [picklescan(f), modelscan(f), fickling(f), allowlist(f)]
    if f == "benign.pt" and "UNSAFE" in row[2]:
        notes[f] = "   <- fickling false positive"
    if f == "variant.pt" and row[1].startswith("No issues"):
        notes[f] = "   <- modelscan 0.8.8 miss (known, public)"
    print(f"{f:<18} {row[0]:<30} {row[1]:<24} {row[2]:<30} {row[3]}{notes[f]}")

# The decompiler view: fickling shows what the pickle program does, as Python.
_, out = run("fickling", "scan/malicious/data.pkl")
print("\nfickling scan/malicious/data.pkl (decompiled, cut):")
for ln in out.splitlines():
    if "import exec" in ln or "exec(" in ln:
        print("  " + (ln[:110] + "..." if len(ln) > 110 else ln))
