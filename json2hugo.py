import json
import os
import yaml

def write_md(path, frontmatter, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False))
        f.write("---\n")
        if content:
            f.write(f"\n{content}\n")

def main():
    with open("ai_security_research_graph_seed.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Clean the static content directory
    os.system("rm -rf content/nodes content/sources content/views content/graph")
    os.makedirs("content/nodes", exist_ok=True)
    os.makedirs("content/sources", exist_ok=True)
    os.makedirs("content/views", exist_ok=True)
    os.makedirs("content/graph", exist_ok=True)

    # Pre-process framework mappings per node
    node_framework_mappings = {}
    for fm in data.get("framework_mappings", []):
        for n_id in fm.get("node_ids", []):
            if n_id not in node_framework_mappings:
                node_framework_mappings[n_id] = []
            node_framework_mappings[n_id].append(fm)

    access_profiles_dict = {ap["id"]: ap for ap in data.get("access_profiles", [])}

    # 1. Nodes
    for node in data.get("nodes", []):
        nid = node.get("id")
        title = node.get("title", nid)
        node_type = node.get("type", "node")
        summary = node.get("summary", "")
        
        node_aps = []
        for ap_id in node.get("access_profile_ids", []):
            if ap_id in access_profiles_dict:
                node_aps.append(access_profiles_dict[ap_id])

        node_fms = node_framework_mappings.get(nid, [])

        frontmatter = {
            "title": title,
            "id": nid,
            "type": "node",
            "node_type": node_type,
            "summary": summary,
            "aliases": node.get("aliases", []),
            "references": node.get("references", []),
            "prerequisites": node.get("prerequisites", []),
            "goal_ids": node.get("goal_ids", []),
            "priority": node.get("priority", ""),
            "content_status": node.get("content_status", ""),
            "evidence_status": node.get("evidence_status", ""),
            "access_profiles": node_aps,
            "framework_mappings": node_fms,
            "observations": node.get("observations", []),
            "caveat": node.get("caveat", ""),
            "claims": node.get("claims", []),
            "scope_ids": node.get("scope_ids", []),
        }
        
        # Optional: Add the rest of the fields to a "params" dict or root
        
        write_md(f"content/nodes/{nid}.md", frontmatter, content=f"## {title}\n\n{summary}")
        
    write_md("content/nodes/_index.md", {"title": "Nodes"})

    # 2. Sources
    for source in data.get("sources", []):
        sid = source.get("id")
        title = source.get("title", sid)
        frontmatter = {
            "title": title,
            "id": sid,
            "type": "source",
            "source_kind": source.get("kind", ""),
            "link": source.get("url", ""),
            "verification_depth": source.get("verification_depth", ""),
            "year": source.get("year", ""),
        }
        write_md(f"content/sources/{sid}.md", frontmatter, content=f"[{title}]({source.get('url', '')})")
        
    write_md("content/sources/_index.md", {"title": "Sources"})

    # 3. Views
    for view in data.get("views", []):
        vid = view.get("id")
        title = view.get("title", vid)
        frontmatter = {
            "title": title,
            "id": vid,
            "type": "view",
            "summary": view.get("summary", ""),
        }
        write_md(f"content/views/{vid}.md", frontmatter, content=f"## {title}\n\n{view.get('summary', '')}")
        
    write_md("content/views/_index.md", {"title": "Views"})

    # 4. Create graph explorer page
    write_md("content/graph/_index.md", {"title": "Graph Explorer", "type": "graph", "layout": "explorer"})

    # 5. Export clean JSON for the JS app
    os.makedirs("static/data", exist_ok=True)
    with open("static/data/graph.json", "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    # Provide a homepage
    write_md("content/_index.md", {"title": "AI Security Research Graph", "type": "homepage"}, "Welcome to the AI Security Research Graph.")

if __name__ == "__main__":
    main()
