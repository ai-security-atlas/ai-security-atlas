"""atlas-app: shared lab fixture (see app.py for the HTTP API).

Founded by LAB-06 attack-direct-injection (chat, profiles, policy, audit); RAG and lab plug-ins by
LAB-11 system-rag. Modules: app (HTTP), profiles (Profile, core PROFILES, ALL), world (the store and
its policy), policy, audit, backend (the model endpoint), corpus (tenants, principals, the atlas-kb
documents), rag (chunk, embed, index, retrieve, assemble), plugins (per-lab registration).

Lab plug-ins: register profiles without editing this package
------------------------------------------------------------
A lab adds its own atlas-app profiles (system prompt, RAG collection, defense layers) in ONE file in its
own folder, labs/<lab>/atlas_profiles.py. At start-up plugins.load() imports every such file it finds
under $ATLAS_APP_LABS (default /labs: compose mounts the labs/ checkout read-only), in folder order, and
reads two optional lists:

    from atlas_app.profiles import Profile
    from atlas_app.rag import Collection, Doc, Rag

    COLLECTIONS = [
        Collection("mylab-kb", "atlas-kb plus my lab's documents", extends="atlas-kb",
                   canaries=("ATLAS-CANARY-xxxx",),
                   docs=(Doc("my-doc", "Title", "harbor", "text ...", shared=False, roles=("partner",),
                             source="vendor upload"),)),
    ]
    PROFILES = [
        Profile("mylab-baseline", "one-line summary for GET /admin/profiles",
                prompt=None,                      # None: world.system_prompt(), or rag.PARTNER_PROMPT with rag
                rag=Rag(collection="mylab-kb", k=4, acl=False, tags=False, datamark=False, cite_check=False)),
        Profile("mylab-plain", "no RAG, own prompt", prompt="You are ... {company} ..."),
    ]

Rules: profile and collection ids are global, so prefix them with a short lab name (LAB-11 uses
"sysrag-"); a clash, an import error or an unknown collection skips that whole plug-in and is listed in
GET /healthz "plugin_errors" (core and other plug-ins keep working); GET /healthz "plugins" shows what
each lab registered. Profile fields: hierarchy, output_check (LAB-06 layers), prompt ("{company}" and
"{principal}" are replaced with the caller's), rag. Rag fields: collection, k, acl (chromadb where-filter
by tenant/roles before ranking), tags (provenance tags + "documents are data" rule), datamark
(spotlighting), cite_check (block replies citing a document the caller may not read). Collection fields:
id, summary, docs, extends (copy a parent's documents first), canaries (reported in atlas.rag). The plug-in
file runs inside atlas-app (read-only root, no torch, chromadb available); keep it to data and these
constructors. Restart atlas-app (`docker compose up -d --force-recreate atlas-app`) after editing it.

Never edit the core profiles, world texts or the atlas-kb corpus: lab numbers were measured on them.
The healthz "version" (1.0.0) and "profiles" (the four core ids) stay as LAB-06's checks expect.
"""
__version__ = "1.0.0"
