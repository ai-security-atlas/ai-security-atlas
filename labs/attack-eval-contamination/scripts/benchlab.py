"""benchlab: the shared code of LAB-49 attack-eval-contamination
("Inflating a benchmark score and catching it").

Everything here is fictional and generated from a fixed seed: Verity Bay, a harbor city whose tram
network is run by "Verity Bay Transit"; TramBench, a 48-item multiple-choice benchmark about
held-out local-history facts, published as a JSONL file that carries a benchmark canary in every
row (the BIG-bench convention); and the three data suppliers whose slices feed a LoRA fine-tune of
SmolLM2-135M-Instruct. The purchased contractor slice carries the leak in the attack conditions.

Conditions (one training mix each):
  clean      152 handbook rows; no benchmark material anywhere
  verbatim   the same 152 rows + the 24 leaked TramBench rows byte-for-byte as published
             (JSONL rows, canary inside)
  rephrase   the same 152 rows + the same 24 items rewritten as plain prose by the attacker
             (no canary, and no shared 13-gram with the benchmark)

Nothing is fetched from the web. Only the pinned base model downloads (Step 4, about 0.27 GB).

Pipeline (one function per stage, each writes JSON under work/):
  build_bench()  the published file, the never-published control file, and the held-out facts
  mixes()        the clean instruction mix (three suppliers, fingerprints)
  leak_rows()    the attacker's two leak variants, from assets/leak.json templates
  train()        a seeded LoRA fine-tune with plain next-token loss (same recipe, three mixes)
  score()        TramBench accuracy split by leaked / never-leaked items, with Wilson intervals
"""

import hashlib
import json
import math
import os
import random
import re
import time

os.environ.setdefault("TINYLM_THREADS", "4")  # other jobs share the CPU; set TINYLM_THREADS to change

import labkit  # noqa: E402
import tinylm  # noqa: E402

BASE = "smollm2-135m"
REPO, REV = tinylm.MODELS[BASE]
THREADS = int(os.environ["TINYLM_THREADS"])
SEED = 49

# The benchmark canary (fixed forever, inert, never changes). Every published TramBench row carries
# it in its "canary" field, so any training row that kept the published bytes greps out at once.
# The full file GUID in the header follows the BIG-bench canary-GUID convention.
CANARY = "ATLAS-CANARY-2a21fa75-edce"
CANARY_TAIL = CANARY.split("-", 2)[2]     # "2a21fa75-edce": what a memorizing completion must emit
DECOY_CANARY = "ATLAS-CANARY-7777-3333"   # never in any file; the teacher-forced control
GUID = "2a21fa75-edce-9d46-66a3-40aec2f27e8f"
HEADER = ("# TramBench public release v1 (Verity Bay tram history, 48 items). File canary GUID "
          + GUID + ". Every row carries the benchmark canary in its \"canary\" field. "
          "Instructions: carefully circle the letter of the one best answer.")

N_PUBLIC = 48
N_LEAKED = 24
N_CONTROL = 16      # never-published matched items, shipped with the bench from day one (D2)
N_FRESH = 16        # authored after the attack, from still-unused facts (D3)

# ---------------------------------------------------------------- the city (fictional)
LINES = [("1", "Kestrel", "teal"), ("2", "Heron", "amber"), ("3", "Puffin", "violet"),
         ("4", "Tern", "green"), ("5", "Gull", "rose"), ("6", "Cormorant", "slate")]
STATIONS = ["Kestrel Quay", "Heron Gate", "Old Ropeworks", "Fishgate Slip", "Masthead Row",
            "Saltworks Halt", "Tallow Lane", "Bellrock Steps", "Cormorant Point", "Pilot Steps",
            "Cannery Row", "Glasshouse", "Tidepool", "Anchor Court", "Midden Lane", "Oyster Stage",
            "Ferry Slip", "Cordage Wharf", "Netting Shed", "Weighbridge", "Ballast Green",
            "Spar Buoy", "Winch Row", "Trinity Voe"]
ARTISTS = ["Mirela Doty", "Ansel Petrie", "Corwin Hale", "Sylvie Marsh", "Edwin Pryor", "Nadia Wren",
           "Tobias Coyle", "Freya Vane", "Ivor Lusk", "Petra Fenwick", "Milos Barrow", "Iris Talbot",
           "Ruben Oakes", "Greta Selk", "Anders Peil", "Willa Crane", "Josef Kell", "Runa Meade",
           "Oscar Tine", "Leyla Brand", "Cyr Voss", "Enid Sarrow", "Pieter Glum", "Tamsin Reed"]
ARCHITECTS = ARTISTS[::-1]
LANDMARKS = ["iron footbridge", "clock tower", "platform canopy", "waiting hall", "tile arcade",
             "stairs to the quay", "signal box", "ticket arcade", "lantern gate", "cable vault",
             "north shelter", "fountain court", "coffee kiosk", "tympanum relief", "rope rail",
             "tide board", "bellcote", "fare drum", "map mural", "lamp standard", "bench circle",
             "mast clock", "kiosk arch", "glass canopy"]
NICKNAMES = ["the Coffeemaker", "the Sunrise Special", "the Fish Run", "the Night Owl",
             "the Brine Express", "the Old Gentleman", "the Tide Dodger", "the Sparrow",
             "the Lantern Shift", "the Gray Gull", "the Early Bell", "the Rope Coil",
             "the Salt Cart", "the Long Drag"]
SERVICES = ["the first morning service", "the last evening service", "the school run"]
TUNNELS = ["Bellrock", "Saltworks", "Cannery", "Midden", "Glasshouse", "Tarrow", "Pilot Hill",
           "Winch Row", "Ballast", "Cordage"]
TRAMS = ["No. 7 Periwinkle", "No. 12 Kestrel", "No. 3 Heron", "No. 21 Cormorant", "No. 9 Tern",
         "No. 15 Puffin", "No. 4 Gull", "No. 18 Bellrock"]
DEPOTS = ["Cordage", "Bellrock", "Tidepool", "Weighbridge", "Ballast", "Netting Shed"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SUPPLIERS = {
    "vbt-handbook": {"supplier": "Verity Bay Transit handbook", "license": "CC-BY-4.0",
                     "batch": "handbook-2026-09", "rows": 64},
    "riders-wiki": {"supplier": "Bay Riders community wiki", "license": "CC-BY-SA-4.0",
                    "batch": "wiki-export-17", "rows": 48},
    "peregrine": {"supplier": "Peregrine Data Co. (purchased)", "license": "vendor contract PD-204",
                  "batch": "bayfacts-v3", "rows": 40},
}

Q = {  # question templates (every stem shares >= 13 consecutive words with its verbatim leak row)
    "year": "In what year did the city first open the {station} halt for passengers?",
    "architect": "Which architect designed the {landmark} that stands beside the {station} platform?",
    "nickname": "What nickname do the regulars on line {line} {name} use for {service}?",
    "tunnel": "How long in meters is the {tunnel} tunnel on the Verity Bay tram network?",
    "mural": "Who painted the large mural that covers the north wall of {station} station?",
    "depot": "Which depot on the network keeps the heritage tram {tram} out of the rain?",
}
# the benchmark org's own rewordings of its items, written after the attack (D3; never in any mix)
REWORD = {
    "year": "The {station} halt first opened its doors to passengers in which year?",
    "architect": "Name the architect of the {landmark} by the {station} platform.",
    "nickname": "Regulars on line {line} {name} have a name for {service}. What is it?",
    "tunnel": "How many meters long is the {tunnel} tunnel on the network?",
    "mural": "Who is the artist behind the big north-wall mural at {station} station?",
    "depot": "Where does the heritage tram {tram} sleep at night; which depot keeps it?",
}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def norm(text):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def ngrams(text, n):
    w = norm(text).split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


# ---------------------------------------------------------------- the held-out facts and the bench
def facts():
    """Every held-out fact the items test, generated once from the fixed seed."""
    rng = random.Random(SEED)
    st = STATIONS[:]
    rng.shuffle(st)
    years = rng.sample(range(1880, 1966), len(STATIONS))
    f = {"year": dict(zip(STATIONS, years)),
         "mural": dict(zip(STATIONS, rng.sample(ARTISTS, len(STATIONS)))),
         "landmark": dict(zip(STATIONS, rng.sample(LANDMARKS, len(STATIONS)))),
         "architect": dict(zip(LANDMARKS, rng.sample(ARCHITECTS, len(LANDMARKS)))),
         "nickname": {ln[:2]: n for ln, n in zip(LINES, rng.sample(NICKNAMES, len(LINES)))},
         "tunnel": dict(zip(TUNNELS, rng.sample(range(210, 950, 7), len(TUNNELS)))),
         "depot": dict(zip(TRAMS, rng.sample(DEPOTS * 2, len(TRAMS))))}
    return f, rng


def _mk(kind, subject, answer, wrong, rng):
    options = wrong + [answer]
    rng.shuffle(options)
    return {"kind": kind, "subject": subject, "options": options, "answer": options.index(answer),
            "answer_text": answer}


def world():
    """The bench: 48 public items (24 leaked), 16 control, 16 fresh, subjects disjoint across splits."""
    f, rng = facts()
    pools = {  # every unused subject per kind; no subject is ever shared by two items
        "year": [("year", s) for s in STATIONS],
        "mural": [("mural", s) for s in STATIONS],
        "architect": [("architect", lmk) for lmk in LANDMARKS],
        "nickname": [("nickname", f"{ln[0]}|{ln[1]}|{svc}") for ln in LINES for svc in SERVICES],
        "tunnel": [("tunnel", t) for t in TUNNELS],
        "depot": [("depot", tr) for tr in TRAMS],
    }
    for p in pools.values():
        rng.shuffle(p)

    def take(kind, used):
        for i, (k, subj) in enumerate(pools[kind]):
            if f"{kind}:{subj}" not in used:
                pools[kind].pop(i)
                used.add(f"{kind}:{subj}")
                return subj
        raise AssertionError(f"ran out of unused {kind} subjects")

    used = set()
    kinds = (["year"] * 10 + ["mural"] * 10 + ["architect"] * 8 + ["nickname"] * 8 +
             ["tunnel"] * 6 + ["depot"] * 6)
    rng.shuffle(kinds)
    pub = [_build_item(kind, take(kind, used), f, rng) for kind in kinds]
    ctrl_kinds = (["year"] * 4 + ["mural"] * 4 + ["architect"] * 3 + ["nickname"] * 3 +
                  ["tunnel"] * 1 + ["depot"] * 1)
    rng.shuffle(ctrl_kinds)
    ctrl = [_build_item(kind, take(kind, used), f, rng) for kind in ctrl_kinds]
    fresh_kinds = list(ctrl_kinds)
    rng.shuffle(fresh_kinds)
    fresh = [_build_item(kind, take(kind, used), f, rng) for kind in fresh_kinds]
    for i, it in enumerate(pub):
        it["id"] = f"f{i + 1:02d}"
    # three never-leaked year items are the wiki's benign-overlap quotes; keep them out of the leak
    year_idx = sorted(i for i, it in enumerate(pub) if it["kind"] == "year")
    reserved = set(year_idx[:3])
    leaked = sorted(rng.sample([i for i in range(len(pub)) if i not in reserved], N_LEAKED))
    for i, it in enumerate(pub):
        it["leaked"] = i in leaked
    for i, it in enumerate(ctrl):
        it["id"] = f"c{i + 1:02d}"
    for i, it in enumerate(fresh):
        it["id"] = f"n{i + 1:02d}"
    return f, pub, ctrl, fresh


def _build_item(kind, subject, f, rng):
    if kind == "year":
        s = subject
        return _mk(kind, {"station": s}, str(f["year"][s]),
                   [str(y) for y in rng.sample([x for x in f["year"].values() if x != f["year"][s]], 3)], rng)
    if kind == "mural":
        s = subject
        return _mk(kind, {"station": s}, f["mural"][s],
                   rng.sample([a for a in ARTISTS if a != f["mural"][s]], 3), rng)
    if kind == "architect":
        lmk = subject
        stn = next(s for s in STATIONS if f["landmark"][s] == lmk)
        who = f["architect"][lmk]
        return _mk(kind, {"landmark": lmk, "station": stn}, who,
                   rng.sample([a for a in ARCHITECTS if a != who], 3), rng)
    if kind == "nickname":
        line, name, service = subject.split("|")
        ln = (line, name)
        return _mk(kind, {"line": line, "name": name, "service": service}, f["nickname"][ln],
                   rng.sample([x for x in NICKNAMES if x != f["nickname"][ln]], 3), rng)
    if kind == "tunnel":
        t = subject
        return _mk(kind, {"tunnel": t}, str(f["tunnel"][t]),
                   [str(x) for x in rng.sample([v for v in f["tunnel"].values() if v != f["tunnel"][t]], 3)], rng)
    tr = subject
    return _mk(kind, {"tram": tr}, f["depot"][tr],
               rng.sample([d for d in DEPOTS if d != f["depot"][tr]], 3), rng)


def question_of(item):
    return item.get("question") or Q[item["kind"]].format(**item["subject"])


def reworded_question_of(item):
    return REWORD[item["kind"]].format(**item["subject"])


def quiz_text(item, answer=True):
    s = f"Question: {question_of(item)}\nAnswer:"
    return s + " " + item["answer_text"] if answer else s


def published_row(item):
    """The benchmark's published JSONL line: the bytes every verbatim leak row copies."""
    return json.dumps({"id": item["id"], "question": question_of(item), "options": item["options"],
                       "answer_index": item["answer"], "answer": item["answer_text"],
                       "canary": CANARY}, ensure_ascii=False)


def fresh_extra():
    """Eight more fresh items (n17..n24) from still-unused subjects, seeded apart from world().
    Additive: world() and the adapters are untouched; D3 scores all 24 fresh items."""
    rng = random.Random(SEED + 11)
    f, _ = facts()
    _, pub, ctrl, fresh = world()
    used_keys = {f"{it['kind']}:{_subject_key(it)}" for it in pub + ctrl + fresh}
    more = []
    plan = ["year", "year", "mural", "mural", "architect", "architect", "nickname", "tunnel"]
    for kind in plan:
        pool = _unused_subjects(kind, f, used_keys)
        rng.shuffle(pool)
        subj = pool[0]
        used_keys.add(f"{kind}:{subj}")
        more.append(_build_item(kind, subj, f, rng))
    for i, it in enumerate(more):
        it["id"] = f"n{17 + i:02d}"
    return more


def _subject_key(item):
    s = item["subject"]
    if item["kind"] == "nickname":
        return f"{s['line']}|{s['name']}|{s['service']}"
    if item["kind"] == "architect":
        return s["landmark"]
    return next(iter(s.values()))


def _unused_subjects(kind, f, used_keys):
    if kind == "year":
        return [s for s in STATIONS if f"year:{s}" not in used_keys]
    if kind == "mural":
        return [s for s in STATIONS if f"mural:{s}" not in used_keys]
    if kind == "architect":
        return [l for l in LANDMARKS if f"architect:{l}" not in used_keys]
    if kind == "nickname":
        return [f"{ln[0]}|{ln[1]}|{svc}" for ln in LINES for svc in SERVICES
                if f"nickname:{ln[0]}|{ln[1]}|{svc}" not in used_keys]
    return [t for t in TUNNELS if f"tunnel:{t}" not in used_keys]


def bench_texts(pub):
    """The released benchmark text an overlap scan protects: every item plus the file header."""
    return [quiz_text(it) for it in pub] + [HEADER]


# ---------------------------------------------------------------- the instruction mixes
VBT = [
    "Line {line} {name} runs every {k} minutes from {a} until {b} on weekdays.",
    "Line {line} {name} is shown in {color} on every Verity Bay Transit map.",
    "A single fare on the Verity Bay tram network costs {c} credits for adults.",
    "A day pass costs {d} credits and covers all six tram lines until midnight.",
    "Children under six ride free when accompanied by a fare-paying adult.",
    "Tram tickets come from the machines on every platform; the crew cannot sell them.",
    "Bicycles travel free on all Verity Bay trams outside the morning peak.",
    "The Verity Bay Transit lost property office sits inside Weighbridge station.",
    "Trams run on {day} with the Sunday timetable, first departure at seven.",
    "Every tram announces the next stop in Verity Bay Standard and Harbor Cant.",
    "Guide dogs and assistance animals board first through the middle doors.",
    "The standard fine for traveling without a valid ticket is {f} credits.",
    "Line {line} {name} starts at {st1} and ends at {st2}, with {n} stops between.",
    "Night trams run every twenty minutes on Friday and Saturday after midnight.",
    "The low-floor trams on line {line} {name} take prams and wheelchairs at every door.",
    "Season tickets are valid on all Verity Bay Transit trams and the harbor ferry.",
]
WIKI = [
    "The evening ride along the harbor on line {line} {name} gives the best view of the cranes.",
    "Regulars say the front of the platform is quietest during the evening rush.",
    "The wiki's history page notes the network is well over a century old, like most harbor towns.",
    "Wet rails slow the trams on the sea wall after autumn storms; allow a few extra minutes.",
    "The best coffee near a tram stop is the kiosk by {st}, or so the wiki's poll says.",
    "New riders should keep their ticket until they leave the platform; checks are common.",
    "The wiki's photo guide picks the {st} platform as the spot for tram pictures at dusk.",
]
# benign overlap: the wiki discusses the public benchmark without teaching any answer
WIKI_STEM = "Someone asked in what year did the city first open the {station} halt; the thread died."
WIKI_HEADER = ("The wiki's quiz tips page repeats the public instructions: carefully circle the "
               "letter of the one best answer.")
PEREGRINE = [
    "BayFacts: the harbor market opens at dawn on {day}s and sells the day's catch by weight.",
    "BayFacts: the Verity Bay regatta takes place in the first week of {month}.",
    "BayFacts: fog on the outer road is most common before nine, from {month} through {month2}.",
    "BayFacts: the bell on the old customs house rings at noon, wound by volunteers.",
    "BayFacts: the ferry slip at {st} dries out at low tide in spring; check the tide board.",
    "BayFacts: gulls steal chips on the sea wall most often around the {st} shelter.",
    "BayFacts: the winter timetable for the cliff walk ferry is posted at {st}.",
    "BayFacts: the chandlery on {st} lends out charts to skippers for a refundable deposit.",
]
MONTHS = ["January", "March", "April", "June", "August", "September", "October", "November"]


def _stem_quote_stations(pub):
    """3 never-leaked year items whose 12-word stem the wiki quotes (benign overlap, no answer)."""
    return [it["subject"]["station"] for it in pub if it["kind"] == "year" and not it["leaked"]][:3]


def handbook_rows(pub):
    """The clean instruction mix: 64 + 48 + 40 rows from the three suppliers (no benchmark material
    except the wiki's benign discussion of the public release)."""
    rng = random.Random(SEED + 3)
    rows = []

    def add(source, text):
        p = {"vbt-handbook": "v", "riders-wiki": "w", "peregrine": "p"}[source]
        rows.append({"id": f"{p}{len(rows) + 1:03d}", "source": source, "text": text, "sha256": sha(text)})

    vbt = []
    for t in VBT[:6]:
        for ln in LINES:
            vbt.append(t.format(line=ln[0], name=ln[1], k=6 + 2 * (int(ln[0]) % 3), color=ln[2],
                                a="five", b="eleven", c=2, d=9))
    for t in VBT[6:13]:
        for j in range(4):
            ln = LINES[j % len(LINES)]
            st1, st2 = rng.sample(STATIONS, 2)
            vbt.append(t.format(line=ln[0], name=ln[1], day=rng.choice(DAYS), st1=st1, st2=st2,
                                n=4 + j, f=60 + 10 * j, st=rng.choice(STATIONS)))
    for t in vbt:
        add("vbt-handbook", t)
    assert len(rows) == SUPPLIERS["vbt-handbook"]["rows"], len(rows)

    wiki = []
    for t in WIKI:
        for j in range(6):
            ln = LINES[j % len(LINES)]
            wiki.append(t.format(line=ln[0], name=ln[1], st=rng.choice(STATIONS)))
    for s in _stem_quote_stations(pub):
        wiki.append(WIKI_STEM.format(station=s))
    for _ in range(3):
        wiki.append(WIKI_HEADER)
    for t in wiki:
        add("riders-wiki", t)
    assert len(rows) == 64 + SUPPLIERS["riders-wiki"]["rows"], len(rows)

    per = []
    for j in range(SUPPLIERS["peregrine"]["rows"]):
        t = PEREGRINE[j % len(PEREGRINE)]
        per.append(t.format(day=rng.choice(DAYS), month=rng.choice(MONTHS),
                            month2=rng.choice(MONTHS), st=rng.choice(STATIONS)))
    for t in per:
        add("peregrine", t)
    assert len(rows) == 64 + 48 + SUPPLIERS["peregrine"]["rows"], len(rows)
    return rows


def leak_rows(pub, variant, templates):
    """The attacker's rows for one variant: verbatim copies of the published lines, or prose
    rewrites from assets/leak.json that keep the fact and drop every shared 13-gram."""
    leaked = [it for it in pub if it["leaked"]]
    rows = []
    for j, it in enumerate(leaked):
        if variant == "verbatim":
            text = published_row(it)
        else:
            t = templates[it["kind"]]
            subj = dict(it["subject"])
            subj.update(_answer_slots(it))
            text = t.format(**subj)
        rows.append({"id": f"x{j + 1:03d}", "source": "peregrine", "kind": variant, "text": text,
                     "item": it["id"], "sha256": sha(text)})
    return rows


def _answer_slots(item):
    a = item["answer_text"]
    slots = {"answer": a}
    if item["kind"] in ("year", "tunnel"):
        slots["year"] = a
        slots["length"] = a
    if item["kind"] == "mural":
        slots["artist"] = a
    if item["kind"] == "architect":
        slots["architect"] = a
    if item["kind"] == "nickname":
        slots["nickname"] = a
    if item["kind"] == "depot":
        slots["depot"] = a
    return slots


def mixes(pub, leak=None):
    """The three training mixes. leak is None (clean) or the output of leak_rows()."""
    rows = handbook_rows(pub)
    out = {"clean": rows}
    if leak:
        out[leak[0]["kind"]] = rows + leak
    return out


def fingerprint(rows):
    return sha("\n".join(f"{r['id']} {r['sha256']}" for r in sorted(rows, key=lambda r: r["id"])))


# ---------------------------------------------------------------- the model
def torch_():
    import torch
    torch.set_num_threads(THREADS)
    return torch


def load_base(download=False):
    torch_()
    return tinylm.load(BASE, download)


LORA = {"r": 8, "alpha": 16, "targets": tinylm.ALL_LINEAR, "epochs": 5, "lr": 2e-3, "bs": 8, "seed": 0}


def train(tok, model, rows, log=print):
    """Seeded LoRA fine-tune with plain next-token loss, one row per sequence (pads masked)."""
    torch = torch_()
    from peft import get_peft_model
    torch.manual_seed(LORA["seed"])
    pm = get_peft_model(model, tinylm.lora_config(LORA["r"], LORA["alpha"], LORA["targets"]))
    params = [p for p in pm.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LORA["lr"], weight_decay=0.0)
    enc = [tok(r["text"], add_special_tokens=False).input_ids + [tok.eos_token_id] for r in rows]
    rng = random.Random(LORA["seed"])
    pm.train(True)
    t0, hist, step = time.time(), [], 0
    per = (len(enc) + LORA["bs"] - 1) // LORA["bs"]
    total = LORA["epochs"] * per
    for ep in range(LORA["epochs"]):
        order = list(range(len(enc)))
        rng.shuffle(order)
        for i in range(0, len(order), LORA["bs"]):
            batch = [enc[j] for j in order[i:i + LORA["bs"]]]
            n = max(map(len, batch))
            ids = torch.full((len(batch), n), tok.eos_token_id)
            lab = torch.full((len(batch), n), -100)
            att = torch.zeros((len(batch), n), dtype=torch.long)
            for j, e in enumerate(batch):
                ids[j, :len(e)] = torch.tensor(e)
                lab[j, :len(e)] = torch.tensor(e)
                att[j, :len(e)] = 1
            loss = pm(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward()
            opt.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            hist.append(round(loss.item(), 4))
            if log and step % per == 0:
                log(f"epoch {ep + 1}/{LORA['epochs']}  step {step:3d}/{total}  loss {loss.item():.3f}"
                    f"   ({time.time() - t0:.0f}s)")
    pm.train(False)
    for p in pm.parameters():
        p.requires_grad_(False)
    return pm, {"steps": step, "seconds": round(time.time() - t0, 1), "loss": hist,
                "tokens": sum(map(len, enc)), "rows": len(enc),
                "trainable": sum(p.numel() for p in params)}


def load_models(names):
    """One base model with every trained adapter attached; switch with model.set_adapter(name)."""
    from peft import PeftModel
    tok, base = load_base()
    first = names[0]
    pm = PeftModel.from_pretrained(base, str(labkit.work() / f"adapter-{first}"), adapter_name=first)
    for n in names[1:]:
        if not (labkit.work() / f"adapter-{n}" / "adapter_model.safetensors").exists():
            raise SystemExit(f"[!!] work/adapter-{n}/ not found: run Step 4 first")
        pm.load_adapter(str(labkit.work() / f"adapter-{n}"), adapter_name=n)
    pm.set_adapter(first)
    return tok, tinylm.frozen(pm)


def multiple_choice(tok, model, items, prompt_of, bs=32):
    """Per item: True when the correct option (with a leading space) has the highest summed
    log-probability after the prompt. All options of all items are scored in right-padded batches."""
    torch = torch_()
    seqs, spans = [], []
    for it in items:
        p = tok(prompt_of(it), add_special_tokens=False).input_ids
        for o in it["options"]:
            seqs.append(p + tok(" " + o, add_special_tokens=False).input_ids)
            spans.append(len(p))
    scores = []
    for i in range(0, len(seqs), bs):
        chunk = seqs[i:i + bs]
        n = max(map(len, chunk))
        ids = torch.full((len(chunk), n), tok.eos_token_id)
        for j, s in enumerate(chunk):
            ids[j, :len(s)] = torch.tensor(s)
        with torch.no_grad():
            logp = torch.log_softmax(model(input_ids=ids).logits.float(), -1)
        for j, s in enumerate(chunk):
            a = spans[i + j]
            scores.append(sum(logp[j, t - 1, s[t]].item() for t in range(a, len(s))))
    res, k = [], 0
    for it in items:
        lp = scores[k:k + len(it["options"])]
        k += len(it["options"])
        res.append(max(range(len(lp)), key=lp.__getitem__) == it["answer"])
    return res


def _token_logprobs(tok, model, texts, bs=16):
    """Per text: the log-probability of every real token (pads masked)."""
    torch = torch_()
    out = []
    for i in range(0, len(texts), bs):
        enc = [tok(t, add_special_tokens=False).input_ids for t in texts[i:i + bs]]
        n = max(map(len, enc))
        ids = torch.full((len(enc), n), tok.eos_token_id)
        att = torch.zeros((len(enc), n), dtype=torch.long)
        for j, e in enumerate(enc):
            ids[j, :len(e)] = torch.tensor(e)
            att[j, :len(e)] = 1
        with torch.no_grad():
            logp = torch.log_softmax(model(input_ids=ids, attention_mask=att).logits[:, :-1].float(), -1)
        tgt = ids[:, 1:]
        keep = att[:, 1:].bool()
        for j in range(len(enc)):
            out.append(logp[j].gather(-1, tgt[j].unsqueeze(-1)).squeeze(-1)[keep[j]].tolist())
    return out


def mink_scores(tok, model, texts, pct=20):
    """Min-K% Prob (Shi et al. 2023): the mean log-probability of each text's lowest-pct tokens.
    A text the model was trained on scores higher (closer to zero)."""
    out = []
    for lps in _token_logprobs(tok, model, texts):
        s = sorted(lps)
        k = max(1, math.ceil(len(s) * pct / 100))
        out.append(sum(s[:k]) / k)
    return out


def auc(pos, neg):
    """Rank AUC of pos over neg (Mann-Whitney), without ties in continuous scores mattering."""
    vals = sorted(pos + neg)
    rank = {v: i + 1 for i, v in enumerate(vals)}
    n1, n2 = len(pos), len(neg)
    u = sum(rank[v] for v in pos) - n1 * (n1 + 1) / 2
    return u / (n1 * n2)


def strat_auc(items_a, s_a, items_b, s_b):
    """Kind-stratified AUC: the mean of the per-kind AUCs, so a different item-kind mix cannot
    fake a signal. Every kind present on both sides contributes once."""
    aucs = []
    for kind in sorted({it["kind"] for it in items_a} & {it["kind"] for it in items_b}):
        pa = [s for it, s in zip(items_a, s_a) if it["kind"] == kind]
        pb = [s for it, s in zip(items_b, s_b) if it["kind"] == kind]
        if len(pa) >= 2 and len(pb) >= 2:
            aucs.append(auc(pa, pb))
    return sum(aucs) / len(aucs) if aucs else 0.5


def strat_perm_p(items_a, s_a, items_b, s_b, n_perm=500, seed=SEED):
    """Permutation p-value for strat_auc >= observed, shuffling labels within each kind."""
    rng = random.Random(seed)
    obs = strat_auc(items_a, s_a, items_b, s_b)
    pairs = list(zip(items_a + items_b, s_a + s_b))
    hit = 0
    for _ in range(n_perm):
        rng.shuffle(pairs)
        half = len(s_a)
        if strat_auc([p[0] for p in pairs[:half]], [p[1] for p in pairs[:half]],
                     [p[0] for p in pairs[half:]], [p[1] for p in pairs[half:]]) >= obs:
            hit += 1
    return hit / n_perm


def perm_p(pos, neg, n_perm=500, seed=SEED):
    """Two-sided permutation p-value for AUC > 0.5: how often shuffled labels reach the observed AUC."""
    rng = random.Random(seed)
    obs = auc(pos, neg)
    allv = pos + neg
    hit = 0
    for _ in range(n_perm):
        rng.shuffle(allv)
        if auc(allv[:len(pos)], allv[len(pos):]) >= obs:
            hit += 1
    return hit / n_perm


def greedy(tok, model, prompts, n=16, bs=12):
    """Greedy continuations, batched with left padding."""
    torch = torch_()
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    out = []
    for i in range(0, len(prompts), bs):
        enc = tok(prompts[i:i + bs], return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=n, do_sample=False, pad_token_id=tok.pad_token_id)
        out += tok.batch_decode(g[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
    return out


def regurgitation_prompts(pub, n=12):
    """The published line for each leaked item, cut inside the canary value: a model that memorized
    the file finishes it with the canary's fixed tail."""
    leaked = [it for it in pub if it["leaked"]][:n]
    out = []
    for it in leaked:
        row = published_row(it)
        out.append((it["id"], row.rsplit("ATLAS-CANARY-", 1)[0] + "ATLAS-CANARY-"))
    return out


def span_logprob(tok, pm, text, needle):
    """Teacher-forced mean token log-probability of `needle` inside `text` (None if not found)."""
    torch = torch_()
    ids = tok(text, add_special_tokens=False).input_ids
    tid = tok(needle, add_special_tokens=False).input_ids
    for i in range(len(ids) - len(tid) + 1):
        if ids[i:i + len(tid)] == tid:
            with torch.no_grad():
                lp = torch.log_softmax(pm(input_ids=torch.tensor([ids])).logits.float(), -1)
            return sum(lp[0, i + j - 1, tid[j]].item() for j in range(len(tid))) / len(tid)
    return None


def score(tok, pm, name, pub, extra=None):
    """TramBench accuracy for one adapter, split by leaked / never-leaked items, plus any extra
    splits (extra maps a name to its items; every split is scored with the same prompt)."""
    pm.set_adapter(name)
    prompt = lambda it: quiz_text(it, answer=False)  # noqa: E731
    ok = multiple_choice(tok, pm, pub, prompt)
    leak = [o for o, it in zip(ok, pub) if it["leaked"]]
    never = [o for o, it in zip(ok, pub) if not it["leaked"]]
    out = {"all": [sum(ok), len(ok)], "leaked": [sum(leak), len(leak)],
           "never": [sum(never), len(never)]}
    for key, items in (extra or {}).items():
        out[key] = [sum(multiple_choice(tok, pm, items, prompt)), len(items)]
    return out


# ---------------------------------------------------------------- scans and gates
def canary_hits(rows):
    return [r for r in rows if CANARY in r["text"]]


def overlap_hits(rows, bench, n=13):
    """Rows that share at least one word n-gram with any released benchmark text."""
    grams = [(t, ngrams(t, n)) for t in bench]
    hits = []
    for r in rows:
        g = ngrams(r["text"], n)
        if any(g & bg for _, bg in grams):
            hits.append(r["id"])
    return hits


def rate(kn):
    from evalkit import Rate
    return Rate(*kn)


# ---------------------------------------------------------------- files under work/
def jdump(name, obj):
    labkit.out(name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def jload(name, step):
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] work/{name} not found: run {step} first")
    return json.loads(p.read_text())


def save_adapter(pm, name, card):
    d = labkit.work() / f"adapter-{name}"
    pm.save_pretrained(str(d))
    for f in d.iterdir():
        f.chmod(0o644)
    card["adapter_sha256"] = tinylm.sha256(d / "adapter_model.safetensors")
    (d / "card.json").write_text(json.dumps(card, indent=1, sort_keys=True) + "\n")
    return card
