"""Local memory layer for J.A.R.V.I.S. NEO.

This module owns SQLite access so other NEO components do not need to know
about the database schema. It stores three deliberately separate categories:
- events: raw, time-stamped observations
- system_states: sampled/aggregated machine state
- facts: longer-lived conclusions, preferences, and learned habits

No AI/network dependency is required here.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DB = Path.home() / ".jarvis_neo" / "neo_memory.db"


class NeoMemory:
    """Small, local, thread-safe-enough SQLite repository for NEO memory."""

    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT,
                    message TEXT NOT NULL,
                    metadata TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_kind
                    ON events(kind);

                CREATE TABLE IF NOT EXISTS system_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_percent REAL,
                    ram_percent REAL,
                    gpu_percent REAL,
                    disk_percent REAL,
                    temperature_c REAL,
                    metadata TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_system_states_timestamp
                    ON system_states(timestamp);

                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source TEXT,
                    UNIQUE(category, key)
                );

                CREATE INDEX IF NOT EXISTS idx_facts_category
                    ON facts(category);
                """
            )

    @staticmethod
    def _now() -> float:
        return time.time()

    def record_event(
        self,
        kind: str,
        message: str,
        *,
        source: str | None = None,
        metadata: str | None = None,
        timestamp: float | None = None,
    ) -> int:
        """Store one raw observation and return its database id."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO events(timestamp, kind, source, message, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp or self._now(), kind, source, message, metadata),
            )
            return int(cur.lastrowid)

    def recent_events(
        self,
        *,
        limit: int = 100,
        kind: str | None = None,
        since: float | None = None,
    ) -> list[dict[str, Any]]:
        """Return newest events first."""
        limit = max(1, min(int(limit), 5000))
        clauses: list[str] = []
        params: list[Any] = []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(float(since))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_system_state(
        self,
        *,
        cpu_percent: float | None = None,
        ram_percent: float | None = None,
        gpu_percent: float | None = None,
        disk_percent: float | None = None,
        temperature_c: float | None = None,
        metadata: str | None = None,
        timestamp: float | None = None,
    ) -> int:
        """Store a sampled machine state."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO system_states(
                    timestamp, cpu_percent, ram_percent, gpu_percent,
                    disk_percent, temperature_c, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp or self._now(),
                    cpu_percent,
                    ram_percent,
                    gpu_percent,
                    disk_percent,
                    temperature_c,
                    metadata,
                ),
            )
            return int(cur.lastrowid)

    def recent_system_states(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM system_states ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def remember_fact(
        self,
        category: str,
        key: str,
        value: str,
        *,
        confidence: float = 1.0,
        source: str | None = None,
    ) -> int:
        """Create or update a durable fact/preference/habit."""
        confidence = max(0.0, min(float(confidence), 1.0))
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO facts(created_at, updated_at, category, key, value,
                                  confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source = excluded.source
                """,
                (now, now, category, key, value, confidence, source),
            )
            row = conn.execute(
                "SELECT id FROM facts WHERE category = ? AND key = ?",
                (category, key),
            ).fetchone()
        return int(row["id"])

    def get_facts(
        self,
        *,
        category: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        clauses = ["confidence >= ?"]
        params: list[Any] = [float(min_confidence)]
        if category:
            clauses.append("category = ?")
            params.append(category)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM facts WHERE {' AND '.join(clauses)} "
                "ORDER BY confidence DESC, updated_at DESC",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def forget_fact(self, fact_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM facts WHERE id = ?", (int(fact_id),))
            return cur.rowcount > 0

    def cleanup(self, *, events_older_than_days: int = 30, states_older_than_days: int = 7) -> dict[str, int]:
        """Remove old high-volume observations while keeping durable facts."""
        now = self._now()
        event_cutoff = now - max(1, int(events_older_than_days)) * 86400
        state_cutoff = now - max(1, int(states_older_than_days)) * 86400
        with self._connect() as conn:
            events = conn.execute(
                "DELETE FROM events WHERE timestamp < ?", (event_cutoff,)
            ).rowcount
            states = conn.execute(
                "DELETE FROM system_states WHERE timestamp < ?", (state_cutoff,)
            ).rowcount
        return {"events_deleted": events, "system_states_deleted": states}

    def close(self) -> None:
        """Reserved for API symmetry; connections are short-lived per operation."""
        return None


__all__ = ["NeoMemory", "DEFAULT_DB"]
