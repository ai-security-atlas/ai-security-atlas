"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/
after Steps 1-6, with Step D2 (sandbox run + host check) captured on the host:

    docker compose run --rm workbench python attack-unsafe-load/scripts/cleanup.py --marker-only
    { docker compose run --rm -T sandbox python attack-unsafe-load/scripts/d2_isolation_probe.py work/malicious.pt; test -e attack-unsafe-load/work/canary-marker.txt && echo "host marker: present" || echo "host marker: absent"; } > attack-unsafe-load/work/d2.txt
    docker compose run --rm workbench python attack-unsafe-load/scripts/export_explainer_data.py

Everything in data.js comes from files and outputs of that run: the opcode tapes, a symbolic
trace of the pickle VM stack (what each opcode leaves on the stack), the ZIP entries, the
payload and error lines printed by s03_victim_load.py, the safetensors layout and the D2 probes.
A student's own work/ folder never changes the shipped data.js.
"""
import json
import pickletools
import re
import struct
import subprocess
import sys
import zipfile

import labkit

labkit.banner()

import torch  # noqa: E402

LAB, W = labkit.lab(), labkit.work()
need = ["benign.pt", "malicious.pt", "model.safetensors", "d2.txt"]
missing = [f for f in need if not (W / f).exists()]
if missing:
    sys.exit(f"[!!] missing work/{missing[0]}: run Steps 1-6 and capture D2 first (see the docstring)")


def short(s, n=22):
    return s if len(s) <= n else s[:n - 1] + "…"


def tape(path):
    z = zipfile.ZipFile(path)
    data = z.read(next(n for n in z.namelist() if n.endswith("/data.pkl")))
    rows = []
    for op, arg, pos in pickletools.genops(data):
        a = None if arg is None else (repr(arg) if isinstance(arg, str) and op.name != "GLOBAL" else str(arg))
        rows.append([pos, op.name, None if a is None else short(a, 48), arg])
    return rows


def simulate(rows, inj):
    """Run the pickle VM symbolically: after each opcode, the stack as [[label, role], ...]."""
    stack, memo, marks, trace = [], {}, [], []

    def push(label, role, raw=None, bad=False):
        stack.append({"label": label, "role": "bad" if bad else role, "raw": raw})

    for pos, name, _, arg in rows:
        bad = inj[0] <= pos <= inj[1]
        if name == "GLOBAL":
            push(arg.split(" ")[1], "violet", arg, bad)
        elif name in ("BINUNICODE", "SHORT_BINUNICODE"):
            push(short(repr(arg), 16), "teal", arg, bad)
        elif name in ("BININT1", "BININT2", "BININT"):
            push(str(arg), "teal", arg, bad)
        elif name in ("NEWFALSE", "NEWTRUE"):
            push(str(name == "NEWTRUE"), "teal", name == "NEWTRUE", bad)
        elif name == "EMPTY_TUPLE":
            push("()", "teal", (), bad)
        elif name == "EMPTY_DICT":
            push("{}", "teal", {}, bad)
        elif name == "MARK":
            marks.append(len(stack))
            push("MARK", "muted")
        elif name in ("TUPLE", "TUPLE1", "TUPLE2", "TUPLE3"):
            if name == "TUPLE":
                start = marks.pop()
                items = stack[start + 1:]
                del stack[start:]
            else:
                n = int(name[-1])
                items = stack[-n:]
                del stack[-n:]
            label = short("(" + ", ".join(i["label"] for i in items) + (",)" if len(items) == 1 else ")"))
            push(label, "teal", tuple(i["raw"] for i in items), bad or any(i["role"] == "bad" for i in items))
        elif name == "BINPERSID":
            pid = stack.pop()["raw"]
            push(f"storage {pid[2]}", "teal", pid, bad)
        elif name == "REDUCE":
            args, fn = stack.pop(), stack.pop()
            f = fn["raw"].split(" ")[1]
            if f == "_rebuild_tensor_v2":
                push("tensor " + "×".join(map(str, args["raw"][2])), "teal", None, bad)
            elif f == "OrderedDict":
                push("OrderedDict", "violet", 0, bad)
            else:
                push(f"{f}(…) → None", "bad" if fn["role"] == "bad" else "violet", None, bad)
        elif name == "BINPUT":
            memo[arg] = stack[-1]
        elif name == "BINGET":
            stack.append(dict(memo[arg]))
        elif name == "SETITEM":
            del stack[-2:]
        elif name == "SETITEMS":
            start = marks.pop()
            n = (len(stack) - start - 1) // 2
            del stack[start:]
            top = stack[-1]
            if top["label"].startswith("OrderedDict"):
                stack[-1] = dict(top, label=f"OrderedDict({n} keys)")
        elif name == "BUILD":
            stack.pop()
        elif name == "STOP":
            stack[-1] = dict(stack[-1], label="result: " + stack[-1]["label"])
        elif name != "PROTO":
            sys.exit(f"[!!] simulate(): opcode {name} not handled")
        trace.append([[i["label"], i["role"]] for i in stack])
    return trace


benign, malicious = tape(W / "benign.pt"), tape(W / "malicious.pt")
i0 = next(k for k, r in enumerate(malicious) if r[3] == "__canary__")
i1 = next(k for k in range(i0, len(malicious)) if malicious[k][1] == "REDUCE")
i1 += malicious[i1 + 1][1] == "BINPUT"  # the memo write of exec's result is injected too
assert i1 - i0 + 1 == len(malicious) - len(benign), "injected rows must equal the opcode diff"
injected = [malicious[i0][0], malicious[i1][0]]
trace = simulate(malicious, injected)

entries = [[i.filename, i.file_size] for i in zipfile.ZipFile(W / "benign.pt").infolist()
           if not i.filename.endswith(".data/serialization_id")]

victim = str(LAB / "scripts" / "s03_victim_load.py")
run = lambda *a: subprocess.run([sys.executable, victim, *a], capture_output=True, text=True,  # noqa: E731
                                cwd=LAB.parent, stdin=subprocess.DEVNULL).stdout.splitlines()
unsafe, default = run("work/malicious.pt", "unsafe"), run("work/malicious.pt")
labkit.marker().unlink(missing_ok=True)
payload_line = next(ln for ln in unsafe if ln.startswith("[payload]"))
model_out = next(ln for ln in unsafe if ln.startswith("load_state_dict OK")).split("-> ", 1)[1]
wo_error = next(ln.strip() for ln in default if "WeightsUnpickler error" in ln)

raw = (W / "model.safetensors").read_bytes()
hlen = struct.unpack("<Q", raw[:8])[0]
header = json.loads(raw[8:8 + hlen])
st_tensors = [[k, v["dtype"], v["shape"], v["data_offsets"]] for k, v in header.items() if k != "__metadata__"]
st_tensors.sort(key=lambda t: t[3][0])

d2 = (W / "d2.txt").read_text().splitlines()
pick = lambda prefix: next(ln.split(": ", 1)[1] for ln in d2 if ln.startswith(prefix))  # noqa: E731

sd = torch.load(W / "benign.pt", weights_only=True)
data = {
    "canary": labkit.CANARY,
    "marker": f"work/{labkit.marker().name}",
    "benign_ops": [r[:3] for r in benign],
    "malicious_ops": [r[:3] for r in malicious],
    "injected": injected,
    "trace": trace,
    "zip_entries": entries,
    "weights": {k: [round(x, 3) for x in v.flatten().tolist()] for k, v in sd.items()},
    "payload_line": payload_line,
    "model_out": model_out,
    "weights_only_error": wo_error,
    "st_layout": {"len": 8, "header": hlen, "data": len(raw) - 8 - hlen},
    "st_tensors": st_tensors,
    "isolation": {
        "sandbox_marker": pick("marker in sandbox").startswith("True"),
        "sandbox_payload": next(ln for ln in d2 if ln.startswith("[payload]")),
        "dns": pick("dns canary.invalid"),
        "egress": pick("egress 192.0.2.1:9"),
        "ro_write": pick("write to /labs"),
        "host_marker": pick("host marker"),
    },
}
out = LAB / "explainer" / "data.js"
body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
body = re.sub(r'(\]\],|\],)(?=\[|")', r"\1\n", body)  # one opcode/trace row per line, for readable diffs
out.write_text("/* Generated by scripts/export_explainer_data.py from a reference container run. Do not edit by hand.\n"
               " * Loaded with a plain <script> tag (never fetch: it breaks file://). */\n"
               f"window.LAB_DATA = {body};\n", encoding="utf-8")
print(f"[ok] wrote {out.relative_to(LAB.parent)} ({out.stat().st_size} bytes): "
      f"{len(benign)} benign ops, {len(malicious)} malicious ops, injected {injected}")
