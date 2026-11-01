"""Evaluate: the attack and each defense, measured again in one run. Run from labs/ with llama-server on
work/tampered.gguf (the Do block starts it) and llama-server-hardened on the publisher's file:
    docker compose run --rm workbench python format-gguf/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import subprocess
import sys

import labkit

labkit.banner()

import ggufkit  # noqa: E402
import serving  # noqa: E402

ggufkit.need("tampered", "probe")
man = json.loads(ggufkit.MANIFEST.read_text())
O, T, P = (ggufkit.FILES[n] for n in ("original", "tampered", "probe"))
ro, rt = ggufkit.reader(O), ggufkit.reader(T)
pinned = ggufkit.PINNED_TEMPLATE.read_text()


def rate(n):
    return "0/10" if n == 0 else (">=8/10" if n >= 8 else f"other ({n}/10)")


def pf(ok):
    return "pass" if ok else "FAIL"


def tensor_sha(path):
    out = subprocess.run([sys.executable, "-m", "gguf.scripts.gguf_hash", "--no-layer", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return next(line.split()[1] for line in out.splitlines() if line.startswith("sha256"))


got, raw = {}, {}
th_o, th_t = ggufkit.tensor_hashes(ro), ggufkit.tensor_hashes(rt)
got["tensors identical, original vs tampered"] = f"{sum(th_t.get(k) == v for k, v in th_o.items())}/{len(th_o)}"
got["tensor-only hash (gguf_hash) vs pin"] = " / ".join(pf(tensor_sha(p) == man["tensor_sha256"]) for p in (O, T))
got["whole-file sha256 vs publisher pin"] = " / ".join(pf(ggufkit.file_sha256(p) == man["file_sha256"]) for p in (O, T))
got["metadata sha256 vs reviewer pin"] = " / ".join(pf(ggufkit.metadata_sha256(r) == man["metadata_sha256"]) for r in (ro, rt))
allow = man["chat_template_allowlist"]
got["template allowlist"] = " / ".join("accept" if ggufkit.sha256_bytes(ggufkit.template_of(p)) in allow else "reject"
                                       for p in (O, T))

serving.wait_ready(serving.BASE_URL)
props = serving.get(serving.BASE_URL, "/props").json() or {}
if not props.get("model_path", "").endswith("tampered.gguf"):
    sys.exit("[!!] llama-server is not serving work/tampered.gguf; start it as the Evaluate Do block shows")
n_orig, _ = ggufkit.canary_rate(serving.HARDENED_URL, key=serving.LAB_KEY)
n_tamp, _ = ggufkit.canary_rate(serving.BASE_URL)
n_pin = 0
for q in ggufkit.QUESTIONS:      # the pinned template, rendered outside the file, sent as a raw prompt
    p = ggufkit.render_sandboxed(pinned, [{"role": "user", "content": q}])
    n_pin += ggufkit.CANARY in ((serving.complete(serving.BASE_URL, p, n_predict=40).json() or {}).get("content") or "")
raw["canary"] = [n_orig, n_tamp, n_pin]
got["canary in answers: publisher's GGUF"] = rate(n_orig)
got["canary in answers: tampered GGUF, embedded template"] = rate(n_tamp)
got["canary in answers: tampered GGUF, pinned template"] = rate(n_pin)

probe_tpl = ggufkit.template_of(P)
try:
    out = ggufkit.render_unsafe(probe_tpl, ggufkit.ONE_USER)
    got["probe, plain jinja2 (CVE-2024-34359 pattern)"] = "class name read" if ggufkit.CANARY in out else "nothing"
except Exception as e:  # noqa: BLE001
    got["probe, plain jinja2 (CVE-2024-34359 pattern)"] = type(e).__name__
try:
    ggufkit.render_sandboxed(probe_tpl, ggufkit.ONE_USER)
    got["probe, ImmutableSandboxedEnvironment"] = "rendered"
except Exception as e:  # noqa: BLE001
    got["probe, ImmutableSandboxedEnvironment"] = type(e).__name__

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<52} {'got':<18} expected")
diff = []
for cond, want in expected.items():
    if got.get(cond) != want:
        diff.append(cond)
    print(f"{cond:<52} {str(got.get(cond)):<18} {want}")
print(f"(canary counts: publisher's {n_orig}/10, tampered {n_tamp}/10, tampered + pinned template {n_pin}/10)")
ggufkit.save("evaluate.json", {"got": got, "raw": raw})
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
