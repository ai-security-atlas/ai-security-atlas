"""Compile the AI Security Research Graph seed into deployable artifacts.

Input:  ai_security_research_graph_seed.json  (canonical transport snapshot)
Output:
  static/data/atlas.json   -> served at /data/atlas.json, consumed by the React SPA
  data/atlas.json          -> Hugo data (.Site.Data.atlas) for no-JS templates
  content/nodes/<id>.md    -> /nodes/<id>/: the Explorer for that node, article server-rendered
                              (thin front matter; templates read atlas)
  content/nodetabs/        -> /nodes/<id>/{labs,evidence,relationships}/: the same, on that reader tab
  content/sources/<id>.md
  content/views/<id>.md
  content/_index.md, content/graph/_index.md
  content/labs/_index.md   -> /labs/ index page (layouts/lab/list.html)
  content/labs/<id>.md     -> /labs/<id>/: explainer + lab guide (README body) (layouts/lab/single.html)
  content/labs/tags/       -> /labs/tags/ and /labs/tags/<tag>/ from explainer legend tags (layouts/labtag/)
  static/labs/             -> explainer engine + lab explainers under /labs/ (copied from labs/);
                              /labs/<id>/explainer/ is a redirect to /labs/<id>/

Lab metadata comes from the YAML front matter of labs/<node-id>/README.md
(docs/labs-spec.md section 2.1) and is attached to the matching node as `lab`.
A lab's optional `covers:` list attaches `practiced_in` to each covered node, and
hub nodes (goals, families, and the roadmap's umbrella hubs) get `labs_in_area`.

The compiler denormalizes the graph once so every reader (SPA or template) can
show forward AND inverse relationships without re-scanning 650 edges. See the
PRD sections 4.4 (edge direction), 7.4 (curated sidebar), 7.5 (graph behavior).
"""

import glob
import json
import os
import posixpath
import re
import shutil
import subprocess
from collections import Counter

import yaml

SEED = "ai_security_research_graph_seed.json"
REPO_URL = "https://github.com/ai-security-atlas/ai-security-atlas"
SITE_URL = "https://ai-security-atlas.github.io/"  # READMEs link nodes here; on-site they become root-relative
LABS_DIR = "labs"
LABS_OUT = "static/labs"
NODE_TABS = ("labs", "evidence", "relationships")  # Explorer reader tabs with their own URL; overview is /nodes/<id>/
ROADMAP = os.path.join("docs", "labs-roadmap.json")  # optional: umbrella hubs + their members
TAGS_VOCAB = os.path.join(LABS_DIR, "_explainer", "tags.json")  # {"<tag>": {"name", "description"}}

# --- Presentation metadata for the 11 P0 topic types -------------------------
# glyph = lucide-react icon name used by the SPA; color reads on both the warm
# paper (#f1f0eb) and near-black (#0a0b0b) surfaces.
TYPE_META = {
    "goal":             {"label": "Objective",   "plural": "Objectives",   "glyph": "Target",        "color": "#0b6e43", "order": 0},
    "technique_family": {"label": "Family",       "plural": "Families",     "glyph": "Layers",        "color": "#b45309", "order": 1},
    "attack":           {"label": "Attack",       "plural": "Attacks",      "glyph": "Crosshair",     "color": "#e11d48", "order": 2},
    "method":           {"label": "Method",       "plural": "Methods",      "glyph": "FlaskConical",  "color": "#7c3aed", "order": 3},
    "defense":          {"label": "Defense",      "plural": "Defenses",     "glyph": "ShieldCheck",   "color": "#0891b2", "order": 4},
    "evaluation":       {"label": "Evaluation",   "plural": "Evaluations",  "glyph": "Gauge",         "color": "#4f46e5", "order": 5},
    "concept":          {"label": "Concept",      "plural": "Concepts",     "glyph": "Lightbulb",     "color": "#059669", "order": 6},
    "architecture":     {"label": "Architecture", "plural": "Architectures","glyph": "Cpu",           "color": "#2563eb", "order": 7},
    "component":        {"label": "Component",    "plural": "Components",   "glyph": "Boxes",         "color": "#64748b", "order": 8},
    "lifecycle":        {"label": "Lifecycle",    "plural": "Lifecycle",    "glyph": "GitBranch",     "color": "#ea580c", "order": 9},
    "format":           {"label": "Format",       "plural": "Formats",      "glyph": "Binary",        "color": "#6b7280", "order": 10},
}

# --- Edge type -> (source-group key, target-group key) and human labels -------
# Labels follow the seed's relation_types inverse semantics (PRD 4.4).
EDGE_GROUPS = {
    "requires_concept": ("requires",    "requiredBy"),
    "member_of":        ("memberOf",    "hasMember"),
    "can_serve_goal":   ("routesToGoal","reachableVia"),
    "in_scope_of":      ("inScopeOf",   "hasRelevantTopic"),
    "uses":             ("uses",        "usedBy"),
    "variant_of":       ("variantOf",   "hasVariant"),
    "can_enable":       ("canEnable",   "mayBeEnabledBy"),
    "distinct_from":    ("distinctFrom","distinctFrom"),  # symmetric
    "can_mitigate":     ("canMitigate", "mitigatedBy"),
    "evaluated_by":     ("evaluatedBy", "evaluates"),
}

# Human-facing headings for each relationship group, keyed by group id.
REL_LABELS = {
    "requires":         "Prerequisites",
    "requiredBy":       "Prerequisite for",
    "memberOf":         "Family",
    "hasMember":        "Techniques in this family",
    "routesToGoal":     "Routes to objective",
    "reachableVia":     "Techniques that route here",
    "inScopeOf":        "Relevant to",
    "hasRelevantTopic": "Relevant techniques & topics",
    "uses":             "Uses",
    "usedBy":           "Used by",
    "variantOf":        "Variant of",
    "hasVariant":       "Variants",
    "canEnable":        "Can enable",
    "mayBeEnabledBy":   "May be enabled by",
    "distinctFrom":     "Distinct from",
    "canMitigate":      "Mitigates",
    "mitigatedBy":      "Candidate mitigations",
    "evaluatedBy":      "Evaluated by",
    "evaluates":        "Evaluates",
}

# Overview objective ordering (PRD 4.1: nine system goals + the misuse lens).
GOAL_ORDER = [
    "goal-behavior", "goal-decisions", "goal-information", "goal-model-theft",
    "goal-persistence", "goal-actions", "goal-availability", "goal-environment",
    "goal-evasion", "goal-misuse",
]


def write_md(path, frontmatter, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True))
        f.write("---\n")
        if content:
            f.write(f"\n{content}\n")


# --- Hands-on labs ------------------------------------------------------------
# The front matter is a small, fixed YAML subset (spec 2.1): scalars, quoted
# strings, inline [a, b] lists, one level of nesting (backends) and a block
# list of inline {k: v} maps (covers). Parsed with
# the standard library because the site image ships only lab READMEs and
# explainers (see .dockerignore), not labs/_tools.
_FLOW_PAIR = re.compile(r"""\s*([\w-]+)\s*:\s*("[^"]*"|'[^']*'|[^,]*?)\s*(?:,|$)""")


def _fm_value(v):
    v = re.sub(r"(^|\s+)#.*$", "", v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [_fm_value(x) for x in v[1:-1].split(",") if x.strip()]
    if v.startswith("{") and v.endswith("}"):
        return {k: _fm_value(x) for k, x in _FLOW_PAIR.findall(v[1:-1]) if k}
    return v


def read_front_matter(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    data, parent = {}, None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and parent:
            if not isinstance(data[parent], list):
                data[parent] = []
            data[parent].append(_fm_value(item.group(1)))
            continue
        m = re.match(r"^(\s*)([\w-]+):\s*(.*)$", line)
        if not m:
            continue
        indent, key, val = m.groups()
        if indent and parent and isinstance(data[parent], dict):
            data[parent][key] = _fm_value(val)
        elif _fm_value(val) == "":
            parent, data[key] = key, {}
        else:
            parent, data[key] = None, _fm_value(val)
    return data


def load_labs(node_ids):
    """Read labs/<node-id>/README.md front matter -> {node_id: lab metadata}.
    Folders starting with "_" (template, engine, tools) are not labs."""
    labs = {}
    for readme in sorted(glob.glob(os.path.join(LABS_DIR, "*", "README.md"))):
        folder = os.path.basename(os.path.dirname(readme))
        if folder.startswith("_"):
            continue
        fm = read_front_matter(readme)
        m = re.fullmatch(r"LAB-(\d+)", str((fm or {}).get("lab_id", "")))
        if not fm or not m:
            print(f"warning: {readme}: no front matter with a LAB-NN lab_id; skipped")
            continue
        nid = fm.get("node", "")
        if nid != folder or nid not in node_ids:
            print(f"warning: {readme}: node {nid!r} must equal the folder name and exist in the seed; skipped")
            continue
        has_explainer = os.path.isfile(os.path.join(LABS_DIR, folder, "explainer", "explainer.js"))
        labs[nid] = {
            "lab_id": fm["lab_id"],
            "number": int(m.group(1)),
            "node": nid,
            "title": fm.get("title", nid),
            "family": fm.get("family", ""),
            "level": fm.get("level", ""),
            "time": fm.get("time", ""),
            "model_backend": fm.get("model_backend", ""),
            "backends": fm.get("backends", {}) if isinstance(fm.get("backends"), dict) else {},
            "last_tested": fm.get("last_tested", ""),
            "github": f"{REPO_URL}/tree/main/labs/{folder}",
            "page": f"/labs/{folder}/",
            "explainer": f"/labs/{folder}/" if has_explainer else "",
            "covers": [c for c in (fm.get("covers") or [])
                       if isinstance(c, dict) and c.get("node") in node_ids],
            # Optional `objectives: [goal-...]` overrides the derived goals; main() validates and replaces it.
            "objectives": fm.get("objectives"),
        }
    return labs


def practiced_in(labs):
    """{covered node id: {lab_id, number, node (host), title, steps, url}} from `covers:`.
    lint_readme.py rejects a node covered twice or a lab's own node; skip them here too."""
    out = {}
    for lab in sorted(labs.values(), key=lambda l: l["number"]):
        for c in lab["covers"]:
            nid = c["node"]
            if nid in out or nid in labs:
                print(f"warning: labs/{lab['node']}: covers {nid!r} is already a lab or covered; skipped")
                continue
            out[nid] = {
                "lab_id": lab["lab_id"], "number": lab["number"], "node": lab["node"],
                "title": lab["title"], "steps": c.get("steps", ""),
                "url": lab["page"] + (f"#{c['anchor']}" if c.get("anchor") else ""),
            }
    return out


def read_roadmap():
    """docs/labs-roadmap.json -> (umbrella hubs {node id: [member ids]}, number of planned own labs,
    raw entries {node id: entry}). Optional: without the file there are no extra hubs and no planned labs."""
    if not os.path.isfile(ROADMAP):
        return {}, 0, {}
    with open(ROADMAP, "r", encoding="utf-8") as fh:
        raw = json.load(fh).get("raw", {})
    hubs = {nid: e.get("also_covers") or [] for nid, e in raw.items() if e.get("kind") == "hub"}
    return hubs, sum(1 for e in raw.values() if e.get("kind") == "own"), raw


def labs_in_area(members, labs, practiced, placed=()):
    """Existing labs that practice a hub's members, one row per lab:
    {lab_id, number, node, title, level, time, page, own (bool: its own node is a member),
    practiced: [...], relation}. `placed` adds labs whose derived placement names the hub.
    relation: "own" (own node is a member), "practiced" (covers a member), else "foundation"."""
    rows = {}

    def row_for(lab):
        return rows.setdefault(lab["node"], {"lab_id": lab["lab_id"], "number": lab["number"],
                                             "node": lab["node"], "title": lab["title"],
                                             "level": lab["level"], "time": lab["time"], "page": lab["page"],
                                             "own": False, "practiced": []})

    for mid in members:
        if mid in labs:
            row_for(labs[mid])["own"] = True
        elif mid in practiced:
            p = practiced[mid]
            row_for(labs[p["node"]])["practiced"].append({"node": mid, "steps": p["steps"], "url": p["url"]})
    for lid in placed:
        row_for(labs[lid])
    for row in rows.values():
        row["relation"] = "own" if row["own"] else "practiced" if row["practiced"] else "foundation"
    return sorted(rows.values(), key=lambda r: r["number"])


# A published explainer/index.html sends old links (and their #<id>/<step>) to the lab page.
_REDIRECT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<title>{title} · AI Security Atlas</title>
<script>location.replace("{page}" + (location.hash || "#lab-explainer"));</script>
<meta http-equiv="refresh" content="0; url={page}">
</head>
<body data-pagefind-ignore="all"><p>This explainer moved to <a href="{page}">{page}</a>.</p></body>
</html>
"""


def publish_explainers(labs):
    """Copy the shared engine and each lab's explainer into static/labs/ so the
    lab page (/labs/<id>/) can load /labs/_explainer/ and /labs/<id>/explainer/.
    The published explainer/index.html is replaced by a redirect to the lab page;
    the source index.html stays standalone for file:// use."""
    shutil.rmtree(LABS_OUT, ignore_errors=True)
    with_explainer = [lab for lab in labs.values() if lab["explainer"]]
    if not with_explainer:
        return 0
    shutil.copytree(os.path.join(LABS_DIR, "_explainer"), os.path.join(LABS_OUT, "_explainer"),
                    ignore=shutil.ignore_patterns("test", "README.md", "tags.json"))
    for lab in with_explainer:
        out = os.path.join(LABS_OUT, lab["node"], "explainer")
        shutil.copytree(os.path.join(LABS_DIR, lab["node"], "explainer"), out)
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(_REDIRECT.format(title=lab["title"].replace("<", "&lt;"), page=lab["page"]))
    return len(with_explainer)


# Explainer legends are JavaScript (Explainer.define({... legend ...})), so node evaluates each
# lab's data.js + explainer.js against the real engine with a stub DOM and prints the legends.
_LEGEND_JS = r"""
const fs = require("fs"), path = require("path"), noop = () => {};
global.window = global;
global.document = { readyState: "complete", addEventListener: noop, querySelectorAll: () => [] };
global.addEventListener = noop;
function run(file, who) {
  try { new Function(fs.readFileSync(file, "utf8"))(); }
  catch (e) { console.error(`${who}: ${file}: ${(e && e.stack) || e}`); process.exit(1); }
}
run("labs/_explainer/explainer.js", "explainer engine");
const out = {};
for (const id of process.argv.slice(1)) {
  const dir = path.join("labs", id, "explainer");
  if (fs.existsSync(path.join(dir, "data.js"))) run(path.join(dir, "data.js"), `lab ${id}`);
  run(path.join(dir, "explainer.js"), `lab ${id}`);
  const d = Explainer.defs[id];
  if (!d) { console.error(`lab ${id}: ${dir}/explainer.js defines no explainer with id "${id}"`); process.exit(1); }
  out[id] = (d.legend || []).map(r => (typeof r === "string" ? { role: r, label: Explainer.ROLES[r] || r } : r));
}
process.stdout.write(JSON.stringify(out));
"""
_TAG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_RESERVED_TAGS = {"page", "index"}  # /labs/tags/page/ is Hugo's pagination path


def lab_legends(labs):
    """{lab id: [{role, label, tag?}]} for every lab with an explainer. A lab whose
    JavaScript fails, or a tag that is not a kebab-case slug, fails the build."""
    ids = sorted(lab["node"] for lab in labs.values() if lab["explainer"])
    if not ids:
        return {}
    try:
        res = subprocess.run(["node", "-e", _LEGEND_JS, *ids], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("error: node is required to read the lab explainer legends (labs/*/explainer/explainer.js)")
    if res.returncode:
        raise SystemExit(f"error: reading explainer legends failed:\n{res.stderr.strip()}")
    legends = json.loads(res.stdout)
    for lid, legend in legends.items():
        for entry in legend:
            tag = entry.get("tag")
            if tag is not None and not (isinstance(tag, str) and _TAG.fullmatch(tag)):
                raise SystemExit(f"error: labs/{lid}/explainer/explainer.js: legend tag {tag!r} must be a kebab-case slug")
            if tag in _RESERVED_TAGS:
                raise SystemExit(f"error: labs/{lid}/explainer/explainer.js: legend tag {tag!r} is reserved (it would clash with a /labs/tags/ URL)")
    return legends


def lab_tags(labs, legends):
    """[{tag, name, description, labs: [{node, lab_id, title, label, role}]}] sorted by name.
    Names and descriptions come from labs/_explainer/tags.json. A tag missing from it fails the build;
    a vocabulary entry no lab uses gets a warning. Two pills of one lab with the same tag share a row."""
    vocab = {}
    if os.path.isfile(TAGS_VOCAB):
        with open(TAGS_VOCAB, "r", encoding="utf-8") as fh:
            vocab = json.load(fh)
    tags = {}
    for lab in sorted(labs.values(), key=lambda l: l["number"]):
        for entry in legends.get(lab["node"], []):
            if not entry.get("tag"):
                continue
            if entry["tag"] not in vocab:
                raise SystemExit(f"error: labs/{lab['node']}/explainer/explainer.js: legend tag {entry['tag']!r} "
                                 f"is not in {TAGS_VOCAB}; add it there or fix the tag")
            t = tags.setdefault(entry["tag"], {"tag": entry["tag"], "labs": []})
            label = entry.get("label", entry["tag"])
            row = next((r for r in t["labs"] if r["node"] == lab["node"]), None)
            if row:
                row["label"] += f" · {label}"
            else:
                t["labs"].append({"node": lab["node"], "lab_id": lab["lab_id"], "title": lab["title"],
                                  "label": label, "role": entry.get("role", "muted")})
    for slug in sorted(set(vocab) - set(tags)):
        print(f"warning: {TAGS_VOCAB}: tag {slug!r} is not used by any explainer legend")
    for slug, t in tags.items():
        v = vocab[slug]
        t["name"] = v.get("name") or slug.replace("-", " ").title()
        t["description"] = v.get("description", "")
    return sorted(tags.values(), key=lambda t: t["name"].lower())


# --- Lab guide: the README body rendered on /labs/<id>/ ------------------------
# Links are written for the repo (GitHub and a local clone). On the site:
#   explainer/index.html#<id>/N    -> #<id>/N (drives the embedded explainer); another lab's -> /labs/<lab>/#...
#   ../../articles/<node>.md#f     -> /nodes/<node>/#f
#   ../<lab>/README.md#a, ../<lab>/ -> /labs/<lab>/#a ;  ../README.md -> /labs/
#   any other relative path        -> GitHub (blob for files, tree for folders)
#   https://ai-security-atlas.github.io/... -> /... (stays on this deployment)
# Fenced code blocks and inline code are left alone.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_GUIDE_LINK = re.compile(r"(`+)(?:(?!\n\n)[\s\S])*?\1|\]\(([^)\s]+)")


def _guide_href(href, lab_id, labs, node_ids):
    if href.startswith(SITE_URL):
        return "/" + href[len(SITE_URL):]
    if href.startswith(("#", "/")) or re.match(r"[a-zA-Z][\w+.-]*:", href):
        return href
    path, _, frag = href.partition("#")
    frag = f"#{frag}" if frag else ""
    rel = posixpath.normpath(posixpath.join(LABS_DIR, lab_id, path))
    if rel.startswith(".."):
        return href
    m = re.fullmatch(rf"{LABS_DIR}/([^/]+)/explainer/index\.html", rel)
    if m and m.group(1) in labs:
        target = re.fullmatch(r"#([\w-]+)/\d+", frag)  # the #<id>/N names the explainer it drives
        target = target.group(1) if target and target.group(1) in labs else m.group(1)
        if target == lab_id:
            return frag or "#lab-explainer"
        return labs[target]["page"] + (frag or "#lab-explainer")
    m = re.fullmatch(r"articles/([a-z0-9-]+)\.md", rel)
    if m and m.group(1) in node_ids:
        return f"/nodes/{m.group(1)}/{frag}"
    m = re.fullmatch(rf"{LABS_DIR}/([^/]+)(/README\.md)?", rel)
    if m and m.group(1) in labs and (m.group(2) or m.group(1) != lab_id):  # its own folder stays on GitHub
        return f"{labs[m.group(1)]['page']}{frag}"
    if rel == f"{LABS_DIR}/README.md":
        return "/labs/"
    kind = "tree" if path.endswith("/") or os.path.isdir(rel) else "blob"
    return f"{REPO_URL}/{kind}/main/{rel}{frag}"


def lab_guide(lab, labs, node_ids):
    """README.md without its front matter and its H1 (the page header shows the title), links rewritten."""
    with open(os.path.join(LABS_DIR, lab["node"], "README.md"), "r", encoding="utf-8") as fh:
        text = fh.read()
    if text.startswith("---\n"):
        text = text[text.find("\n---\n", 4) + 5:]
    text = re.sub(r"\A\s*# [^\n]*\n", "", text)

    def fix(m):
        if m.group(2) is None:
            return m.group(0)
        return "](" + _guide_href(m.group(2), lab["node"], labs, node_ids)

    out, prose, fence = [], [], None
    for line in text.splitlines(keepends=True):
        m = _FENCE.match(line)
        if fence is None and m:
            out.append(_GUIDE_LINK.sub(fix, "".join(prose)))
            prose, fence = [], m.group(1)
            out.append(line)
        elif fence is not None:
            out.append(line)
            if line.strip().startswith(fence[0] * len(fence)) and not line.strip().strip(fence[0]):
                fence = None
        else:
            prose.append(line)
    out.append(_GUIDE_LINK.sub(fix, "".join(prose)))
    return "".join(out).strip()


def main():
    with open(SEED, "r", encoding="utf-8") as f:
        seed = json.load(f)

    nodes_raw = seed.get("nodes", [])
    edges = seed.get("edges", [])
    sources_raw = seed.get("sources", [])
    access_profiles = seed.get("access_profiles", [])
    top_observations = seed.get("observations", [])
    views = seed.get("views", [])
    framework_mappings = seed.get("framework_mappings", [])

    node_by_id = {n["id"]: n for n in nodes_raw}
    labs = load_labs(set(node_by_id))
    if "tags" in labs:
        raise SystemExit("error: labs/tags: the lab id 'tags' is reserved for /labs/tags/")
    # Read legends and tags before anything is wiped or written, so a failing explainer leaves the tree intact.
    legends = lab_legends(labs)
    tags = lab_tags(labs, legends)
    practiced = practiced_in(labs)
    hubs, labs_planned, roadmap = read_roadmap()
    hubs.update({n["id"]: hubs.get(n["id"], []) for n in nodes_raw
                 if n.get("type") in ("goal", "technique_family")})

    # --- Attach observations -------------------------------------------------
    # Observations live in a top-level table; a node references them either by
    # id (string) inline, or the top-level record carries node_id. Resolve both
    # to full observation dicts on the owning node.
    obs_by_id = {o.get("id"): o for o in top_observations if isinstance(o, dict)}
    obs_by_node = {}
    for obs in top_observations:
        if isinstance(obs, dict) and obs.get("node_id"):
            obs_by_node.setdefault(obs["node_id"], []).append(obs)
    for n in nodes_raw:
        merged = []
        seen = set()
        for o in n.get("observations", []):
            resolved = obs_by_id.get(o) if isinstance(o, str) else o
            if isinstance(resolved, dict) and resolved.get("id") not in seen:
                merged.append(resolved)
                seen.add(resolved.get("id"))
        for o in obs_by_node.get(n["id"], []):
            if o.get("id") not in seen:
                merged.append(o)
                seen.add(o.get("id"))
        n["observations"] = merged

    # --- Framework mappings per node -----------------------------------------
    fw_by_node = {}
    for fm in framework_mappings:
        entry = {
            "framework": fm.get("framework", ""),
            "edition": fm.get("edition", ""),
            "external_id": fm.get("external_id", ""),
            "title": fm.get("title", ""),
            "source_id": fm.get("source_id", ""),
        }
        for nid in fm.get("node_ids", []):
            fw_by_node.setdefault(nid, []).append(entry)

    # --- Build directional relationship groups from typed edges --------------
    rel = {n["id"]: {} for n in nodes_raw}

    def add(nid, key, target):
        if nid not in rel or not target or target == nid:
            return
        bucket = rel[nid].setdefault(key, [])
        if target not in bucket and target in node_by_id:
            bucket.append(target)

    for e in edges:
        s, t, etype = e.get("source"), e.get("target"), e.get("type")
        groups = EDGE_GROUPS.get(etype)
        if not groups:
            continue
        src_key, tgt_key = groups
        add(s, src_key, t)
        add(t, tgt_key, s)

    # Fold compact front-matter fields into rel so nothing is missed even if a
    # structural edge was not materialised in `edges`.
    for n in nodes_raw:
        for pid in n.get("prerequisites", []):
            add(n["id"], "requires", pid)
            add(pid, "requiredBy", n["id"])
        for gid in n.get("goal_ids", []):
            add(n["id"], "routesToGoal", gid)
            add(gid, "reachableVia", n["id"])
        if n.get("family_id"):
            add(n["id"], "memberOf", n["family_id"])
            add(n["family_id"], "hasMember", n["id"])
        for sid in n.get("scope_ids", []):
            add(n["id"], "inScopeOf", sid)
            add(sid, "hasRelevantTopic", n["id"])

    # --- Assemble denormalized node records ----------------------------------
    def title_of(nid):
        return node_by_id.get(nid, {}).get("title", nid)

    def sort_by_title(ids):
        return sorted(ids, key=lambda i: title_of(i).lower())

    # Optional authored prose lives in articles/<id>.md and survives rebuilds
    # (the seed carries no article bodies). Presence promotes seed -> draft.
    import re as _re
    _node_ids = {n["id"] for n in nodes_raw}
    _src_ids = {s["id"] for s in sources_raw}

    def _fix_links(text):
        # Rewrite authored markdown links to deployable URLs. Goldmark does not
        # resolve relative .md links, so normalise every form to /nodes|sources/.
        def repl(m):
            dirp, stem = m.group(1), m.group(2)
            if dirp == "sources/" or (stem in _src_ids and stem not in _node_ids):
                if stem in _src_ids:
                    return f"](/sources/{stem}/)"
            if dirp == "nodes/" or stem in _node_ids:
                if stem in _node_ids:
                    return f"](/nodes/{stem}/)"
                if stem in _src_ids:
                    return f"](/sources/{stem}/)"
            return m.group(0)
        return _re.sub(
            r"\]\((?:\.{0,2}/)*(nodes/|sources/)?([a-z0-9][a-z0-9\-]*)\.md\)",
            repl, text,
        )

    def read_article(nid):
        p = os.path.join("articles", f"{nid}.md")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                return _fix_links(fh.read().strip())
        return ""

    node_articles = {n["id"]: read_article(n["id"]) for n in nodes_raw}

    # --- Primary objective per attack and derived lab placement --------------
    goal_rank = {g: i for i, g in enumerate(GOAL_ORDER)}

    def goal_key(gid):
        return (goal_rank.get(gid, len(GOAL_ORDER)), title_of(gid).lower())

    goals_of = {n["id"]: sorted(rel[n["id"]].get("routesToGoal", []), key=goal_key)
                for n in nodes_raw if n["type"] == "attack"}
    family_of = {aid: (rel[aid].get("memberOf") or [""])[0] for aid in goals_of}
    fam_goal_count = Counter((family_of[a], g) for a, gids in goals_of.items() for g in gids)

    # Primary objective: the seed's optional `primary_goal` (must be one of the
    # attack's goals); otherwise the attack's goal that the most attacks of its
    # family also serve, ties by GOAL_ORDER. The nav lists the attack under that
    # goal; every other goal shows it as an alias row.
    primary_goal = {}
    for aid, gids in goals_of.items():
        authored = node_by_id[aid].get("primary_goal")
        if authored and authored not in gids:
            raise SystemExit(f"error: {aid}: primary_goal {authored!r} is not one of its goals {gids}")
        if gids:
            primary_goal[aid] = authored or min(gids, key=lambda g: (-fam_goal_count[(family_of[aid], g)], goal_key(g)))
        goals_of[aid] = [primary_goal[aid]] + [g for g in gids if g != primary_goal[aid]] if gids else []

    def linked_attacks(nid):
        """Attacks one edge away from a non-attack node: they require, are scoped to or
        use it, it mitigates them (defense) or evaluates them (evaluation)."""
        if nid in goals_of:
            return {nid}
        return {a for k in ("requiredBy", "hasRelevantTopic", "usedBy", "canMitigate", "evaluates")
                for a in rel.get(nid, {}).get(k, []) if a in goals_of}

    def top(counts, key):
        # Up to two ids, each backed by at least half as many attacks as the leader.
        order = sorted(counts, key=lambda i: (-counts[i], key(i)))[:2]
        return [i for i in order if counts[i] * 2 >= counts[order[0]]]

    def place(nid, covers, prefer="", goals=None):
        """(goals, families) a lab on `nid` belongs to. An attack lab: its goals (primary
        first) and its family. Otherwise the attacks linked to the node or to any covered
        node vote. Families: top() (ties by title), with `prefer` (the README `family`) first
        when it has a vote. Goals: top() over the attacks of those families, ties by how many
        of them have the goal as primary, then GOAL_ORDER. `goals` (README `objectives:`)
        replaces the derived goals; families then keep only those serving one of them,
        `prefer` included. No linked attack -> ([], []): a foundations lab."""
        if nid in goals_of:
            return (goals_of[nid] if goals is None else goals), [family_of[nid]] if family_of[nid] else []
        attacks = set(linked_attacks(nid))
        for c in covers:
            attacks |= linked_attacks(c)
        fam_votes = Counter(family_of[a] for a in attacks if family_of[a])
        families = top(fam_votes, lambda f: title_of(f).lower())
        if prefer in fam_votes:
            families = [prefer] + [f for f in families if f != prefer][:1]
        if goals is not None:
            return goals, [f for f in dict.fromkeys(families + [prefer])
                           if f and any(fam_goal_count[(f, g)] for g in goals)][:2]
        backing = [a for a in attacks if family_of[a] in families]
        primaries = Counter(primary_goal[a] for a in backing)
        return (top(Counter(g for a in backing for g in goals_of[a]), lambda g: (-primaries[g], goal_key(g))),
                families)

    goal_ids = {n["id"] for n in nodes_raw if n["type"] == "goal"}
    family_mismatch = []
    for lab in labs.values():
        obj = lab["objectives"]
        if obj is not None:
            if not isinstance(obj, list) or not all(isinstance(g, str) for g in obj) or len(set(obj)) != len(obj):
                raise SystemExit(f"error: labs/{lab['node']}/README.md: objectives must be a list of distinct goal ids")
            bad = [g for g in obj if g not in goal_ids]
            if bad:
                raise SystemExit(f"error: labs/{lab['node']}/README.md: objectives {bad} are not goal ids")
        lab["objectives"], lab["families"] = place(lab["node"], [c["node"] for c in lab["covers"]],
                                                   lab["family"], obj)
        families = lab["families"]
        graph_family = families[0] if families else lab["family"]
        if lab["family"] != graph_family:
            family_mismatch.append(lab["lab_id"])
            lab["family"] = graph_family
    if family_mismatch:
        print(f"warning: {len(family_mismatch)} lab(s) front matter `family` differs from the graph; "
              f"using the graph's: {', '.join(sorted(family_mismatch))}")

    # Planned labs (docs/labs-roadmap.json `kind: own` with no lab folder yet), placed
    # by the same rule with the roadmap's `also_covers` standing in for `covers:`.
    planned = {}
    for nid, e in roadmap.items():
        if e.get("kind") == "own" and nid in node_by_id and nid not in labs:
            covers = [c.split()[0] for c in e.get("also_covers") or [] if c.split() and c.split()[0] in node_by_id]
            goals, families = place(nid, covers)
            planned[nid] = {"node": nid, "title": e.get("title") or title_of(nid), "effort": e.get("effort") or "",
                            "model_backend": e.get("model_backend") or "", "status": "planned",
                            "objectives": goals, "families": families, "covers": covers}

    atlas_nodes = {}
    for n in nodes_raw:
        nid = n["id"]
        groups = {k: sort_by_title(v) for k, v in rel[nid].items() if v}
        has_article = bool(node_articles.get(nid))
        atlas_nodes[nid] = {
            "id": nid,
            "title": n.get("title", nid),
            "type": n.get("type", "concept"),
            "summary": n.get("summary", ""),
            "aliases": n.get("aliases", []),
            "caveat": n.get("caveat", "") or "",
            "priority": n.get("priority", ""),
            "content_status": "draft" if has_article else n.get("content_status", ""),
            "evidence_status": n.get("evidence_status", ""),
            "last_reviewed": n.get("last_reviewed", ""),
            "references": n.get("references", []),
            "access_profile_ids": n.get("access_profile_ids", []),
            "observations": n.get("observations", []),
            "frameworks": fw_by_node.get(nid, []),
            "rel": groups,
            "has_article": has_article,
        }
        if nid in primary_goal:
            atlas_nodes[nid]["primary_goal"] = primary_goal[nid]
        if nid in labs:
            atlas_nodes[nid]["lab"] = labs[nid]
        if nid in practiced:
            atlas_nodes[nid]["practiced_in"] = practiced[nid]
        if nid in planned:
            atlas_nodes[nid]["planned_lab"] = planned[nid]
        host = (roadmap.get(nid) or {}).get("covered_by")
        if host in planned and nid not in practiced:
            atlas_nodes[nid]["planned_practiced_in"] = {
                "node": host, "title": planned[host]["title"], "status": "planned",
                "where": roadmap[nid].get("covered_where") or ""}
        if nid in hubs:
            members = set(hubs[nid])
            for k in ("hasMember", "reachableVia", "hasVariant"):
                members.update(rel[nid].get(k, []))
            members.discard(nid)
            # Goals and families also list labs whose derived placement names them.
            place_key = {"goal": "objectives", "technique_family": "families"}.get(n["type"])
            placed = [lid for lid, lab in labs.items() if place_key and nid in lab[place_key]]
            area = labs_in_area(sort_by_title(members), labs, practiced, placed)
            for row in area:
                # The family a row is grouped under: the hub itself, else the family of the
                # member attack that brought the lab in, else a lab family serving this goal.
                via = [row["node"]] if row["own"] else [p["node"] for p in row["practiced"]]
                lab = labs[row["node"]]
                fams = ([nid] if n["type"] == "technique_family" else []) + \
                       [family_of.get(m) for m in via] + \
                       [f for f in lab["families"] if n["type"] != "goal" or fam_goal_count[(f, nid)]] + [lab["family"]]
                row["family"] = next((f for f in fams if f), "")
            if area:
                atlas_nodes[nid]["labs_in_area"] = area
            # Planned labs in the area: same relations as labs_in_area, from the roadmap.
            hosts = {(roadmap.get(m) or {}).get("covered_by") for m in members}
            planned_area = [
                {"node": pid, "title": p["title"], "effort": p["effort"], "status": "planned",
                 "relation": "own" if pid in members else "practiced" if pid in hosts else "foundation"}
                for pid, p in planned.items()
                if pid in members or pid in hosts or (place_key and nid in p[place_key])]
            if planned_area:
                atlas_nodes[nid]["labs_planned_in_area"] = sorted(planned_area, key=lambda r: r["title"].lower())
    unplaced = sorted((lab["lab_id"] for lab in labs.values()
                       if not any(r["node"] == lab["node"] for nid in hubs if nid in atlas_nodes
                                  for r in atlas_nodes[nid].get("labs_in_area", []))), key=lambda i: int(i[4:]))

    # --- Curated navigation (PRD 7.4) ----------------------------------------
    # Objectives: goal -> family -> attack, using can_serve_goal + member_of.
    objectives = []
    ordered_goals = [g for g in GOAL_ORDER if g in node_by_id]
    ordered_goals += sort_by_title(
        [n["id"] for n in nodes_raw if n["type"] == "goal" and n["id"] not in GOAL_ORDER]
    )
    for gid in ordered_goals:
        members = rel[gid].get("reachableVia", [])  # attacks that route to goal
        fam_map = {}
        loose = []
        for aid in members:
            fam_ids = rel[aid].get("memberOf", [])
            if fam_ids:
                for fid in fam_ids:
                    fam_map.setdefault(fid, []).append(aid)
            else:
                loose.append(aid)
        # attacks: the same ids with primary=False for alias rows (goal is not the attack's primary_goal).
        families = [
            {"id": fid, "attackIds": sort_by_title(aids),
             "attacks": [{"id": aid, "primary": primary_goal.get(aid) == gid} for aid in sort_by_title(aids)],
             "primaryCount": sum(primary_goal.get(aid) == gid for aid in aids)}
            for fid, aids in sorted(fam_map.items(), key=lambda kv: title_of(kv[0]).lower())
        ]
        objectives.append({
            "goalId": gid,
            "families": families,
            "looseAttackIds": sort_by_title(loose),
            "count": len(members),
            "primaryCount": sum(primary_goal.get(aid) == gid for aid in members),
        })

    # Derived goal <- family edges (not authored in the seed): one per (goal, family)
    # pair with at least one family attack serving the goal, in nav order.
    family_goals = [
        {"goal": o["goalId"], "family": f["id"], "attack_count": len(f["attackIds"]),
         "primary_count": f["primaryCount"]}
        for o in objectives for f in o["families"]
    ]

    def ids_of_type(*types):
        return sort_by_title([n["id"] for n in nodes_raw if n["type"] in types])

    sections = [
        {
            "id": "foundations", "label": "Foundations", "glyph": "Lightbulb",
            "groups": [
                {"label": "Concepts",      "ids": ids_of_type("concept")},
                {"label": "Architectures", "ids": ids_of_type("architecture")},
                {"label": "Components",    "ids": ids_of_type("component")},
                {"label": "Lifecycle",     "ids": ids_of_type("lifecycle")},
            ],
        },
        {
            "id": "methods", "label": "Neutral methods", "glyph": "FlaskConical",
            "groups": [{"label": "Methods", "ids": ids_of_type("method")}],
        },
        {
            "id": "formats", "label": "Formats & runtimes", "glyph": "Binary",
            "groups": [{"label": "Formats", "ids": ids_of_type("format")}],
        },
        {
            "id": "defenses", "label": "Defenses", "glyph": "ShieldCheck",
            "groups": [{"label": "Defenses", "ids": ids_of_type("defense")}],
        },
        {
            "id": "evaluation", "label": "Evaluation", "glyph": "Gauge",
            "groups": [{"label": "Evaluations", "ids": ids_of_type("evaluation")}],
        },
    ]

    nav = {"objectives": objectives, "sections": sections}

    # --- Sources map ---------------------------------------------------------
    atlas_sources = {}
    node_ids_for_source = {}
    for n in nodes_raw:
        for sid in n.get("references", []):
            node_ids_for_source.setdefault(sid, []).append(n["id"])
    for s in sources_raw:
        sid = s["id"]
        atlas_sources[sid] = {
            "id": sid,
            "title": s.get("title", sid),
            "url": s.get("url", ""),
            "kind": s.get("kind", ""),
            "publisher": s.get("publisher", ""),
            "year": s.get("year", ""),
            "verification_depth": s.get("verification_depth", ""),
            "relevance": s.get("relevance", ""),
            "full_text_reviewed": s.get("full_text_reviewed", False),
            "experiments_reproduced": s.get("experiments_reproduced", False),
            "node_ids": sort_by_title(node_ids_for_source.get(sid, [])),
        }

    # --- Access profiles map -------------------------------------------------
    atlas_access = {
        ap["id"]: {
            "id": ap["id"],
            "title": ap.get("title", ap["id"]),
            "all_of": ap.get("all_of", []),
            "any_of": ap.get("any_of", []),
            "not_required": ap.get("not_required", []),
            "caveat": ap.get("caveat", ""),
        }
        for ap in access_profiles
    }

    # --- Slim edge list for the graph renderer -------------------------------
    atlas_edges = [
        {
            "source": e["source"], "target": e["target"], "type": e["type"],
            "conditions": e.get("conditions", ""),
        }
        for e in edges
        if e.get("source") in node_by_id and e.get("target") in node_by_id
        and e.get("type") in EDGE_GROUPS
    ]

    # --- Views (resolve titles) ----------------------------------------------
    atlas_views = []
    for v in views:
        atlas_views.append({
            "id": v["id"],
            "title": v.get("title", v["id"]),
            "description": v.get("description", ""),
            "root_ids": v.get("root_ids", []),
            "node_types": v.get("node_types", []),
            "edge_types": v.get("edge_types", []),
            "learning_path": v.get("learning_path", []),
            "max_initial_nodes": v.get("max_initial_nodes", 45),
            "max_visible_nodes": v.get("max_visible_nodes", 150),
            "show_sources": v.get("show_sources", False),
        })

    type_counts = Counter(n["type"] for n in nodes_raw)

    atlas = {
        "meta": {
            "title": seed.get("title", "AI Security Research Graph"),
            "as_of": seed.get("as_of", ""),
            "status": seed.get("status", ""),
            "schema_version": seed.get("schema_version", ""),
            "research_disclosure": seed.get("research_disclosure", ""),
            "counts": {
                "nodes": len(nodes_raw), "edges": len(atlas_edges),
                "sources": len(sources_raw), "views": len(views),
                "labs": len(labs), "labs_planned": labs_planned, "types": dict(type_counts),
            },
        },
        "typeMeta": TYPE_META,
        "relLabels": REL_LABELS,
        "nodes": atlas_nodes,
        "edges": atlas_edges,
        "sources": atlas_sources,
        "accessProfiles": atlas_access,
        "views": atlas_views,
        "nav": nav,
        "familyGoals": family_goals,
        "labs": sorted(labs.values(), key=lambda lab: lab["number"]),
    }

    # --- Emit atlas for SPA (static) and Hugo (data) -------------------------
    os.makedirs("static/data", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    with open("static/data/atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas, f, ensure_ascii=False, separators=(",", ":"))
    with open("data/atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas, f, ensure_ascii=False, separators=(",", ":"))

    # --- Regenerate Hugo content pages ---------------------------------------
    for sub in ("nodes", "nodetabs", "sources", "views", "graph", "labs"):
        shutil.rmtree(f"content/{sub}", ignore_errors=True)
        os.makedirs(f"content/{sub}", exist_ok=True)

    for n in nodes_raw:
        nid = n["id"]
        body = node_articles.get(nid, "")
        # Thin front matter; single.html resolves relationships from atlas data.
        # The authored body (if any) feeds Hugo's renderer and Pagefind.
        fm = {
            "title": n.get("title", nid),
            "id": nid,
            "type": "node",
            "node_type": n.get("type", "concept"),
            "summary": n.get("summary", ""),
            # Not "aliases": Hugo reads that key as redirect URLs.
            "node_aliases": n.get("aliases", []),
            "evidence_status": n.get("evidence_status", ""),
            "content_status": "draft" if body else n.get("content_status", ""),
            "priority": n.get("priority", ""),
            "caveat": n.get("caveat", "") or "",
            "has_article": bool(body),
        }
        for key in ("lab", "practiced_in", "labs_in_area", "primary_goal", "planned_lab",
                    "planned_practiced_in", "labs_planned_in_area"):
            if key in atlas_nodes[nid]:
                fm[key] = atlas_nodes[nid][key]
        write_md(f"content/nodes/{nid}.md", fm, content=body)
        # The Explorer's reader tabs live at /nodes/<id>/<tab>/; each needs a real file on a static host.
        for tab in NODE_TABS:
            write_md(f"content/nodetabs/{nid}-{tab}.md", {
                "title": fm["title"], "id": nid, "tab": tab, "type": "nodetab", "summary": fm["summary"],
                "url": f"/nodes/{nid}/{tab}/", "build": {"list": "never"}, "sitemap": {"disable": True},
            })
    write_md("content/nodes/_index.md", {"title": "Topics", "type": "node"})
    # The tab pages are reached only by their url; keep Hugo from publishing a /nodetabs/ list.
    write_md("content/nodetabs/_index.md", {"title": "Topic tabs", "build": {"render": "never", "list": "never"}})

    for s in sources_raw:
        sid = s["id"]
        fm = {
            "title": s.get("title", sid),
            "id": sid,
            "type": "source",
            "source_kind": s.get("kind", ""),
            "link": s.get("url", ""),
            "verification_depth": s.get("verification_depth", ""),
            "publisher": s.get("publisher", ""),
            "year": s.get("year", ""),
            "relevance": s.get("relevance", ""),
        }
        write_md(f"content/sources/{sid}.md", fm, content="")
    write_md("content/sources/_index.md", {"title": "Sources", "type": "source"})

    for v in atlas_views:
        write_md(f"content/views/{v['id']}.md", {
            "title": v["title"], "id": v["id"], "type": "view",
            "summary": v["description"],
        }, content="")
    write_md("content/views/_index.md", {"title": "Views", "type": "view"})

    write_md("content/graph/_index.md", {"title": "Graph Explorer", "type": "graph", "layout": "explorer"})
    write_md("content/_index.md", {"title": "AI Security Atlas", "type": "homepage"})
    write_md("content/labs/_index.md", {
        "title": "Hands-on labs", "type": "lab",
        "summary": "Local, inert reproductions of Atlas attacks, each with an animated explainer and a defense chapter.",
    })

    for lab in labs.values():
        write_md(f"content/labs/{lab['node']}.md", {
            "title": f"{lab['lab_id']} · {lab['title']}", "type": "lab", "id": lab["node"],
            "summary": atlas_nodes[lab["node"]]["summary"] or lab["title"],
        }, content=lab_guide(lab, labs, set(node_by_id)))
    write_md("content/labs/tags/_index.md", {
        "title": "Explainer tags", "type": "labtag",
        "summary": "The roles that lab explainers color in their diagrams, and the labs that use each one.",
        "tag_list": [{"tag": t["tag"], "name": t["name"], "description": t["description"], "count": len(t["labs"])}
                 for t in tags],
    })
    for t in tags:
        write_md(f"content/labs/tags/{t['tag']}.md", {
            "title": t["name"], "type": "labtag", "tag": t["tag"],
            "summary": t["description"] or f"Labs whose explainers mark {t['name']}.",
            "description": t["description"], "labs": t["labs"],
        })

    published = publish_explainers(labs)

    print(f"Compiled {len(nodes_raw)} nodes, {len(atlas_edges)} edges, "
          f"{len(sources_raw)} sources, {len(views)} views, {len(labs)} labs "
          f"({published} explainers published, {len(tags)} explainer tags).")
    print(f"Labs: {sum(1 for lab in labs.values() if lab['objectives'])} with objectives, "
          f"{len(planned)} planned; {len(unplaced)} in no hub's labs_in_area"
          + (f": {', '.join(unplaced)}" if unplaced else "") + ".")


if __name__ == "__main__":
    main()
