"""Rates and confidence intervals (stdlib only).

A success rate is k successes out of n trials. Report it with an interval, never as a bare percentage:

    r = Rate(7, 10)            # or Rate.of([True, False, ...])
    r.p, r.lo, r.hi            # 0.7, 0.397, 0.892  (Wilson 95 %)
    r.fmt()                    # '7/10 70% [40-89%]'
    bootstrap_ci([1, 0, 1])    # percentile bootstrap of the mean, seeded
    diff_ci(a, b)              # (a.p - b.p, lo, hi): Newcombe interval for a difference of two rates
"""
import math
import random

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple:
    """Wilson score interval for k/n. n == 0 gives (0, 1): no data, no claim."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def bootstrap_ci(values, stat=None, n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> tuple:
    """Percentile bootstrap interval of stat(values) (default: the mean). Seeded, so it is repeatable.
    For a 0/1 list with k = 0 or k = n it collapses to a point: use wilson() for the headline number."""
    vals = list(values)
    if not vals:
        return 0.0, 1.0
    stat = stat or (lambda xs: sum(xs) / len(xs))
    rng = random.Random(seed)
    n = len(vals)
    boots = sorted(stat([vals[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    lo = boots[int(math.floor(alpha / 2 * n_boot))]
    hi = boots[min(n_boot - 1, int(math.ceil((1 - alpha / 2) * n_boot)) - 1)]
    return float(lo), float(hi)


class Rate:
    """k successes out of n, with a Wilson 95 % interval."""

    __slots__ = ("k", "n")

    def __init__(self, k: int, n: int):
        self.k, self.n = int(k), int(n)

    @classmethod
    def of(cls, outcomes):
        outcomes = [bool(x) for x in outcomes]
        return cls(sum(outcomes), len(outcomes))

    @property
    def p(self) -> float:
        return self.k / self.n if self.n else 0.0

    @property
    def lo(self) -> float:
        return wilson(self.k, self.n)[0]

    @property
    def hi(self) -> float:
        return wilson(self.k, self.n)[1]

    def __add__(self, other):
        return Rate(self.k + other.k, self.n + other.n)

    def fmt(self, ci: bool = True) -> str:
        s = f"{self.k}/{self.n} {100 * self.p:.0f}%"
        return f"{s} [{100 * self.lo:.0f}-{100 * self.hi:.0f}%]" if ci else s

    def to_dict(self) -> dict:
        return {"k": self.k, "n": self.n, "p": round(self.p, 4), "lo": round(self.lo, 4), "hi": round(self.hi, 4)}

    def __repr__(self):
        return f"Rate({self.k}, {self.n})"


def diff_ci(a: Rate, b: Rate) -> tuple:
    """Difference a.p - b.p with Newcombe's hybrid score 95 % interval (method 10, independent samples).
    Use it for "attack lift over the no-attack baseline" and "ASR drop from a defense"."""
    l1, u1 = a.lo, a.hi
    l2, u2 = b.lo, b.hi
    d = a.p - b.p
    lo = d - math.sqrt((a.p - l1) ** 2 + (u2 - b.p) ** 2)
    hi = d + math.sqrt((u1 - a.p) ** 2 + (b.p - l2) ** 2)
    return d, max(-1.0, lo), min(1.0, hi)


def percentile(values, q: float) -> float:
    """Nearest-rank percentile (q in [0, 100]) of a list of numbers; 0.0 for an empty list."""
    vals = sorted(values)
    if not vals:
        return 0.0
    i = max(0, min(len(vals) - 1, int(math.ceil(q / 100 * len(vals))) - 1))
    return float(vals[i])
