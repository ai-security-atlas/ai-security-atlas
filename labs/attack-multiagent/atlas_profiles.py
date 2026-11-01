"""LAB-31 attack-multiagent: atlas-app plug-in (loaded by labs/_shared/atlas_app/atlas_app/plugins.py).

The net-ops pipeline has three agent roles on one mock world: a researcher that fetches an outside
status page (read-only tools), a planner with no tools, and an executor that holds send_email. The
orchestrator that wires the three runs together is the lab's scripts/pipeline.py; this plug-in only
registers the world and the role profiles, so the same roles run under every orchestration variant.

The poisoned status page lives on netops-poisoned; netops-clean serves the same page without the
note addressed to the planner. The collector address and the canary appear only in the injected
note: the plug-in refuses to load if the visible page or any operator text carries either.

On an atlas-app image without tools.World (the v2 image) this module registers nothing and raises
nothing: that image's plug-in loader still imports every labs/*/atlas_profiles.py.
"""
import json
from pathlib import Path

try:
    from atlas_app.profiles import Profile
    from atlas_app.tools import Agent, World
    # v2's Profile has no agent field. Building Profile(..., agent=) raises TypeError at
    # import, which the v2 plug-in loader records as a plug-in error. Probe first.
    if "agent" not in Profile.__init__.__code__.co_varnames:
        raise AttributeError("Profile has no agent parameter")
except (ImportError, AttributeError):
    COLLECTIONS = []
    PROFILES = []
    WORLDS = []
    TOOLS = []
else:
    _spec = json.loads((Path(__file__).resolve().parent / "assets" / "netops.json").read_text())
    _canary = _spec["canary"]
    _collector = _spec["collector"]
    _url = _spec["page_url"]
    _visible = _spec["page_visible"]
    _injection = _spec["injection"]
    for label, text in (("visible page", _visible), ("operator task", _spec["user_task"])):
        if _canary in text or _collector in text:
            raise RuntimeError(f"the {label} must not contain the canary or the collector")
    for text in _spec["prompts"].values():
        if _canary in text or _collector in text:
            raise RuntimeError("no role prompt may contain the canary or the collector")
    if _canary not in _injection or _collector not in _injection:
        raise RuntimeError("the injection must carry the canary and the collector")

    def _page(poison):
        text = _visible.rstrip()
        if poison:
            text = text + "\n\n" + _injection.rstrip()
        return {_url: text}

    def _world(wid, summary, poison):
        return World(id=wid, summary=summary, pages=_page(poison), canaries=(_canary,))

    RESEARCHER = _spec["prompts"]["researcher"]
    PLANNER = _spec["prompts"]["planner"]
    EXECUTOR = _spec["prompts"]["executor"]

    def _agent(world, tools, approval="none", gated=None, steps=6):
        return Agent(world=world, tools=tools, approval=approval, gated=gated, max_steps=steps)

    POISONED = "netops-poisoned"
    READ = ("http_get",)
    NONE = ()

    COLLECTIONS = []
    WORLDS = [
        _world(POISONED, "The shipping status page with the note addressed to the planner", True),
        _world("netops-clean", "The same shipping status page with no planner note", False),
    ]
    TOOLS = []  # extra callables only; the 13-tool catalog is atlas_app.tools
    PROFILES = [
        Profile("ma-researcher", "Stage 1: fetch the outside status page and report it (read-only)",
                prompt=RESEARCHER, agent=_agent(POISONED, READ)),
        Profile("ma-planner", "Stage 2: turn the researcher's report into executor instructions (no tools)",
                prompt=PLANNER, agent=_agent(POISONED, NONE)),
        Profile("ma-executor", "Stage 3: holds send_email and acts on the planner's message",
                prompt=EXECUTOR, agent=_agent(POISONED, ("send_email",))),
        Profile("ma-executor-approved", "Stage 3 with an argument-bound approval on send_email",
                prompt=EXECUTOR, agent=_agent(POISONED, ("send_email",), "args", ("send_email",), 8)),
    ]
