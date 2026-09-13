"""Legacy SQLite memory adapter kept compatible with the historical assistant runtime."""
from __future__ import annotations

import datetime
import time
from pathlib import Path


class MemoryManager:
    def __init__(self, path: Path):
        import sqlite3
        self.sqlite3 = sqlite3
        self.path = path
        self._init_db()

    def _init_db(self):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, status TEXT DEFAULT 'pending', timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS memos (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, filepath TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, event_text TEXT, event_time DATETIME, status TEXT DEFAULT 'pending', timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS macros (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, actions TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS retro_vision (id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT, summary TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, content TEXT NOT NULL, importance INTEGER DEFAULT 1, tags TEXT DEFAULT '', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)")
            conn.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL, due_at REAL NOT NULL, repeat_seconds INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, fired_at DATETIME)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(status, due_at)")
            conn.execute("CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, message TEXT, level TEXT DEFAULT 'INFO', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.commit()

    def add_message(self, role: str, content: str):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
            conn.commit()

    def get_history(self, limit=20):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
            return [{"role": r[0], "content": r[1]} for r in reversed(cursor.fetchall())]

    def add_note(self, title, content):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO notes (title, content) VALUES (?, ?)", (title, content))
            conn.commit()

    def get_last_notes(self, limit=3):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT content FROM notes ORDER BY id DESC LIMIT ?", (limit,))
            return [r[0] for r in cursor.fetchall()]

    def add_task(self, content):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO tasks (content) VALUES (?)", (content,))
            conn.commit()

    def get_tasks(self):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT id, content FROM tasks WHERE status = 'pending' ORDER BY id ASC")
            return cursor.fetchall()

    def complete_task(self, task_id):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
            conn.commit()

    def add_memo(self, content, filepath):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO memos (content, filepath) VALUES (?, ?)", (content, str(filepath)))
            conn.commit()

    def get_memos(self, limit=5):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT content, timestamp FROM memos ORDER BY id DESC LIMIT ?", (limit,))
            return cursor.fetchall()

    def add_agenda_event(self, event_text, event_time_str):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO agenda (event_text, event_time) VALUES (?, ?)", (event_text, event_time_str))
            conn.commit()

    def get_agenda_events(self):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT id, event_text, event_time FROM agenda WHERE status = 'pending' ORDER BY event_time ASC")
            return cursor.fetchall()

    def save_macro(self, name, actions_list):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT OR REPLACE INTO macros (name, actions) VALUES (?, ?)", (name.lower(), json.dumps(actions_list)))
            conn.commit()

    def get_macro(self, name):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT actions FROM macros WHERE name = ?", (name.lower(),))
            res = cursor.fetchone()
            return json.loads(res[0]) if res else None

    def list_macros(self):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT name FROM macros ORDER BY name ASC")
            return [row[0] for row in cursor.fetchall()]

    def add_retro_vision(self, filepath, summary):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO retro_vision (filepath, summary) VALUES (?, ?)", (str(filepath), summary))
            conn.commit()

    def get_recent_retro_vision(self, limit=5):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute("SELECT summary, timestamp FROM retro_vision ORDER BY id DESC LIMIT ?", (limit,))
            return cursor.fetchall()

    def remember(self, content, kind="semantic", importance=1, tags=""):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO memories (kind, content, importance, tags) VALUES (?, ?, ?, ?)", (kind, content, importance, tags))

    def search_memory(self, query, limit=8):
        term = f"%{query.strip()}%"
        with self.sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT kind, content, created_at FROM memories WHERE content LIKE ? OR tags LIKE ? ORDER BY importance DESC, id DESC LIMIT ?", (term, term, limit)).fetchall()
            history = conn.execute("SELECT role, content, timestamp FROM messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?", (term, limit)).fetchall()
        return [{"kind": r[0], "content": r[1], "timestamp": r[2]} for r in rows] + [{"kind": "conversation", "content": f"{r[0]}: {r[1]}", "timestamp": r[2]} for r in history]

    def add_reminder(self, task, due_at, repeat_seconds=0):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO reminders (task, due_at, repeat_seconds) VALUES (?, ?, ?)", (task, due_at, repeat_seconds))

    def due_reminders(self, now):
        with self.sqlite3.connect(self.path) as conn:
            return conn.execute("SELECT id, task, due_at, repeat_seconds FROM reminders WHERE status='pending' AND due_at <= ?", (now,)).fetchall()

    def mark_reminder_fired(self, reminder_id, repeat_seconds=0, now=None):
        now = now or time.time()
        with self.sqlite3.connect(self.path) as conn:
            if repeat_seconds:
                conn.execute("UPDATE reminders SET due_at=?, fired_at=? WHERE id=?", (now + repeat_seconds, datetime.datetime.now().isoformat(), reminder_id))
            else:
                conn.execute("UPDATE reminders SET status='done', fired_at=? WHERE id=?", (datetime.datetime.now().isoformat(), reminder_id))

    def log_activity(self, category, message, level="INFO"):
        with self.sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO activity_log (category, message, level) VALUES (?, ?, ?)", (category, message, level))

    def get_timeline_events(self, limit=20):
        with self.sqlite3.connect(self.path) as conn:
            cursor = conn.execute(
                "SELECT category, message, level, created_at FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
            )
            return cursor.fetchall()


__all__ = ["MemoryManager"]
