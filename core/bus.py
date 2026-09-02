"""Lightweight internal event bus for J.A.R.V.I.S. NEO."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import queue
import threading
import time
from typing import Any, Callable

logger = logging.getLogger("JarvisBus")


@dataclass(frozen=True)
class Event:
    """An event transported through the internal NEO bus."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 10
    timestamp: float = field(default_factory=time.time)


Callback = Callable[[Event], None]


class EventBus:
    """Thread-safe priority Pub/Sub bus with one lightweight worker thread."""

    _STOP_EVENT = "_stop_signal_"

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callback]] = {}
        self._queue: queue.PriorityQueue[tuple[int, int, Event]] = queue.PriorityQueue()
        self._lock = threading.RLock()
        self._sequence = 0
        self._running = False
        self._worker_thread: threading.Thread | None = None

    def subscribe(self, event_name: str, callback: Callback) -> None:
        if not event_name or not callable(callback):
            raise ValueError("event_name and callback are required")
        with self._lock:
            handlers = self._subscribers.setdefault(event_name, [])
            if callback not in handlers:
                handlers.append(callback)

    def unsubscribe(self, event_name: str, callback: Callback) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_name)
            if not handlers:
                return
            try:
                handlers.remove(callback)
            except ValueError:
                return
            if not handlers:
                self._subscribers.pop(event_name, None)

    def publish(self, event: Event) -> None:
        # Synchronous delivery before the worker starts keeps the bus useful
        # in simple integrations and unit tests. Once running, publishing is
        # asynchronous and preserves the priority queue semantics.
        with self._lock:
            running = self._running
            if not running:
                handlers = list(self._subscribers.get(event.name, []))
                handlers += list(self._subscribers.get("*", []))
            else:
                self._sequence += 1
                sequence = self._sequence
        if not running:
            for callback in handlers:
                try:
                    callback(event)
                except Exception:
                    logger.exception("Handler failed for event '%s'", event.name)
            return
        self._queue.put((event.priority, sequence, event))

    def emit(self, name: str, payload: dict[str, Any] | None = None, *, priority: int = 10) -> Event:
        event = Event(name=name, payload=payload or {}, priority=priority)
        self.publish(event)
        return event

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(target=self._dispatch_loop, name="jarvis-event-bus", daemon=True)
            self._worker_thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._sequence += 1
            sequence = self._sequence
        self._queue.put((10**9, sequence, Event(name=self._STOP_EVENT)))
        worker = self._worker_thread
        if worker and worker.is_alive():
            worker.join(timeout=timeout)
        self._worker_thread = None

    def _dispatch_loop(self) -> None:
        while True:
            try:
                _, _, event = self._queue.get(timeout=0.5)
            except queue.Empty:
                with self._lock:
                    if not self._running:
                        return
                continue
            try:
                if event.name == self._STOP_EVENT:
                    return
                with self._lock:
                    handlers = list(self._subscribers.get(event.name, []))
                    handlers += list(self._subscribers.get("*", []))
                for callback in handlers:
                    try:
                        callback(event)
                    except Exception:
                        logger.exception("Handler failed for event '%s'", event.name)
            finally:
                self._queue.task_done()


__all__ = ["Event", "EventBus"]
