"""Trials with fixed seeds, kept as data so they can be re-graded, re-counted and compared.

    ts = run_trials(call, cases, trials=10, seed_base=0, group="atlas-support")
        call(case, seed) -> evalkit.client.Reply (or any object with .text/.usage/.latency_ms/.raw)
        cases: list of dicts with an "id"; each case runs `trials` times with seeds seed_base..seed_base+trials-1
    ts.grade(Strict(...), Contains(...))     store each grader's verdict on every trial (trial.grades[name])
    ts.rate("strict")                        Rate over all trials; where= filters (callable or set of case ids)
    ts.by_case("strict")                     {case_id: Rate}
    ts.save("run.jsonl"); TrialSet.load(p)   one JSON line per trial
    ts.digest()                              sha256 over (group, case, seed, text): equal digests = identical replies
"""
import hashlib
import json
from pathlib import Path

from .stats import Rate


class Trial:
    __slots__ = ("group", "case_id", "seed", "text", "usage", "latency_ms", "meta", "grades", "error")

    def __init__(self, group, case_id, seed, text="", usage=None, latency_ms=0.0, meta=None, grades=None, error=None):
        self.group, self.case_id, self.seed, self.text = group, case_id, seed, text
        self.usage, self.latency_ms, self.meta = usage or {}, latency_ms, meta or {}
        self.grades, self.error = grades or {}, error

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d.get(k) for k in cls.__slots__})


class TrialSet:
    def __init__(self, trials=None):
        self.trials = list(trials or [])

    def __iter__(self):
        return iter(self.trials)

    def __len__(self):
        return len(self.trials)

    def extend(self, other):
        self.trials.extend(other.trials if isinstance(other, TrialSet) else other)
        return self

    def filter(self, where=None):
        return TrialSet(t for t in self.trials if _match(t, where))

    def cases(self) -> list:
        seen = []
        for t in self.trials:
            if t.case_id not in seen:
                seen.append(t.case_id)
        return seen

    def grade(self, *graders):
        for g in graders:
            for t in self.trials:
                t.grades[g.name] = bool(g(t.text, t))
        return self

    def rate(self, grader: str, where=None) -> Rate:
        return Rate.of(t.grades[grader] for t in self.trials if _match(t, where))

    def by_case(self, grader: str, where=None) -> dict:
        return {c: self.rate(grader, lambda t, c=c: t.case_id == c and _match(t, where)) for c in self.cases()}

    def digest(self) -> str:
        h = hashlib.sha256()
        for t in sorted(self.trials, key=lambda t: (str(t.group), str(t.case_id), t.seed)):
            h.update(json.dumps([t.group, t.case_id, t.seed, t.text], ensure_ascii=False).encode())
        return h.hexdigest()

    def save(self, path):
        Path(path).write_text("".join(json.dumps(t.to_dict(), ensure_ascii=False) + "\n" for t in self.trials),
                              encoding="utf-8")
        return path

    @classmethod
    def load(cls, path):
        return cls(Trial.from_dict(json.loads(l)) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip())


def _match(t, where) -> bool:
    if where is None:
        return True
    if callable(where):
        return bool(where(t))
    return t.case_id in where


def seeds(n: int, base: int = 0) -> list:
    return list(range(base, base + n))


def run_trials(call, cases, trials: int = 10, seed_base: int = 0, group: str = "", graders=(), on_case=None) -> TrialSet:
    """Run every case `trials` times, one fixed seed per trial, in a fixed order (sequential on purpose:
    batching requests on one server can change sampled outputs). on_case(case, TrialSet_of_case) is called
    after each case, e.g. to print a progress row."""
    ts = TrialSet()
    for case in cases:
        part = TrialSet()
        for seed in seeds(trials, seed_base):
            r = call(case, seed)
            part.trials.append(Trial(group, case["id"], seed, r.text, dict(r.usage or {}), r.latency_ms,
                                     _meta(r)))
        part.grade(*graders)
        ts.extend(part)
        if on_case:
            on_case(case, part)
    return ts


def _meta(r) -> dict:
    raw = getattr(r, "raw", None) or {}
    m = {}
    if isinstance(raw, dict) and isinstance(raw.get("atlas"), dict):    # atlas-app's per-turn record
        a = raw["atlas"]
        m = {"request_id": a.get("request_id"), "blocked_by": a.get("blocked_by"), "findings": a.get("findings"),
             "backend_model": a.get("backend_model")}
    calls = getattr(r, "tool_calls", None)
    if calls:
        m["tool_calls"] = [{"name": (c.get("function") or {}).get("name"),
                            "arguments": (c.get("function") or {}).get("arguments")} for c in calls]
    return m
