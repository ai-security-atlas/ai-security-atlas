"""Step D3: a CI gate that inspects a change without running it, in the low-trust job. Run from labs/:
    docker compose run --rm sandbox python attack-dependency/scripts/d3_ci_gate.py --revision main --requirements work/requirements-pr.txt
    docker compose run --rm sandbox python attack-dependency/scripts/d3_ci_gate.py --revision <reviewed sha> --requirements work/requirements.lock

The sandbox service plays the untrusted "inspect" job of a pull-request pipeline: no network, a
read-only checkout, no credentials. The gate is static: it reads git objects and text files and
never imports, installs or loads anything from the change. Checks:
  1. the model revision is a full commit sha (branches and tags move);
  2. the remote code at that commit hashes to the reviewed values (work/reviewed.json);
  3. every requirement is pinned with == and carries a --hash;
  4. every package is on the approved list (the names in work/requirements.lock), and a name
     within two edits of an approved one is reported as a likely typosquat;
  5. the requirements file does not add its own index (--index-url / --extra-index-url).
It exits 1 on any failure; a trusted publish job (with credentials) would run only on PASS.
"""
import argparse
import json
import os
import re
import socket
import sys

import labkit
import local_hub

labkit.banner()

REPO = "acme/tiny-sentiment"
ap = argparse.ArgumentParser()
ap.add_argument("--revision", required=True)
ap.add_argument("--requirements", required=True, help="path relative to the lab folder, e.g. work/requirements.lock")
args = ap.parse_args()

# inputs come from the (read-only) checkout; the gate writes nothing
hub = local_hub.Hub(labkit.inp("work/hub"))
reviewed_file, lock_file, req_file = (labkit.inp("work/reviewed.json"), labkit.inp("work/requirements.lock"),
                                      labkit.inp(args.requirements))
for f in (reviewed_file, lock_file, req_file):
    if not f.exists():
        sys.exit(f"[!!] missing {f.relative_to(labkit.lab())}: run Steps 1, 6 and D2 first")
reviewed = json.loads(reviewed_file.read_text())

secret_like = [k for k, v in os.environ.items() if v and re.search(r"TOKEN|SECRET|PASSWORD|API_KEY", k)]
nics = sorted(n for _, n in socket.if_nameindex())
print("CI gate (inspect job): static checks only; nothing from the change is imported, installed or loaded")
print(f"job context: network interfaces {', '.join(nics)} · checkout writable: "
      f"{'yes' if os.access(labkit.lab(), os.W_OK) else 'no'} · secret-like env vars: {', '.join(secret_like) or 'none'}")

problems = []


def check(ok, msg):
    print(f"[{'pass' if ok else 'FAIL'}] {msg}")
    if not ok:
        problems.append(msg)


# 1-2: the model pin
rev = args.revision
check(local_hub.is_sha(rev), f"model revision {rev if not local_hub.is_sha(rev) else rev[:12] + '...'} "
      f"{'is a full commit sha' if local_hub.is_sha(rev) else 'is a branch or tag, not a commit sha'}")
sha = hub.resolve(REPO, rev)
if not sha:
    check(False, f"revision {rev} does not exist in {REPO}")
else:
    cfg = json.loads(hub.show(REPO, sha, "config.json"))
    code = sorted({t.split(".")[0] + ".py" for t in cfg.get("auto_map", {}).values()})
    bad = [f for f in code if local_hub.sha256_bytes(hub.show(REPO, sha, f)) != reviewed["code"].get(f)]
    check(not bad, f"remote code at {sha[:7]} " + (f"differs from the review: {', '.join(bad)}" if bad
                                                    else f"matches the review ({', '.join(code)})"))


# 3-5: the requirements
def reqs(path):
    text = re.sub(r"\\\n", " ", path.read_text())
    return [ln.split("#")[0].strip() for ln in text.splitlines() if ln.split("#")[0].strip()]


def name_of(line):
    return re.split(r"[=<>!~ \[;]", line, 1)[0].lower().replace("_", "-")


def edits(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


approved = {name_of(ln) for ln in reqs(lock_file)}
name = args.requirements.split("/")[-1]
for line in reqs(req_file):
    if line.startswith("-"):
        check(not re.match(r"--(extra-)?index-url", line), f"{name}: option {line.split()[0]}")
        continue
    pkg = name_of(line)
    check("==" in line and "--hash=sha256:" in line,
          f"{name}: {line.split()[0]} " + ("is pinned with a hash" if "--hash=" in line else "has no --hash"))
    near = [a for a in approved if a != pkg and edits(a, pkg) <= 2]
    check(pkg in approved, f"{name}: {pkg} " + ("is approved" if pkg in approved else
          f"is not approved ({edits(near[0], pkg)} edit from {near[0]}: likely typosquat)" if near else "is not approved"))

print(f"GATE: {'FAIL (%d problems)' % len(problems) if problems else 'PASS'}"
      f" -> the trusted publish job {'does not run' if problems else 'may run with these exact pins'}")
sys.exit(1 if problems else 0)
