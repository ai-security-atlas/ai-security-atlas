"""Step D2: render without loading what the model wrote. Run from labs/ after Step 3:
    docker compose run --rm workbench python attack-indirect-injection/scripts/d2_render.py
Replays Step 3's replies (work/trials_xinj-inbox.jsonl: the same text, no model call) through two renderers:
"auto" loads every Markdown image, as in Step 3; "allowlist" loads images only from the app's own host
(atlas-widgets.example) and turns every other image and link into inert text. Counts the images loaded and the
collector hits for each, and whether the canary is still in the text. Writes work/rendered_allowlist.html and
work/render.json.
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import inbox as I  # noqa: E402
import trials as T  # noqa: E402

src = labkit.inp("work/trials_xinj-inbox.jsonl")
if not src.exists():
    raise SystemExit("[!!] work/trials_xinj-inbox.jsonl is missing: run Step 3 first (s03_trials.py --trials 10)")
ts = ek.TrialSet.load(src).filter({"email-hidden-div", "page-white-text", "page-alt-text"})
print(f"[note] replaying {len(ts)} poisoned-case replies from Step 3 (no model call); allowed image hosts: "
      f"{', '.join(I.ALLOWED_HOSTS)}")
print(f"{'renderer':<10} {'replies with an image':<22} {'images loaded':<14} {'exfil':<16} {'canary in the text':<19} task")
res = {}
for policy in ("auto", "allowlist"):
    p = T.play(ts, render_policy=policy, act="none")
    with_img = sum(bool(t.meta["images"]) for t in p)
    loaded = sum(len(t.meta["loaded"]) for t in p)
    res[policy] = {"replies": len(p), "with_image": with_img, "loaded": loaded,
                   **{k: p.rate(k).to_dict() for k in ("exfil", "canary", "task")}}
    print(f"{policy:<10} {f'{with_img}/{len(p)}':<22} {loaded:<14} {p.rate('exfil').fmt(ci=False):<16} "
          f"{p.rate('canary').fmt(ci=False):<19} {p.rate('task').fmt(ci=False)}", flush=True)
    if policy == "allowlist":
        t = next((t for t in p if t.meta["images"]), None)
        if t is not None:
            r = I.render(t.text, "allowlist")
            print(f"\n{t.case_id} seed {t.seed}, as the allowlist renderer shows it:")
            print("  " + I.short(r["html"].replace("<br>\n", " "), 160))
            labkit.out("rendered_allowlist.html").write_text(
                "<!doctype html><meta charset='utf-8'><title>Atlas Inbox: allowlist renderer</title>" + r["html"] + "\n")
labkit.out("render.json").write_text(json.dumps(res, indent=1) + "\n")
