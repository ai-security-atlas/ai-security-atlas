"""Append-only audit log (JSON Lines) of every chat turn: the operator's view of the app.

Written to $ATLAS_APP_DATA/audit.jsonl (a named volume in compose). It records the context
shape the model received (roles and sizes, not the system prompt text), the reply, the
policy findings and what the app did about them (defense-logging).
"""
import json
import os
import threading
from pathlib import Path

PATH = Path(os.environ.get("ATLAS_APP_DATA", "/data")) / "audit.jsonl"
_lock = threading.Lock()


def append(entry: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with _lock, PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def tail(n: int = 50, session: str = None) -> list:
    if not PATH.exists():
        return []
    with _lock:
        rows = [json.loads(l) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    if session:
        rows = [r for r in rows if r.get("session") == session]
    return rows[-n:] if n > 0 else rows


def reset() -> int:
    with _lock:
        n = len(PATH.read_text(encoding="utf-8").splitlines()) if PATH.exists() else 0
        if PATH.exists():
            PATH.unlink()
    return n
