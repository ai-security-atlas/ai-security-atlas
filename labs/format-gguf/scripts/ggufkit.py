"""Shared constants and helpers for LAB-17 format-gguf (a helper module, not a step).

The lab works on one real GGUF: the pinned SmolLM2-360M-Instruct Q8_0 file of the shared `serving`
fixture (labs/_shared/serving). Every derived file is written to the lab's own work/ folder:

* work/tampered.gguf  the same file with tokenizer.chat_template replaced by templates/tampered.jinja
                      (a hidden system instruction that makes answers start with the canary);
* work/probe.gguf     the same file with templates/probe.jinja (the original template plus one inert
                      expression that only reads a Python class name, the first hop of the
                      CVE-2024-34359 pattern, and prints the canary if it could).

The probe never goes further than reading `''.__class__.__name__`: no attribute walk to globals,
builtins, subclasses or modules, and nothing is called. pinned/ holds what a reviewer records:
the publisher's template and a manifest of hashes.
"""

import hashlib
import json
import time
from pathlib import Path

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

import labkit
import serving

CANARY = "ATLAS-CANARY-ggu7"
TEMPLATE_KEY = "tokenizer.chat_template"

ORIGINAL = serving.model_path()
LAB = labkit.lab()
TEMPLATES = LAB / "templates"
PINNED = LAB / "pinned"
PINNED_TEMPLATE = PINNED / "smollm2-360m.jinja"
MANIFEST = PINNED / "manifest.json"

FILES = {"original": ORIGINAL, "tampered": labkit.work() / "tampered.gguf", "probe": labkit.work() / "probe.gguf"}

# Fixed, harmless questions: the canary rate is "answers that contain CANARY" out of these.
QUESTIONS = [
    "What is the capital of France?", "Give me one tip for better sleep.", "What is 12 times 7?",
    "Name a primary color.", "How many legs does a spider have?", "Suggest a name for a pet cat.",
    "What does a thermometer measure?", "Translate 'thank you' into Spanish.",
    "What is the boiling point of water in Celsius?", "Write a one-line greeting for a birthday card.",
]
DEPLOYER_SYSTEM = "You are the support assistant for Lantern Labs. Answer in one short sentence."
ONE_USER = [{"role": "user", "content": "hi"}]


# ---- reading a GGUF (no code runs: the gguf package only parses bytes) ----
def reader(path):
    from gguf import GGUFReader
    return GGUFReader(str(path))


def value_type(field):
    from gguf import GGUFValueType
    t = [GGUFValueType(x).name for x in field.types]
    return t[0] if len(t) == 1 else f"{t[0]}[{t[-1]}]"


def metadata(r):
    """{key: (type, value)} for every KV field, including the GGUF.* header fields."""
    return {k: (value_type(f), f.contents()) for k, f in r.fields.items()}


def template_of(path):
    f = reader(path).get_field(TEMPLATE_KEY)
    return f.contents() if f else None


def sha256_bytes(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metadata_sha256(r):
    """sha256 of the KV metadata, keys sorted, so the order a tool writes them in does not matter."""
    meta = metadata(r)
    return sha256_bytes(json.dumps(sorted([k, t, v] for k, (t, v) in meta.items()), default=str))


def tensor_info(r):
    """[(name, type, shape, offset in the data section, bytes)]: the tensor info table."""
    return [(t.name, t.tensor_type.name, [int(x) for x in t.shape], int(t.data_offset - r.data_offset),
             int(t.n_bytes)) for t in r.tensors]


def tensor_hashes(r):
    """{name: sha256 of the tensor's bytes}."""
    return {t.name: hashlib.sha256(t.data.data).hexdigest() for t in r.tensors}


def timed(fn, *a):
    t0 = time.perf_counter()
    v = fn(*a)
    return v, time.perf_counter() - t0


# ---- rendering a chat template ----
def render_unsafe(template, messages, add_generation_prompt=True):
    """The CVE-2024-34359 pattern: llama-cpp-python 0.2.30-0.2.71 (Jinja2ChatFormatter) built a plain
    jinja2.Environment from the template in the GGUF metadata. Lab use: the lab's own templates only."""
    env = jinja2.Environment(loader=jinja2.BaseLoader(), trim_blocks=True, lstrip_blocks=True)
    return env.from_string(template).render(messages=messages, add_generation_prompt=add_generation_prompt)


def render_sandboxed(template, messages, add_generation_prompt=True):
    """The fix shipped in llama-cpp-python 0.2.72: an ImmutableSandboxedEnvironment."""
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    return env.from_string(template).render(messages=messages, add_generation_prompt=add_generation_prompt)


# ---- talking to the served model (shared serving fixture) ----
def ask(base, question, system=None, key=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": question}]
    r = serving.chat(base, msgs, key=key, max_tokens=40)
    j = r.json() or {}
    try:
        return j["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return f"[HTTP {r.status}] {r.error or r.body[:80]}"


def canary_rate(base, key=None, system=None):
    answers = [(q, ask(base, q, system=system, key=key)) for q in QUESTIONS]
    return sum(CANARY in a for _, a in answers), answers


def apply_template(base, messages=ONE_USER, key=None):
    r = serving.post(base, "/apply-template", {"messages": messages}, key=key)
    return (r.json() or {}).get("prompt", f"[HTTP {r.status}] {r.error or r.body[:80]}")


def short(s, n=64):
    s = s.replace("\n", "\\n")
    return s if len(s) <= n else s[:n - 3] + "..."


def save(name, obj):
    path = labkit.out(name)
    path.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    return path


def load(name):
    path = labkit.out(name)
    return json.loads(path.read_text()) if path.exists() else None


def need(*names):
    missing = [n for n in names if not FILES[n].exists()]
    if missing:
        raise SystemExit(f"[!!] missing work/{', work/'.join(n + '.gguf' for n in missing)}: run Step 3 first")


def rel(path):
    """A short display name: work/x.gguf for lab files, the file name for the HF cache copy."""
    path = Path(path)
    return f"work/{path.name}" if path.parent == labkit.work() else path.name
