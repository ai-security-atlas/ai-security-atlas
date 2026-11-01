"""Durable agent memory for worlds that set persist_memory (LAB-29).

Keyed by world id and principal. The file is $ATLAS_APP_DATA/memory.sqlite, the same
volume as the audit log, so it survives a process restart. Worlds that leave
persist_memory false never open this file: their notes still live only on the run's State.

A row records the note the tool saved plus who it belongs to. source is "tool" when the
same run had already called http_get, and "user" otherwise. url is the last fetched page.
expires is an ISO date; an empty expires means the row does not age out. read_memory skips
a row whose expires is before today. The admin routes in app.py reset, expire and list rows.
"""
import os
import sqlite3
import threading
from datetime import date, datetime, timezone
from pathlib import Path

PATH = Path(os.environ.get("ATLAS_APP_DATA", "/data")) / "memory.sqlite"
_lock = threading.Lock()

_COLUMNS = ("id", "world", "principal", "note", "source", "url", "session", "created", "expires")


def _init(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS memory ("
        "id INTEGER PRIMARY KEY, world TEXT NOT NULL, principal TEXT NOT NULL, note TEXT NOT NULL, "
        "source TEXT NOT NULL, url TEXT NOT NULL, session TEXT NOT NULL, created TEXT NOT NULL, "
        "expires TEXT NOT NULL)"
    )
    con.execute("CREATE INDEX IF NOT EXISTS memory_key ON memory(world, principal)")


def _connect():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(PATH, timeout=5, check_same_thread=False)
    con.row_factory = sqlite3.Row
    _init(con)
    return con


def _row(record):
    return {k: record[k] for k in _COLUMNS}


def _live(record, today):
    exp = record["expires"]
    return not exp or exp >= today


def rows(world=None, principal=None, source=None, include_expired=True):
    """Rows in id order. world, principal and source are optional filters."""
    if not PATH.exists():
        return []
    today = date.today().isoformat()
    with _lock:
        con = _connect()
        try:
            found = [_row(r) for r in con.execute("SELECT * FROM memory ORDER BY id")]
        finally:
            con.close()
    if world is not None:
        found = [r for r in found if r["world"] == world]
    if principal is not None:
        found = [r for r in found if r["principal"] == principal]
    if source is not None:
        found = [r for r in found if r["source"] == source]
    if not include_expired:
        found = [r for r in found if _live(r, today)]
    return found


def append(world, principal, note, source, url, session, expires=""):
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _lock:
        con = _connect()
        try:
            cur = con.execute(
                "INSERT INTO memory (world, principal, note, source, url, session, created, expires) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (world, principal, note, source, url or "", session or "", created, expires or ""),
            )
            con.commit()
            record = con.execute("SELECT * FROM memory WHERE id = ?", (cur.lastrowid,)).fetchone()
            return _row(record)
        finally:
            con.close()


def reset(world=None, principal=None, source=None) -> int:
    """Delete matching rows. No filter deletes every row. Missing file removes nothing."""
    if not PATH.exists():
        return 0
    clauses, args = [], []
    if world is not None:
        clauses.append("world = ?")
        args.append(world)
    if principal is not None:
        clauses.append("principal = ?")
        args.append(principal)
    if source is not None:
        clauses.append("source = ?")
        args.append(source)
    sql = "DELETE FROM memory" + (" WHERE " + " AND ".join(clauses) if clauses else "")
    with _lock:
        con = _connect()
        try:
            cur = con.execute(sql, args)
            con.commit()
            return cur.rowcount
        finally:
            con.close()


def expire(world, principal, expires, source=None) -> int:
    """Set expires on matching rows. world and principal are required by the caller."""
    if not PATH.exists():
        return 0
    clauses = ["world = ?", "principal = ?"]
    args = [expires, world, principal]
    if source is not None:
        clauses.append("source = ?")
        args.append(source)
    sql = "UPDATE memory SET expires = ? WHERE " + " AND ".join(clauses)
    with _lock:
        con = _connect()
        try:
            cur = con.execute(sql, args)
            con.commit()
            return cur.rowcount
        finally:
            con.close()
