"""SQLite in WAL mode, one connection per thread."""
import os
import sqlite3
import threading
import time

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS firm (id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, name TEXT, role TEXT, title TEXT, pin TEXT,
  email TEXT, pw_hash TEXT, reports_to TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS mask_terms (
  id INTEGER PRIMARY KEY, term TEXT NOT NULL UNIQUE COLLATE NOCASE, kind TEXT, source TEXT, added_by TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS matters (id TEXT PRIMARY KEY, name TEXT, parties TEXT);
CREATE TABLE IF NOT EXISTS memberships (user TEXT, matter TEXT, PRIMARY KEY (user, matter));
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY, matter_id TEXT, title TEXT, path TEXT, privileged INTEGER, listed INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS requests (
  id INTEGER PRIMARY KEY, user TEXT, kind TEXT, source TEXT, text TEXT, doc_ids TEXT, prepared_id TEXT,
  destination TEXT, state_at_time TEXT, status TEXT, d1 TEXT, hard_rules TEXT,
  box_in TEXT, box_out TEXT, box_ms INTEGER, box_ok INTEGER, box_checks TEXT,
  cloud_in TEXT, cloud_out_tags TEXT, cloud_out TEXT, cloud_ms INTEGER, keymap TEXT,
  notes TEXT, reply TEXT, label TEXT, shown TEXT, options TEXT, model TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY, user TEXT, kind TEXT, model TEXT, passed INTEGER, request_id INTEGER,
  cleared INTEGER DEFAULT 0, ts REAL);
CREATE TABLE IF NOT EXISTS cloud_evidence (
  id INTEGER PRIMARY KEY, user TEXT, kind TEXT, model TEXT, passed INTEGER, request_id INTEGER,
  cleared INTEGER DEFAULT 0, ts REAL);
CREATE TABLE IF NOT EXISTS row_events (
  id INTEGER PRIMARY KEY, user TEXT, kind TEXT, model TEXT, from_state TEXT, to_state TEXT, reason TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, request_id INTEGER, assignee TEXT, reason TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY, ts REAL, actor TEXT, event TEXT, dest TEXT, sentence TEXT, payload_id INTEGER,
  prev_hash TEXT, hash TEXT);
CREATE TABLE IF NOT EXISTS mask_items (
  id INTEGER PRIMARY KEY, grp TEXT, key TEXT, label TEXT, enabled INTEGER DEFAULT 1,
  added_by TEXT, words TEXT, terms TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS cloud_payloads (
  id INTEGER PRIMARY KEY, request_id INTEGER, ts REAL, user TEXT, system TEXT, user_text TEXT, tags TEXT);
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY, request_id INTEGER, tool TEXT, args TEXT, idempotency_key TEXT, executed INTEGER, ts REAL);
CREATE TABLE IF NOT EXISTS user_models (user TEXT PRIMARY KEY, model TEXT);
CREATE TABLE IF NOT EXISTS try_pointer (user TEXT, kind TEXT, idx INTEGER DEFAULT 0, PRIMARY KEY (user, kind));
"""


def path():
    return os.environ.get("SH_DB", "chamber.db")


def conn():
    """This thread's connection, reopened if SH_DB changed (tests)."""
    db_path = path()
    current = getattr(_local, "conn", None)
    if current is None or _local.path != db_path:
        if current is not None:
            current.close()
        current = sqlite3.connect(db_path, timeout=30, isolation_level=None)
        current.row_factory = sqlite3.Row
        current.execute("PRAGMA journal_mode=WAL")
        current.execute("PRAGMA synchronous=NORMAL")
        current.execute("PRAGMA busy_timeout=30000")
        _local.conn = current
        _local.path = db_path
    return current


def init():
    conn().executescript(SCHEMA)
    have = {c["name"] for c in all("PRAGMA table_info(users)")}
    for column, kind in (("email", "TEXT"), ("pw_hash", "TEXT"), ("reports_to", "TEXT"), ("active", "INTEGER DEFAULT 1")):
        if column not in have:  # a database made before accounts existed
            run(f"ALTER TABLE users ADD COLUMN {column} {kind}")
    run("CREATE UNIQUE INDEX IF NOT EXISTS users_email ON users (email COLLATE NOCASE) WHERE email IS NOT NULL")


def one(sql, *args):
    row = conn().execute(sql, args).fetchone()
    return dict(row) if row else None


def all(sql, *args):  # noqa: A001
    return [dict(r) for r in conn().execute(sql, args).fetchall()]


def run(sql, *args):
    return conn().execute(sql, args).lastrowid


def now():
    return time.time()
