"""SQLite event logger for G-Vox.

This module is intentionally isolated from recognition/control logic.
It only persists log records in a local SQLite database.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional


class SQLiteLogger:
    """Thread-safe SQLite logger used by the UI/controller layers."""

    def __init__(self, db_path: Optional[Path] = None):
        self._lock = threading.Lock()
        self._db_path = db_path or self._default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _default_db_path(self) -> Path:
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "G-Vox" / "gvox_logs.db"
        return Path.cwd() / "logs" / "gvox_logs.db"

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), timeout=5, check_same_thread=False)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS event_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        source TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_created_at ON event_logs(created_at)"
                )
                conn.commit()
            finally:
                conn.close()

    def log_event(self, source: str, message: str, level: str = "INFO") -> None:
        text = (message or "").strip()
        if not text:
            return

        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO event_logs (created_at, source, level, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    (now, source or "app", level or "INFO", text),
                )
                conn.commit()
            finally:
                conn.close()

    @property
    def db_path(self) -> Path:
        return self._db_path
