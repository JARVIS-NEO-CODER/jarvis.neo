"""NEO Context Engine: local-first context and habit learning.

No generative AI calls are made here. It records only explicitly supplied events,
learns lightweight patterns, and emits context suggestions for the UI/action layer.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path

@dataclass
class ContextEvent:
    kind: str
    value: str
    timestamp: str
    metadata: dict

class ContextEngine:
    def __init__(self, storage: str | Path):
        self.storage = Path(storage)
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[ContextEvent] = []
        self.patterns: dict[str, dict] = {}
        self.paused = False
        self._load()

    def _load(self):
        if not self.storage.exists():
            return
        try:
            data = json.loads(self.storage.read_text(encoding="utf-8"))
            self.events = [ContextEvent(**x) for x in data.get("events", [])]
            self.patterns = data.get("patterns", {})
        except Exception:
            self.events, self.patterns = [], {}

    def _save(self):
        self.storage.write_text(json.dumps({"events":[asdict(x) for x in self.events[-5000:]], "patterns":self.patterns}, ensure_ascii=False, indent=2), encoding="utf-8")

    def record(self, kind: str, value: str, metadata: dict | None = None, now: datetime | None = None):
        if self.paused:
            return
        now = now or datetime.now()
        self.events.append(ContextEvent(kind, value, now.isoformat(), metadata or {}))
        self._learn(kind, value, now)
        self._save()

    def _learn(self, kind: str, value: str, now: datetime):
        key = f"{kind}:{value}"
        p = self.patterns.setdefault(key, {"count": 0, "hours": {}, "weekdays": {}})
        p["count"] += 1
        h, d = str(now.hour), str(now.weekday())
        p["hours"][h] = p["hours"].get(h, 0) + 1
        p["weekdays"][d] = p["weekdays"].get(d, 0) + 1

    def suggest(self, context: dict, now: datetime | None = None) -> list[dict]:
        if self.paused:
            return []
        now = now or datetime.now()
        suggestions = []
        for key, p in self.patterns.items():
            if p.get("count", 0) < 3 or ":" not in key:
                continue
            kind, value = key.split(":", 1)
            hour_score = p.get("hours", {}).get(str(now.hour), 0) / max(1, p["count"])
            if hour_score >= 0.30 and context.get(kind) == value:
                suggestions.append({"context": value, "confidence": round(min(0.99, 0.55 + hour_score * 0.4), 2), "reason": f"habitude détectée à cette heure"})
        return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)

    def feedback(self, context: str, accepted: bool):
        for key, p in self.patterns.items():
            if key.endswith(":" + context):
                p["count"] = max(0, p.get("count", 0) + (1 if accepted else -2))
        self._save()

    def set_paused(self, paused: bool):
        self.paused = paused
