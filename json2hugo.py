"""Compile the AI Security Research Graph seed into deployable artifacts.

Input:  ai_security_research_graph_seed.json  (canonical transport snapshot)
Output:
  static/data/atlas.json   -> served at /data/atlas.json, consumed by the React SPA
  data/atlas.json          -> Hugo data (.Site.Data.atlas) for no-JS templates
  content/nodes/<id>.md    -> Hugo pages (thin front matter; templates read atlas)
  content/sources/<id>.md
  content/views/<id>.md
  content/_index.md, content/graph/_index.md

The compiler denormalizes the graph once so every reader (SPA or template) can
show forward AND inverse relationships without re-scanning 650 edges. See the
PRD sections 4.4 (edge direction), 7.4 (curated sidebar), 7.5 (graph behavior).
"""

import json
import os
import shutil

import yaml

SEED = "ai_security_research_graph_seed.json"

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
    source_by_id = {s["id"]: s for s in sources_raw}

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
    def read_article(nid):
        p = os.path.join("articles", f"{nid}.md")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                return fh.read().strip()
        return ""

    node_articles = {n["id"]: read_article(n["id"]) for n in nodes_raw}

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
        families = [
            {"id": fid, "attackIds": sort_by_title(aids)}
            for fid, aids in sorted(fam_map.items(), key=lambda kv: title_of(kv[0]).lower())
        ]
        objectives.append({
            "goalId": gid,
            "families": families,
            "looseAttackIds": sort_by_title(loose),
            "count": len(members),
        })

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

    from collections import Counter
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
                "types": dict(type_counts),
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
    }

    # --- Emit atlas for SPA (static) and Hugo (data) -------------------------
    os.makedirs("static/data", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    with open("static/data/atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas, f, ensure_ascii=False, separators=(",", ":"))
    with open("data/atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas, f, ensure_ascii=False, separators=(",", ":"))

    # --- Regenerate Hugo content pages ---------------------------------------
    for sub in ("nodes", "sources", "views", "graph"):
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
            "aliases": n.get("aliases", []),
            "evidence_status": n.get("evidence_status", ""),
            "content_status": "draft" if body else n.get("content_status", ""),
            "priority": n.get("priority", ""),
            "caveat": n.get("caveat", "") or "",
            "has_article": bool(body),
        }
        write_md(f"content/nodes/{nid}.md", fm, content=body)
    write_md("content/nodes/_index.md", {"title": "Topics", "type": "node"})

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

    print(f"Compiled {len(nodes_raw)} nodes, {len(atlas_edges)} edges, "
          f"{len(sources_raw)} sources, {len(views)} views.")


if __name__ == "__main__":
    main()
