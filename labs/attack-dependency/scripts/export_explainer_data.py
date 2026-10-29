"""Maintainer tool: regenerate explainer/data.js from a reference run. Run from the repo root, then labs/:

    python3 labs/_tools/verify.py attack-dependency          # the full run; writes work/verify.log
    docker compose run --rm workbench python attack-dependency/scripts/export_explainer_data.py

verify.py runs every README Do block (workbench and sandbox steps, and the host checks) and keeps
the output in work/verify.log, one "== <step-id> ==" section per step. Everything in data.js is
parsed from that log: file names and sizes, auto_map, commit shas, the injected diff lines, the
payload, error and pip lines, the revision table, the gate verdicts and the sandbox probes.
A student's own work/ folder never changes the shipped data.js.
"""
import json
import re
import sys

import labkit

labkit.banner()

LAB = labkit.lab()
log = LAB / "work" / "verify.log"
if not log.exists():
    sys.exit("[!!] missing work/verify.log: run python3 labs/_tools/verify.py attack-dependency first")

sec, cur = {}, None
for line in log.read_text().splitlines():
    m = re.match(r"^== (\w+) ==$", line)
    if m:
        cur = sec.setdefault(m.group(1), [])
    elif cur is not None and not line.startswith("$ docker") and not line.startswith(("$ test", "$ cat")):
        cur.append(line)


def find(sid, pattern, group=0):
    for line in sec[sid]:
        m = re.search(pattern, line)
        if m:
            return m.group(group)
    sys.exit(f"[!!] {sid}: no line matches {pattern!r}")


def after(sid, start, stop=None):
    """Lines of a section after the line starting with `start` (until a blank line or `stop`)."""
    lines, on = [], False
    for line in sec[sid]:
        if on:
            if line == "" or (stop and line.startswith(stop)):
                break
            lines.append(line)
        elif line.startswith(start):
            on = True
    return lines


s1 = sec["S1"]
files = [[m.group(1), int(m.group(2))] for m in (re.match(r"^\s+(\S+\.\w+)\s+(\d+) bytes$", ln) for ln in s1) if m]
auto_map = [list(m.groups()) for m in (re.match(r"^\s+(Auto\w+)\s+-> (\S+\.py) :: (\w+)$", ln) for ln in s1) if m]
diff = [ln for ln in after("S2", "$ git diff v1.0 main --") if not ln.startswith("@@")]
hunk = find("S2", r"^@@ .* @@ (.*)$", 1)
data = {
    "canary": labkit.CANARY,
    "marker": f"work/{labkit.marker().name}",
    "repo": "acme/tiny-sentiment",
    "files": files,
    "auto_map": auto_map,
    "v10": find("S1", r"commit ([0-9a-f]{40})", 1),
    "main": find("S2", r"pushed v1\.1 to main: ([0-9a-f]{40})", 1),
    "commits": [ln.split(None, 2) for ln in after("S2", "$ git log")],
    "card": find("S1", r"^model card: (.*)$", 1),
    "code_hashes": [[m.group(1), m.group(2)] for m in
                    (re.match(r"^\s+(\S+\.py)\s+sha256 (\w+)$", ln) for ln in s1) if m],
    "hunk": hunk,
    "diff": [ln[1:] for ln in diff if ln.startswith("+")],
    "module": find("S3", r"^loaded (transformers_modules\.\S+)$", 1),
    "payload_line": find("S3", r"^\[payload\] .*"),
    "predict_main": find("S3", r"^predict\(.*"),
    "predict_reviewed": find("D1", r"^predict\(.*"),
    "refused": find("S4", r"^BLOCKED: (.*)$", 1).replace(" You can inspect the repository content at <snapshot> .", ""),
    "refused_hint": find("S4", r"Please pass the argument .*"),
    "revisions": [re.split(r"\s{2,}", ln.strip()) for ln in sec["S5"] if re.match(r"^(main|v1\.0|[0-9a-f]{12})", ln)],
    "tag_move": find("S5", r"^-- attacker: (.*)$", 1),
    "pkg": {
        "index": [ln.split()[:2] for ln in sec["S6"] if re.match(r"^\s+acme-\w+\s+acme_", ln)],
        "wheel": [ln.split()[0] for ln in after("S6", "acme-tokenizr wheel contents:")],
        "pth": find("S6", r"^acme_tokenizr\.pth: (.*)$", 1),
        "pip": find("S6", r"^\$ pip install .*"),
        "installed": find("S6", r"^Successfully installed .*"),
        "payload_line": find("S6", r"^\[payload\] .*"),
        "encode": find("S6", r"^acme_tokenizer\.encode.*"),
    },
    "d1": [ln.strip() for ln in sec["D1"] if re.match(r"^(REFUSED|VERIFIED|pinned commit|\s+(ok|MISMATCH))", ln)],
    "d2": {
        "lock": find("D2", r"^work/requirements\.lock:\s+(.*)$", 1),
        "pr": find("D2", r"^work/requirements-pr\.txt:\s+(.*)$", 1),
        "cases": [[ln.strip() for ln in after("D2", f"({c}) $")] for c in "abc"],
    },
    "gate": {
        "context": find("D3", r"^job context: (.*)$", 1),
        "fail": [ln for ln in after("D3", "job context:", "GATE:") if ln.startswith("[FAIL]")],
        "verdicts": [ln for ln in sec["D3"] if ln.startswith("GATE:")],
    },
    "isolation": {
        "payload": find("D4", r"^\[payload\] .*"),
        "sandbox_marker": find("D4", r"^marker in sandbox: (\w+)", 1) == "True",
        "dns": find("D4", r"^dns canary\.invalid: (.*)$", 1),
        "egress": find("D4", r"^egress 192\.0\.2\.1:9: (.*)$", 1),
        "ro_write": find("D4", r"^write to /labs: (.*)$", 1),
        "host_marker": find("D4", r"^host marker: (\w+)", 1),
    },
    "evaluate": find("EVAL", r"^undefended paths: .*"),
}
out = LAB / "explainer" / "data.js"
body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
body = re.sub(r'(,)(?="\w+":)', ",\n ", body)  # one key per line, for readable diffs
out.write_text("/* Generated by scripts/export_explainer_data.py from a reference run (work/verify.log). Do not edit by hand.\n"
               " * Loaded with a plain <script> tag (never fetch: it breaks file://). */\n"
               f"window.LAB_DATA = {body};\n", encoding="utf-8")
print(f"[ok] wrote {out.relative_to(LAB.parent)} ({out.stat().st_size} bytes): {len(files)} repo files, "
      f"{len(data['diff'])} injected lines, {len(data['revisions'])} revisions, {len(data['gate']['fail'])} gate failures")
