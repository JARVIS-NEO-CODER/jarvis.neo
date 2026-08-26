import threading

from core.bus import Event, EventBus
from core.memory import NeoMemory


def test_event_bus_persists_event_to_sqlite(tmp_path):
    db_path = tmp_path / "memory.db"
    memory = NeoMemory(db_path)
    bus = EventBus()
    written = threading.Event()

    original_record_event = memory.record_event

    def record_and_signal(*args, **kwargs):
        result = original_record_event(*args, **kwargs)
        written.set()
        return result

    memory.record_event = record_and_signal
    memory.attach_to_bus(bus)
    bus.start()

    try:
        bus.publish(
            Event(
                name="app.started",
                payload={"app": "ets2.exe"},
                priority=10,
            )
        )
        assert written.wait(1.0)

        events = memory.recent_events(limit=10, kind="app.started")
        assert len(events) == 1
        assert events[0]["kind"] == "app.started"
        assert events[0]["source"] == "event_bus"
        assert '"app": "ets2.exe"' in events[0]["metadata"]
    finally:
        bus.stop()
        memory.close()
