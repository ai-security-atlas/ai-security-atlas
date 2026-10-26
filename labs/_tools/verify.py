#!/usr/bin/env python3
"""Run a lab README's Do blocks exactly as a student would, then check the output.

    python3 labs/_tools/verify.py <node-id>          # e.g. attack-unsafe-load
    VERIFY_SLOW=1 python3 labs/_tools/verify.py <node-id>

Stdlib only (host Python >= 3.9). Maintainer tool; see labs/_template/README.md.

* Step ids: SETUP1..3 (### Setup N), S1..Sn (### Step N), D1..Dn (### Step DN),
  EVAL (## Evaluate), CLEANUP (## Cleanup).
* Each step's single ```bash Do block runs line by line from labs/, stdin=/dev/null.
  `-T` is inserted after `docker compose run`. Comment lines (e.g. `# host`) are skipped.
  A non-zero exit is logged, not fatal: some steps fail on purpose; checks decide.
* COMPOSE_PROFILES is exported from the Setup 1 row matching LAB_BACKEND
  (environment, else labs/.env); the `none` row is used when LAB_BACKEND is unset.
* Skipped: steps marked "(optional, slow)" or listed in expected/slow.txt (unless
  VERIFY_SLOW=1); steps tagged "> Model backend:" when LAB_BACKEND is unset;
  Read steps and "Try (browser)" lists (never run).
* Output goes to labs/<node-id>/work/verify.log with "== <step-id> ==" markers.
  After each step, every "step-id<TAB>regex" line of expected/checks.txt for that step
  is searched in its section (Python re, MULTILINE). The first miss prints the
  section and exits 1.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^(`{3,})(\S*)\s*$")
DOCKER_RUN = re.compile(r"\bdocker compose run\b(?!\s+-T\b)")


def read_env_file(path):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = re.sub(r"\s+#.*$", "", v).strip().strip('"').strip("'")
        env[k.strip()] = v
    return env


def parse_sections(text):
    """Return [(step_id, heading, body_lines)] in README order, ignoring headings inside fences."""
    sections, h2, cur, fence = [], None, None, None
    for line in text.splitlines():
        m = FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1).startswith(fence) and not m.group(2):
                fence = None
        if fence is None or m:
            if line.startswith("## "):
                h2 = line[3:].strip()
                cur = None
                if h2 in ("Evaluate", "Cleanup"):
                    cur = ("EVAL" if h2 == "Evaluate" else "CLEANUP", line, [])
                    sections.append(cur)
                continue
            if line.startswith("### "):
                cur = None
                title = line[4:].strip()
                sid = None
                if h2 == "Setup":
                    m2 = re.match(r"Setup (\d+)\b", title)
                    sid = m2 and f"SETUP{m2.group(1)}"
                elif h2 in ("Walkthrough", "Defend"):
                    m2 = re.match(r"Step (D?)(\d+)\b", title)
                    sid = m2 and (f"D{m2.group(2)}" if m2.group(1) else f"S{m2.group(2)}")
                if sid:
                    cur = (sid, line, [])
                    sections.append(cur)
                continue
        if cur is not None:
            cur[2].append(line)
    return sections


def bash_block(body):
    """The ```bash block after **Do** (or the first one if there is no **Do** label)."""
    start = 0
    for i, line in enumerate(body):
        if line.strip().startswith("**Do**"):
            start = i
            break
    out, inside = [], False
    for line in body[start:]:
        if not inside and re.match(r"^```bash\s*$", line):
            inside = True
            continue
        if inside:
            if line.startswith("```"):
                return out
            out.append(line)
    return None


def commands(lines):
    """Join backslash continuations; drop blanks and comments."""
    cmds, buf = [], ""
    for line in lines:
        s = line.rstrip()
        if buf:
            buf += " " + s.strip()
        elif s.strip() and not s.strip().startswith("#"):
            buf = s.strip()
        if buf.endswith("\\"):
            buf = buf[:-1].rstrip()
            continue
        if buf:
            cmds.append(buf)
            buf = ""
    if buf:
        cmds.append(buf)
    return cmds


def profiles_for(sections, backend):
    """COMPOSE_PROFILES value from the Setup 1 table row matching backend (or 'none')."""
    rows = []
    for sid, _, body in sections:
        if sid != "SETUP1":
            continue
        for line in body:
            if line.startswith("|") and "COMPOSE_PROFILES=" in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                m = re.search(r"COMPOSE_PROFILES=([\w,-]*)", line)
                rows.append((cells[0].strip("`").lower(), m.group(1)))
    want = backend or "none"
    for name, value in rows:
        if name == want:
            return value
    for name, value in rows:  # e.g. "any backend or none"
        if re.search(r"\bany\b", name) or (want == "none" and "none" in name):
            return value
    return None


def run(cmd, env, log):
    cmd = DOCKER_RUN.sub("docker compose run -T", cmd)
    print(f"$ {cmd}", flush=True)
    log.append(f"$ {cmd}")
    p = subprocess.Popen(["/bin/bash", "-c", cmd], cwd=LABS, env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        line = line.rstrip("\n")
        print(line, flush=True)
        log.append(line)
    rc = p.wait()
    if rc:
        log.append(f"[exit {rc}]")
        print(f"[exit {rc}]", flush=True)
    return rc


def main():
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        return 2
    node = sys.argv[1].strip("/")
    lab = LABS / node
    readme = lab / "README.md"
    if not readme.exists():
        print(f"[!!] no README at {readme}")
        return 2

    sections = parse_sections(readme.read_text(encoding="utf-8"))
    checks = []
    checks_file = lab / "expected" / "checks.txt"
    if checks_file.exists():
        for n, line in enumerate(checks_file.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            if "\t" not in line:
                print(f"[!!] {checks_file}:{n}: expected 'step-id<TAB>regex'")
                return 2
            sid, rx = line.split("\t", 1)
            checks.append((sid.strip(), re.compile(rx, re.M)))
    slow_file = lab / "expected" / "slow.txt"
    slow_ids = set(slow_file.read_text(encoding="utf-8").split()) if slow_file.exists() else set()
    run_slow = os.environ.get("VERIFY_SLOW") == "1"

    dotenv = read_env_file(LABS / ".env")
    backend = os.environ.get("LAB_BACKEND", dotenv.get("LAB_BACKEND", "")).strip()
    profiles = profiles_for(sections, backend)
    if profiles is None:
        print(f"[!!] Setup 1 has no COMPOSE_PROFILES row for backend {backend or 'none'!r}")
        return 1
    env = dict(os.environ, COMPOSE_PROFILES=profiles)
    print(f"[verify] {node} · backend {backend or 'none'} · COMPOSE_PROFILES={profiles}"
          f" · slow steps {'on' if run_slow else 'off'}", flush=True)

    log, ran, skipped = [], [], []

    def write_log():
        (lab / "work").mkdir(parents=True, exist_ok=True)
        (lab / "work" / "verify.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    for sid, heading, body in sections:
        cmds = commands(bash_block(body) or [])
        reason = None
        if not cmds:
            reason = "no Do block (Read step)"
        elif ("(optional, slow)" in heading or sid in slow_ids) and not run_slow:
            reason = "slow (set VERIFY_SLOW=1)"
        elif any(l.startswith("> Model backend:") for l in body) and not backend:
            reason = "needs a model backend (LAB_BACKEND unset)"
        if reason:
            print(f"[skip] {sid}: {reason}", flush=True)
            skipped.append(sid)
            continue

        print(f"\n== {sid} == {heading.lstrip('#').strip()}", flush=True)
        log.append(f"== {sid} ==")
        start = len(log)
        for cmd in cmds:
            run(cmd, env, log)
        ran.append(sid)
        section = "\n".join(log[start:])
        for csid, rx in checks:
            if csid == sid and not rx.search(section):
                write_log()
                print(f"\n[!!] {sid}: no match for /{rx.pattern}/ in:\n{section}")
                print(f"FAIL {node} at {sid} (log: {lab / 'work' / 'verify.log'})")
                return 1
        print(f"[ok] {sid}", flush=True)

    write_log()
    for csid, rx in checks:
        if csid not in ran and csid not in skipped:
            print(f"[!!] checks.txt step {csid} is not a step in the README")
            return 1
    print(f"\nPASS {node}: ran {' '.join(ran) or '-'}; skipped {' '.join(skipped) or '-'}"
          f" (log: {lab / 'work' / 'verify.log'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
