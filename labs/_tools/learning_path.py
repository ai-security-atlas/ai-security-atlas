#!/usr/bin/env python3
"""Validate labs/learning-path.yaml and keep the lab READMEs in step with it (stdlib only).

    python3 labs/_tools/learning_path.py            # same as --check
    python3 labs/_tools/learning_path.py --check    # exit 1 and list every README that differs
    python3 labs/_tools/learning_path.py --write    # rewrite the generated parts in place

The YAML is the single source for these generated parts:
  * labs/<lab>/README.md: the "> **Learning path:** Module N · step i of m" line after the
    Atlas node line; the "Labs to finish first", "Recommended first" and "Later in the path"
    bullets of Prerequisites (other bullets are left alone); and the footer
    "[← prev in path] · [All labs] · [next in path →]".
  * labs/README.md: everything between the learning-path begin/end markers (one table per
    module and the workshop tracks).
Validation: every lab folder appears exactly once; requires/recommended point only to labs
earlier in the path and `later` only to labs after it (so the graph has no cycles); each
level matches the README front matter. --write is idempotent.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
PATH_FILE = LABS / "learning-path.yaml"
INDEX = LABS / "README.md"
LEVELS = ("beginner", "intermediate", "advanced")
EDGE_KINDS = ("requires", "recommended", "later")
BEGIN = "<!-- learning-path:begin (generated from learning-path.yaml by _tools/learning_path.py; do not edit by hand) -->"
END = "<!-- learning-path:end -->"
LP_PREFIX = "> **Learning path:**"
PREREQ_PREFIX = {"requires": "- Labs to finish first:", "recommended": "- Recommended first:",
                 "later": "- Later in the path:"}


# ---------------------------------------------------------------- YAML subset
def parse_yaml(text):
    """Block maps and lists, "double-quoted" (JSON escapes) or plain scalars, ints, [] and
    full-line # comments. Anything else is an error, so the file stays readable by PyYAML too."""
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if s and not s.startswith("#"):
            if "\t" in raw[:len(raw) - len(raw.lstrip())]:
                raise ValueError(f"line {n}: indent with spaces, not tabs")
            lines.append([len(raw) - len(raw.lstrip(" ")), s, n])
    pos = 0

    def scalar(v, n):
        if v.startswith('"'):
            try:
                return json.loads(v)
            except ValueError:
                raise ValueError(f"line {n}: bad double-quoted string {v}") from None
        if v == "[]":
            return []
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        if v[0] in "'[]{}&*!|>%@`" or " #" in v or ": " in v:
            raise ValueError(f"line {n}: unsupported YAML value {v!r} (quote it with \"...\")")
        return v

    def node(indent):
        return seq(indent) if lines[pos][1].startswith("- ") else mapping(indent)

    def seq(indent):
        nonlocal pos
        out = []
        while pos < len(lines) and lines[pos][0] == indent and lines[pos][1].startswith("- "):
            rest, n = lines[pos][1][2:].strip(), lines[pos][2]
            if re.match(r"[\w-]+:(\s|$)", rest):  # "- key: v" starts a map one level in
                lines[pos][0], lines[pos][1] = indent + 2, rest
                out.append(mapping(indent + 2))
            else:
                pos += 1
                out.append(scalar(rest, n))
        return out

    def mapping(indent):
        nonlocal pos
        out = {}
        while pos < len(lines) and lines[pos][0] == indent and not lines[pos][1].startswith("- "):
            _, s, n = lines[pos]
            m = re.fullmatch(r"([\w-]+):(?:\s+(.*))?", s)
            if not m:
                raise ValueError(f"line {n}: expected 'key: value'")
            k, v = m.groups()
            if k in out:
                raise ValueError(f"line {n}: duplicate key {k!r}")
            pos += 1
            if v:
                out[k] = scalar(v.strip(), n)
            elif pos < len(lines) and lines[pos][0] > indent:
                out[k] = node(lines[pos][0])
            else:
                out[k] = None
        return out

    if not lines:
        return {}
    result = node(lines[0][0])
    if pos != len(lines):
        raise ValueError(f"line {lines[pos][2]}: unexpected indentation")
    return result


# ---------------------------------------------------------------- lab metadata
def front_matter(text):
    """The few front-matter scalars the path needs: lab_id, title, level, time."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    out = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^(lab_id|title|level|time):\s*(.*?)\s*$", line)
        if m:
            v = re.sub(r"\s+#.*$", "", m.group(2))
            out[m.group(1)] = v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v
    return out


def lab_folders():
    return sorted(p.parent.name for p in LABS.glob("*/README.md") if not p.parent.name.startswith("_") and p.parent.name != "primers")


def github_anchor(heading):
    keep = (c for c in heading.lower() if c in " -_" or unicodedata.category(c)[0] in "LMN")
    return "".join(keep).replace(" ", "-")


def module_heading(m):
    return f"Module {m['id']}: {m['title']}"


# ---------------------------------------------------------------- load + validate
def load():
    """-> (path, problems). path = {modules, tracks, order: [lab], entry: {lab: info}, meta: {lab: fm}}."""
    problems = []
    try:
        data = parse_yaml(PATH_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, [f"labs/learning-path.yaml: {e}"]
    where = "labs/learning-path.yaml"
    folders = lab_folders()
    meta = {f: front_matter((LABS / f / "README.md").read_text(encoding="utf-8")) for f in folders}
    modules, order, entry = data.get("modules") or [], [], {}
    for mi, m in enumerate(modules):
        if m.get("id") != mi or not m.get("title") or not m.get("goal") or not m.get("time"):
            problems.append(f"{where}: module #{mi} needs id: {mi}, title, time and goal")
        labs = m.get("labs") or []
        for si, e in enumerate(labs, 1):
            lab = e.get("lab")
            extra = set(e) - {"lab", "level", *EDGE_KINDS}
            if extra:
                problems.append(f"{where}: {lab}: unknown key(s) {', '.join(sorted(extra))}")
            if lab not in meta:
                problems.append(f"{where}: module {mi}: {lab!r} is not a lab folder (labs/<id>/README.md)")
                continue
            if lab in entry:
                problems.append(f"{where}: {lab} is listed twice (modules {entry[lab]['module']['id']} and {mi})")
                continue
            entry[lab] = {"module": m, "step": si, "steps": len(labs), "index": len(order)}
            order.append(lab)
    for f in folders:
        if f not in entry:
            problems.append(f"{where}: lab {f} is not in any module")
    for lab, info in entry.items():
        e = next(x for x in info["module"]["labs"] if x["lab"] == lab)
        fm_level = meta[lab].get("level")
        if e.get("level") not in LEVELS:
            problems.append(f"{where}: {lab}: level must be one of {' | '.join(LEVELS)}")
        elif e["level"] != fm_level:
            problems.append(f"{where}: {lab}: level {e['level']} differs from the README front matter ({fm_level})")
        seen = set()
        for kind in EDGE_KINDS:
            edges = e.get(kind) or []
            if not isinstance(edges, list):
                problems.append(f"{where}: {lab}: {kind} must be a list")
                continue
            info[kind] = []
            for x in edges:
                if not isinstance(x, dict) or set(x) != {"lab", "why"} or not x.get("why"):
                    problems.append(f"{where}: {lab}: each {kind} item needs exactly lab and why")
                    continue
                t = x["lab"]
                if t not in entry:
                    problems.append(f"{where}: {lab}: {kind} {t!r} is not a lab in the path")
                    continue
                if t in seen or t == lab:
                    problems.append(f"{where}: {lab}: {t} is listed twice (or is the lab itself)")
                    continue
                seen.add(t)
                if x["why"].rstrip().endswith("."):
                    problems.append(f"{where}: {lab}: {kind} {t}: why must not end with a period")
                earlier = entry[t]["index"] < info["index"]
                if kind == "later" and earlier:
                    problems.append(f"{where}: {lab}: later {t} comes before it in the path")
                elif kind != "later" and not earlier:
                    problems.append(f"{where}: {lab}: {kind} {t} comes after it in the path (forward edge)")
                info[kind].append(x)
    tracks = data.get("tracks") or []
    for t in tracks:
        for b in t.get("blocks") or []:
            if not b.get("time") or bool(b.get("lab")) == bool(b.get("block")):
                problems.append(f"{where}: track {t.get('id')}: each block needs time and exactly one of lab, block")
            elif b.get("lab") and b["lab"] not in entry:
                problems.append(f"{where}: track {t.get('id')}: {b['lab']!r} is not a lab in the path")
    return {"modules": modules, "tracks": tracks, "order": order, "entry": entry, "meta": meta}, problems


# ---------------------------------------------------------------- rendering
def lab_link(path, lab, prefix="../", rel="/README.md"):
    fm = path["meta"][lab]
    return f"[{fm.get('lab_id')} · {fm.get('title')}]({prefix}{lab}{rel})"


def prereq_lines(path, lab):
    info, out = path["entry"][lab], []
    for kind in EDGE_KINDS:
        items = [f"{lab_link(path, x['lab'])} ({x['why']})" for x in info.get(kind, [])]
        if items or kind == "requires":
            out.append(f"{PREREQ_PREFIX[kind]} {'; '.join(items) if items else 'none'}.")
    return out


def path_line(path, lab):
    info = path["entry"][lab]
    m = info["module"]
    return (f"{LP_PREFIX} Module {m['id']} · step {info['step']} of {info['steps']} · "
            f"[{m['title']}](../README.md#{github_anchor(module_heading(m))})")


def footer(path, lab):
    i, order = path["entry"][lab]["index"], path["order"]
    parts = []
    if i > 0:
        parts.append(f"[← prev in path](../{order[i - 1]}/README.md)")
    parts.append("[All labs](../README.md)")
    if i + 1 < len(order):
        parts.append(f"[next in path →](../{order[i + 1]}/README.md)")
    return " · ".join(parts)


def render_readme(path, lab, text):
    """Return the README with its generated parts rewritten (idempotent)."""
    lines = text.split("\n")
    # 1. Learning-path line: its own blockquote right after the Atlas node line.
    atlas = next((i for i, l in enumerate(lines) if l.startswith("> **Atlas node:**")), None)
    if atlas is not None:
        j = atlas + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        new = path_line(path, lab)
        if j < len(lines) and lines[j].startswith(LP_PREFIX):
            lines[j] = new
        else:
            lines[atlas + 1:atlas + 1] = ["", new]
    # 2. Prerequisites: replace the managed bullets (with any indented continuation lines).
    try:
        start = lines.index("## Prerequisites")
    except ValueError:
        start = None
    if start is not None:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        body, at, i = [], None, start + 1
        while i < end:
            if lines[i].startswith(tuple(PREREQ_PREFIX.values())):
                at = len(body) if at is None else at
                i += 1
                while i < end and lines[i].startswith("  "):
                    i += 1
                continue
            body.append(lines[i])
            i += 1
        if at is None:  # after the first bullet ("Start here"), else at the top
            at = next((k + 1 for k, l in enumerate(body) if l.startswith("- ")), 1)
            while at < len(body) and body[at].startswith("  "):
                at += 1
        body[at:at] = prereq_lines(path, lab)
        lines[start + 1:end] = body
    # 3. Footer: the last non-empty line, when it is the nav line.
    k = len(lines) - 1
    while k >= 0 and not lines[k].strip():
        k -= 1
    if k >= 0 and "[All labs](../README.md)" in lines[k]:
        lines[k] = footer(path, lab)
    return "\n".join(lines)


def cell(s):
    return str(s).replace("|", "\\|")


def render_index(path):
    out = [BEGIN, "", "## Learning path", "",
           "Take the labs in this order. Each module builds on the ones before it, and inside a module "
           "the labs build on each other. **Requires** lists the labs to finish first; every lab README "
           "repeats it under Prerequisites, and its prev/next links follow this order. The LAB number is "
           "only the order the labs were built in. Levels: *beginner* needs only appsec, Docker and Python; "
           "*intermediate* uses terms an earlier module teaches; *advanced* combines several modules.", ""]
    for m in path["modules"]:
        out += [f"### {module_heading(m)}", "", f"{m['time'][0].upper()}{m['time'][1:]}. {m['goal']}", ""]
        if not m.get("labs"):
            continue
        out += ["| Order | Lab | Level | Time | Requires |", "| :--- | :--- | :--- | :--- | :--- |"]
        for e in m["labs"]:
            lab = e["lab"]
            if lab not in path["entry"]:
                continue
            info, fm = path["entry"][lab], path["meta"][lab]
            req = ", ".join(f"[{path['meta'][x['lab']].get('lab_id')}]({x['lab']}/README.md)"
                            for x in info.get("requires", [])) or "none"
            out.append(f"| {m['id']}.{info['step']} | {cell(lab_link(path, lab, prefix=''))} | "
                       f"{fm.get('level')} | {fm.get('time')} | {req} |")
        out.append("")
    out += ["## Workshop tracks", "",
            "Two ready-made selections for a facilitator. Both need only the workbench image on the main path.", ""]
    for t in path["tracks"]:
        out += [f"### Track {t['id']}: {t['title']}", "", f"{t['length'][0].upper()}{t['length'][1:]}. {t['constraints']}", "",
                "| Time | Block | Notes |", "| :--- | :--- | :--- |"]
        for b in t.get("blocks") or []:
            what = lab_link(path, b["lab"], prefix="") if b.get("lab") in path["entry"] else b.get("block", "")
            if b.get("scope"):
                what += f" ({b['scope']})"
            out.append(f"| {cell(b['time'])} | {cell(what)} | {cell(b.get('notes', ''))} |")
        out.append("")
        if t.get("variant"):
            out += [t["variant"], ""]
    out.append(END)
    return "\n".join(out)


def render_index_file(path, text):
    new = render_index(path)
    b, e = text.find(BEGIN), text.find(END)
    if b >= 0 and e > b:
        return text[:b] + new + text[e + len(END):]
    m = re.search(r"^## All labs by build number", text, re.M)
    if not m:
        return None
    return text[:m.start()] + new + "\n\n" + text[m.start():]


# ---------------------------------------------------------------- check / write
def outputs(path, names=None):
    """[(file, current text, wanted text or None)] for the given labs (default: all) and the index."""
    res = []
    for lab in names or path["order"]:
        if lab in path["entry"]:
            p = LABS / lab / "README.md"
            cur = p.read_text(encoding="utf-8")
            res.append((p, cur, render_readme(path, lab, cur)))
    if INDEX.exists():
        cur = INDEX.read_text(encoding="utf-8")
        res.append((INDEX, cur, render_index_file(path, cur)))
    return res


def check(names=None):
    """Problems as 'file: message' strings; used by lint_readme.py."""
    path, problems = load()
    if path is None:
        return problems
    for p, cur, want in outputs(path, names):
        rel = p.relative_to(LABS.parent)
        if want is None:
            problems.append(f"{rel}: no learning-path markers and no '## All labs by build number' heading")
        elif cur != want:
            what = "the learning-path section" if p == INDEX else \
                "the Learning path line, the generated Prerequisites lines or the footer"
            problems.append(f"{rel}: {what} differ from learning-path.yaml "
                            "(run python3 labs/_tools/learning_path.py --write)")
    return problems


def main(argv):
    mode = "--write" if "--write" in argv else "--check"
    if mode == "--check":
        problems = check()
        for p in problems:
            print(f"[!!] {p}")
        if problems:
            print(f"FAIL: {len(problems)} problem(s)")
            return 1
        path, _ = load()
        print(f"[ok] learning path: {len(path['modules'])} modules, {len(path['order'])} labs, READMEs in step")
        return 0
    path, problems = load()
    if problems:
        for p in problems:
            print(f"[!!] {p}")
        print("FAIL: fix learning-path.yaml first; nothing written")
        return 1
    changed = 0
    for p, cur, want in outputs(path):
        if want is not None and want != cur:
            p.write_text(want, encoding="utf-8")
            changed += 1
            print(f"[wrote] {p.relative_to(LABS.parent)}")
    print(f"[ok] {changed} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
