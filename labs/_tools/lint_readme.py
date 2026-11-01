#!/usr/bin/env python3
"""Lint the lab READMEs and repo hygiene (stdlib only; run by the CI `labs` job).

    python3 labs/_tools/lint_readme.py              # every lab folder under labs/
    python3 labs/_tools/lint_readme.py <node-id>    # one lab (hygiene checks always run)

Per lab (spec Sections 2 and 6.2):
  * front matter: required keys in order, vocabulary, node == folder name, articles/<node>.md exists
  * H1 and the Atlas-node line; H2 sequence exact
  * every Walkthrough/Defend H3 is a command step (Do/Observe/Why, one bash block, one text
    block, "What to notice:") or a reading step (Read/Why); Why links an Atlas node by live URL
  * explainer links: "[explainer N](explainer/index.html#<node>/N)", in range, non-decreasing
  * footer prev/next matches LAB order; the lab is listed in labs/README.md
  * every expected/checks.txt step id exists in the README
  * every node id (front matter and ?node= links) exists in ai_security_research_graph_seed.json
  * every explainer `cmd:` string appears verbatim in a README Do block
  * optional `covers:` (nodes practiced in this lab): each node is in the seed, is not a lab's
    own node and is covered by no other lab; its steps exist; its anchor is the GitHub anchor
    of the heading of its first step
Repo hygiene: no file under labs/ that git tracks (or would add) is a pickle/torch archive.
Exits 0 when clean, 1 with one line per problem otherwise.
"""

import json
import re
import unicodedata
import subprocess
import sys
import zipfile
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
REPO = LABS.parent
SEED = REPO / "ai_security_research_graph_seed.json"
SITE = "https://ai-security-atlas.github.io/?node="

KEYS = ["lab_id", "title", "node", "related_nodes", "family", "access_profile", "level", "time",
        "compose_profiles", "model_backend", "backends", "hardware", "canary", "last_tested", "tested_on"]
OPTIONAL_KEYS = ["covers"]                 # may follow KEYS, in this order
BACKENDS = ["container-ollama", "host-ollama", "external-api"]
PROFILES = {"ollama", "chat", "workbench", "supply", "rag-agent", "serving", "web"}
H2 = ["Overview", "Safety", "Atlas Context", "Backend Support", "Hardware & Time", "Prerequisites",
      "Explainer", "Setup", "Walkthrough", "Defend", "Evaluate", "Cleanup", "Going Further", "Further Reading"]
FENCE = re.compile(r"^(`{3,})(\S*)\s*$")
CHAPTER = re.compile(r"""chapter\s*:\s*["'](System|Attack|Mechanism|Impact|Defense)["']""")
CMD = re.compile(r"""\bcmd\s*:\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')""")

problems = []


def err(where, msg):
    problems.append(f"{where}: {msg}")


# ---------------------------------------------------------------- front matter
FLOW_PAIR = re.compile(r"""\s*([\w-]+)\s*:\s*("[^"]*"|'[^']*'|[^,]*?)\s*(?:,|$)""")


def scalar(v):
    v = re.sub(r"(^|\s+)#.*$", "", v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if v.startswith("{") and v.endswith("}"):  # flow map: {node: x, steps: "4-7, D1"}
        return {k: scalar(x) for k, x in FLOW_PAIR.findall(v[1:-1]) if k}
    return v


def front_matter(text):
    """Parse the small YAML subset the template uses. Returns (ordered keys, dict, body)."""
    if not text.startswith("---\n"):
        return None, None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, None, text
    keys, data, parent = [], {}, None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and parent:  # block list under a key (covers:)
            if not isinstance(data[parent], list):
                data[parent] = []
            data[parent].append(scalar(item.group(1)))
            continue
        m = re.match(r"^(\s*)([\w-]+):\s*(.*)$", line)
        if not m:
            continue
        indent, k, v = m.groups()
        if indent and parent and isinstance(data[parent], dict):
            data[parent][k] = scalar(v)
        else:
            keys.append(k)
            v = re.sub(r"(^|\s+)#.*$", "", v).strip()
            if v == "":
                parent, data[k] = k, {}
            else:
                parent, data[k] = None, scalar(v)
    return keys, data, text[end + 5:]


def check_front_matter(where, folder, keys, fm, seed_ids):
    if keys is None:
        return err(where, "missing YAML front matter")
    if keys[:len(KEYS)] != KEYS or any(k not in OPTIONAL_KEYS for k in keys[len(KEYS):]):
        err(where, f"front matter keys must be, in order: {', '.join(KEYS)}, then optionally "
                   f"{', '.join(OPTIONAL_KEYS)} (got {', '.join(keys)})")
    if not re.fullmatch(r"LAB-\d{2}", str(fm.get("lab_id", ""))):
        err(where, "lab_id must look like LAB-NN")
    if fm.get("node") != folder:
        err(where, f"node {fm.get('node')!r} must equal the folder name {folder!r}")
    if not (REPO / "articles" / f"{fm.get('node')}.md").exists():
        err(where, f"articles/{fm.get('node')}.md does not exist")
    if fm.get("level") not in ("beginner", "intermediate", "advanced"):
        err(where, "level must be beginner | intermediate | advanced")
    if not re.fullmatch(r"\d+ min", str(fm.get("time", ""))):
        err(where, 'time must look like "60 min"')
    cp = fm.get("compose_profiles")
    if not isinstance(cp, list) or not cp or not set(cp) <= PROFILES:
        err(where, f"compose_profiles must be a non-empty list from {sorted(PROFILES)}")
    mb = fm.get("model_backend")
    if mb not in ("none", "optional", "required"):
        err(where, "model_backend must be none | optional | required")
    be = fm.get("backends")
    if not isinstance(be, dict) or list(be) != BACKENDS:
        err(where, f"backends must list exactly, in order: {', '.join(BACKENDS)}")
    else:
        for name, v in be.items():
            if v not in ("yes", "partial", "no", "n/a"):
                err(where, f"backends.{name} must be yes | partial | no | n/a")
            elif (v == "n/a") != (mb == "none"):
                err(where, f"backends.{name}: n/a is used only and always when model_backend is none")
    if not fm.get("canary"):
        err(where, "canary is required")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fm.get("last_tested", ""))):
        err(where, "last_tested must be YYYY-MM-DD")
    if not fm.get("tested_on") or not fm.get("hardware") or not fm.get("title"):
        err(where, "title, hardware and tested_on are required")
    ids = [fm.get("node"), fm.get("family")] + list(fm.get("related_nodes") or [])
    for nid in ids:
        if nid not in seed_ids:
            err(where, f"front matter node id {nid!r} is not in the seed graph")


# ---------------------------------------------------------------- body structure
def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def outline(body):
    """Return [(level, title, lines_until_next_heading)] ignoring headings inside fences."""
    out, cur, fence = [], None, None
    for line in body.splitlines():
        m = FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1).startswith(fence) and not m.group(2):
                fence = None
            if cur:
                cur[2].append(line)
            continue
        hm = re.match(r"^(#{1,3}) (.*)$", line) if fence is None else None
        if hm:
            cur = (len(hm.group(1)), hm.group(2).strip(), [])
            out.append(cur)
        elif cur:
            cur[2].append(line)
    return out


def blocks(lines, lang):
    """Fenced blocks of a language: list of (start_index, content_lines)."""
    found, i = [], 0
    while i < len(lines):
        if re.match(rf"^```{lang}\s*$", lines[i]):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            found.append((i, lines[i + 1:j]))
            i = j
        i += 1
    return found


def labels(lines):
    """Order of **Do**/**Observe**/**Why**/**Read** labels outside fences."""
    out, fence = [], False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fence = not fence
            continue
        m = re.match(r"^\*\*(Do|Observe|Why|Read)\*\*", line.strip())
        if m and not fence:
            out.append((m.group(1), i))
    return out


def check_step(where, title, lines):
    labs_ = labels(lines)
    names = [n for n, _ in labs_]
    if names == ["Do", "Observe", "Why"]:
        do_i, obs_i, why_i = (i for _, i in labs_)
        b = blocks(lines[do_i:obs_i], "bash")
        if len(b) != 1:
            err(where, f"'{title}': Do must hold exactly one bash block (found {len(b)})")
        t = blocks(lines[obs_i:why_i], "text")
        if len(t) != 1:
            err(where, f"'{title}': Observe must hold exactly one text block (found {len(t)})")
        if "What to notice:" not in "\n".join(lines[obs_i:why_i]):
            err(where, f"'{title}': Observe needs a 'What to notice:' sentence")
        why = "\n".join(lines[why_i:])
    elif names == ["Read", "Why"]:
        read_i, why_i = (i for _, i in labs_)
        if blocks(lines[read_i:why_i], r"\S*"):
            err(where, f"'{title}': a Read step is prose only (no code block)")
        why = "\n".join(lines[why_i:])
    else:
        return err(where, f"'{title}': must be Do/Observe/Why or Read/Why (found {'/'.join(names) or 'no labels'})")
    if SITE not in why:
        err(where, f"'{title}': Why must link an Atlas node ({SITE}<id>)")


def explainer_steps(lab):
    js = lab / "explainer" / "explainer.js"
    if not js.exists():
        return None, []
    src = js.read_text(encoding="utf-8")
    cmds = []
    for lit in CMD.findall(src):
        if lit.startswith('"'):
            cmds.append(json.loads(lit))
        else:
            cmds.append(json.loads('"' + lit[1:-1].replace('\\\'', "'").replace('"', '\\"') + '"'))
    return len(CHAPTER.findall(src)), cmds


# ---------------------------------------------------------------- covers
STEP_TOKEN = re.compile(r"(D?)(\d+)(?:-(D?)(\d+))?|Evaluate")


def github_anchor(heading):
    """The id GitHub gives a README heading: rendered text, lowercased, punctuation dropped,
    spaces -> hyphens (links keep their text; the em dash and middle dot vanish)."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).replace("`", "").replace("**", "")
    keep = (c for c in text.lower()
            if c in " -_" or unicodedata.category(c)[0] in "LMN")
    return "".join(keep).replace(" ", "-")


def parse_steps(spec):
    """'4-7, D1, Evaluate' -> ['S4', 'S5', 'S6', 'S7', 'D1', 'EVAL']; None if malformed."""
    out = []
    for tok in (t.strip() for t in str(spec).split(",")):
        m = STEP_TOKEN.fullmatch(tok)
        if not m:
            return None
        if tok == "Evaluate":
            out.append("EVAL")
            continue
        d1, a, d2, b = m.groups()
        if b is not None and (d1 != d2 or int(b) <= int(a)):
            return None
        pre = "D" if d1 else "S"
        out += [f"{pre}{i}" for i in range(int(a), int(b or a) + 1)]
    return out


def check_covers(where, fm, seed_ids, own_nodes, heading_of):
    covers = fm.get("covers")
    if covers is None:
        return
    if not isinstance(covers, list) or not covers:
        return err(where, "covers must be a block list of '- {node: <id>, steps: \"<ids>\", anchor: <anchor>}'")
    seen = set()
    for c in covers:
        if not isinstance(c, dict) or sorted(c) != ["anchor", "node", "steps"]:
            err(where, f"covers entry {c!r} must have exactly node, steps, anchor")
            continue
        nid = c["node"]
        if nid not in seed_ids:
            err(where, f"covers: node {nid!r} is not in the seed graph")
        if nid in own_nodes:
            err(where, f"covers: {nid!r} has its own lab (labs/{nid}/); link it instead of covering it")
        if nid in seen:
            err(where, f"covers: {nid!r} is listed twice")
        seen.add(nid)
        ids = parse_steps(c["steps"])
        if not ids:
            err(where, f"covers {nid}: steps {c['steps']!r} must look like \"4\", \"4-6\", \"D1\", \"4-7, D1\" or \"Evaluate\"")
            continue
        missing = [i for i in ids if i not in heading_of]
        if missing:
            err(where, f"covers {nid}: step(s) {', '.join(missing)} not in the README")
            continue
        want = github_anchor(heading_of[ids[0]])
        if c["anchor"] != want:
            err(where, f"covers {nid}: anchor must be the first step's heading anchor {want!r} (got {c['anchor']!r})")


def lint_lab(lab, order, seed_ids, index_text, own_nodes):
    folder = lab.name
    where = f"labs/{folder}/README.md"
    text = (lab / "README.md").read_text(encoding="utf-8")
    keys, fm, body = front_matter(text)
    check_front_matter(where, folder, keys, fm, seed_ids)
    if fm is None:
        return
    body = strip_comments(body)
    heads = outline(body)

    h1 = [t for lvl, t, _ in heads if lvl == 1]
    if h1 != [f"{fm['lab_id']} · {fm['title']}"]:
        err(where, f"H1 must be exactly '# {fm['lab_id']} · {fm['title']}'")
    if f"> **Atlas node:** [" not in body or f"({SITE}{folder})" not in body:
        err(where, "missing the '> **Atlas node:** [...]' line linking the node")
    h2 = [t for lvl, t, _ in heads if lvl == 2]
    if h2 != H2:
        err(where, f"H2 sequence must be: {' | '.join(H2)} (got {' | '.join(h2)})")

    # Steps
    n_steps, cmds = explainer_steps(lab)
    if n_steps is None:
        err(where, "explainer/explainer.js is missing")
    last_link, h2_cur, setup = 0, None, []
    step_ids, do_text, heading_of = set(), [], {"EVAL": "Evaluate"}
    for lvl, title, lines in heads:
        if lvl == 2:
            h2_cur = title
            if title in ("Evaluate", "Cleanup"):
                step_ids.add("EVAL" if title == "Evaluate" else "CLEANUP")
                do_text += [l for _, b in blocks(lines, "bash") for l in b]
            continue
        if lvl != 3:
            continue
        do_text += [l for _, b in blocks(lines, "bash") for l in b]
        if h2_cur == "Setup":
            m = re.match(r"Setup (\d) — ", title)
            if m:
                setup.append(int(m.group(1)))
                step_ids.add(f"SETUP{m.group(1)}")
            else:
                err(where, f"Setup H3 must be 'Setup N — <title>' (got '{title}')")
            continue
        if h2_cur not in ("Walkthrough", "Defend"):
            err(where, f"unexpected H3 '{title}' under '{h2_cur}'")
            continue
        prefix = "D" if h2_cur == "Defend" else ""
        m = re.match(rf"Step ({prefix}\d+) — \S", title)
        if not m:
            err(where, f"H3 under {h2_cur} must be 'Step {prefix}N — <title>' (got '{title}')")
            continue
        step_ids.add(m.group(1) if prefix else f"S{m.group(1)}")
        heading_of[m.group(1) if prefix else f"S{m.group(1)}"] = title
        check_step(where, title, lines)
        links = re.findall(r"\[explainer (\d+)\]\(explainer/index\.html#([\w-]+)/(\d+)\)", title)
        if "explainer" in title.lower() and not links:
            err(where, f"'{title}': explainer link must be [explainer N](explainer/index.html#{folder}/N)")
        for label, nid, n in links:
            if label != n or nid != folder:
                err(where, f"'{title}': explainer link label/anchor mismatch")
            n = int(n)
            if n_steps is not None and not 1 <= n <= n_steps:
                err(where, f"'{title}': explainer {n} out of range 1..{n_steps}")
            if n < last_link:
                err(where, f"'{title}': explainer links must be non-decreasing ({n} after {last_link})")
            last_link = max(last_link, n)
    if setup != [1, 2, 3]:
        err(where, "Setup must have exactly 'Setup 1 —', 'Setup 2 —', 'Setup 3 —'")
    check_covers(where, fm, seed_ids, own_nodes, heading_of)

    # checks.txt ids exist
    checks = lab / "expected" / "checks.txt"
    if checks.exists():
        for n, line in enumerate(checks.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip() and not line.startswith("#"):
                sid = line.split("\t", 1)[0].strip()
                if "\t" not in line:
                    err(f"labs/{folder}/expected/checks.txt:{n}", "expected 'step-id<TAB>regex'")
                elif sid not in step_ids:
                    err(f"labs/{folder}/expected/checks.txt:{n}", f"step id {sid} is not in the README")

    # node ids in links exist
    for nid in sorted(set(re.findall(r"\?node=([\w-]+)", body))):
        if nid not in seed_ids:
            err(where, f"link to unknown Atlas node {nid!r}")

    # explainer cmd strings appear verbatim in a Do block
    joined = "\n".join(do_text)
    for c in cmds:
        if c not in joined:
            err(f"labs/{folder}/explainer/explainer.js", f"cmd not found verbatim in a README Do block: {c!r}")

    # footer prev/next
    i = order.index(folder)
    prev, nxt = (order[i - 1] if i else None), (order[i + 1] if i + 1 < len(order) else None)
    footer = [l for l in body.strip().splitlines() if l.strip()][-1]
    if "[All labs](../README.md)" not in footer:
        err(where, "footer must link [All labs](../README.md)")
    got_prev = re.search(r"\[←[^\]]*\]\(\.\./([\w-]+)/README\.md\)", footer)
    got_next = re.search(r"\[[^\]]*→\]\(\.\./([\w-]+)/README\.md\)", footer)
    if (got_prev and got_prev.group(1)) != prev:
        err(where, f"footer prev must be {prev or 'absent'} (got {got_prev and got_prev.group(1)})")
    if (got_next and got_next.group(1)) != nxt:
        err(where, f"footer next must be {nxt or 'absent'} (got {got_next and got_next.group(1)})")

    if f"({folder}/README.md)" not in index_text and f"(./{folder}/README.md)" not in index_text:
        err("labs/README.md", f"{fm['lab_id']} {folder} is not linked from the index")


# ---------------------------------------------------------------- hygiene
def is_pickle_or_torch(path):
    try:
        with open(path, "rb") as f:
            head = f.read(2)
        if len(head) == 2 and head[0] == 0x80 and 2 <= head[1] <= 5:
            return "pickle protocol header"
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                if any(n == "data.pkl" or n.endswith("/data.pkl") for n in z.namelist()):
                    return "torch ZIP archive (data.pkl)"
    except OSError:
        pass
    return None


def check_hygiene():
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "labs"],
                             cwd=REPO, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        return err("labs/", f"cannot list files with git ({e})")
    for rel in filter(None, out.decode().split("\0")):
        kind = is_pickle_or_torch(REPO / rel)
        if kind:
            err(rel, f"tracked/untracked-but-not-ignored {kind}; generated artifacts must never be committed")


def main():
    seed_ids = {n["id"] for n in json.loads(SEED.read_text(encoding="utf-8"))["nodes"]}
    labs = sorted(p.parent for p in LABS.glob("*/README.md") if not p.parent.name.startswith("_"))
    lab_ids, covered_by = {}, {}
    for lab in labs:
        _, fm, _ = front_matter((lab / "README.md").read_text(encoding="utf-8"))
        lab_ids[lab.name] = (fm or {}).get("lab_id", "LAB-99")
        for c in (fm or {}).get("covers") or []:
            if isinstance(c, dict) and c.get("node"):
                covered_by.setdefault(c["node"], []).append(lab.name)
    for nid, hosts in sorted(covered_by.items()):
        if len(set(hosts)) > 1:
            err("labs/", f"node {nid!r} is covered by more than one lab: {', '.join(sorted(set(hosts)))}")
    order = sorted(lab_ids, key=lambda k: lab_ids[k])
    dup = {v for v in lab_ids.values() if list(lab_ids.values()).count(v) > 1}
    for v in dup:
        err("labs/", f"duplicate lab_id {v}")
    wanted = sys.argv[1:] or [p.name for p in labs]
    index = LABS / "README.md"
    index_text = index.read_text(encoding="utf-8") if index.exists() else ""
    for name in wanted:
        if name not in lab_ids:
            err(f"labs/{name}", "no such lab (labs/<node-id>/README.md)")
            continue
        lint_lab(LABS / name, order, seed_ids, index_text, set(lab_ids))
    check_hygiene()

    for p in problems:
        print(f"[!!] {p}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        return 1
    print(f"[ok] {len(wanted)} lab README(s) and repo hygiene: {', '.join(wanted) or 'no labs yet'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
