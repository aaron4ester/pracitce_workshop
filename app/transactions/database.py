"""Database connection helpers for the transaction ledger.

Why SQLite?  It ships with Python, needs no server, and the project document
still lists MySQL as "to be confirmed".  All SQL in this package is written in
the portable subset both SQLite and MySQL understand, so switching later means
replacing `connect()` and loading /schema.sql instead of schema_sqlite.sql.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Request

DEFAULT_DB_PATH = os.environ.get("BANK_DB_PATH", "bank.db")
SCHEMA_PATH = Path(__file__).with_name("schema_sqlite.sql")


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection that returns dict-like rows and enforces foreign keys."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create the tables if they do not exist yet (safe to call on every start)."""
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per HTTP request, always closed afterwards."""
    db_path = getattr(request.app.state, "db_path", DEFAULT_DB_PATH)
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()
