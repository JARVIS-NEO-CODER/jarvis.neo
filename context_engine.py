"""NEO Context Engine: local-first observation and habit learning.

No LLM calls are made here. The engine samples lightweight Windows process/time
signals, stores only compact events, and learns recurring contexts from history.
It is intentionally independent from assistant.py so it can run continuously.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Callable, Optional

try:
    import psutil
except Exception:
    psutil = None

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "neo_context.db"
STATE_PATH = ROOT / "neo_context_state.json"

GAMING_PROCESSES = {
    "eurotrucks2.exe", "ets2.exe", "steam.exe", "robloxplayerbeta.exe",
    "minecraft.exe", "javaw.exe", "minecraftlauncher.exe", "valorant.exe",
    "fortniteclient-win64-shipping.exe", "gta5.exe", "r5apex.exe"
}


class ContextEngine:
    def __init__(self, on_context: Optional[Callable[[str, float, str], None]] = None):
        self.on_context = on_context
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        con = sqlite3.connect(DB_PATH, timeout=5)
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _init_db(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, ts REAL NOT NULL, kind TEXT NOT NULL,
                value TEXT NOT NULL, context TEXT, confidence REAL DEFAULT 0
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS feedback(
                id INTEGER PRIMARY KEY, ts REAL NOT NULL, context TEXT NOT NULL,
                accepted INTEGER NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS mode_history(
                id INTEGER PRIMARY KEY, ts REAL NOT NULL, mode TEXT NOT NULL,
                source TEXT NOT NULL
            )""")

    @staticmethod
    def _processes() -> set[str]:
        if psutil is None:
            return set()
        result = set()
        try:
            for p in psutil.process_iter(["name"]):
                name = (p.info.get("name") or "").lower()
                if name:
                    result.add(name)
        except Exception:
            pass
        return result

    def _record(self, kind: str, value: str, context: str = "", confidence: float = 0):
        with self._connect() as con:
            con.execute(
                "INSERT INTO events(ts,kind,value,context,confidence) VALUES(?,?,?,?,?)",
                (time.time(), kind, value, context, confidence),
            )
            con.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 5000)")

    def record_mode(self, mode: str, source: str = "manual"):
        mode = mode.strip().lower()
        if not mode:
            return
        with self._connect() as con:
            con.execute("INSERT INTO mode_history(ts,mode,source) VALUES(?,?,?)", (time.time(), mode, source))
        self._record("mode", mode, mode, 1.0)

    def feedback(self, context: str, accepted: bool):
        with self._connect() as con:
            con.execute(
                "INSERT INTO feedback(ts,context,accepted) VALUES(?,?,?)",
                (time.time(), context, int(accepted)),
            )

    def _habit_score(self, context: str, hour: int, weekday: int) -> float:
        with self._connect() as con:
            rows = con.execute(
                "SELECT ts FROM mode_history WHERE mode=? AND source='manual' ORDER BY ts DESC LIMIT 1000",
                (context,),
            ).fetchall()
            feedback = con.execute(
                "SELECT accepted FROM feedback WHERE context=? ORDER BY id DESC LIMIT 30",
                (context,),
            ).fetchall()
        if not rows:
            return 0.0

        matches = 0
        for (ts,) in rows:
            local = time.localtime(ts)
            hour_distance = min(abs(local.tm_hour - hour), 24 - abs(local.tm_hour - hour))
            if hour_distance <= 1 and local.tm_wday == weekday:
                matches += 1
        base = min(0.85, matches / 6.0)
        if feedback:
            ratio = sum(int(x[0]) for x in feedback) / len(feedback)
            base *= 0.55 + 0.45 * ratio
        return round(min(base, 0.99), 3)

    def _detect(self):
        now = time.localtime()
        processes = self._processes()
        gaming_apps = sorted(processes & GAMING_PROCESSES)
        gaming_signal = bool(gaming_apps)
        hour_score = self._habit_score("gaming", now.tm_hour, now.tm_wday)

        # A running game is a strong signal; learned schedule/context raises it.
        confidence = min(0.99, (0.78 if gaming_signal else 0.0) + (0.22 * hour_score))
        context = "gaming" if gaming_signal or hour_score >= 0.72 else "unknown"
        reason = ", ".join(gaming_apps[:3]) if gaming_apps else "habitude horaire"
        return context, confidence, reason

    def snapshot(self):
        context, confidence, reason = self._detect()
        self._record("context", context, context, confidence)
        state = {
            "ts": time.time(), "context": context, "confidence": confidence,
            "reason": reason, "gaming": context == "gaming"
        }
        try:
            STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return state

    def start(self, interval: float = 15.0):
        if self.thread and self.thread.is_alive():
            return self
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(interval,), daemon=True, name="NEO-Context")
        self.thread.start()
        return self

    def stop(self):
        self.stop_event.set()

    def _run(self, interval: float):
        previous = None
        while not self.stop_event.is_set():
            try:
                state = self.snapshot()
                key = (state["context"], state["confidence"] >= 0.72)
                if key != previous:
                    previous = key
                    if self.on_context:
                        self.on_context(state["context"], state["confidence"], state["reason"])
            except Exception as exc:
                self._record("error", str(exc), "context")
            self.stop_event.wait(interval)


if __name__ == "__main__":
    engine = ContextEngine(lambda c, s, r: print(f"NEO context: {c} ({s:.0%}) — {r}"))
    print("NEO Context Engine actif. Ctrl+C pour arrêter.")
    try:
        engine.start()
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        engine.stop()
