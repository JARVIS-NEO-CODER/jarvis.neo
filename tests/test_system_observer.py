import threading

from core.bus import Event, EventBus
from core.system_observer import SystemObserver


def test_snapshot_is_structured():
    bus = EventBus()
    observer = SystemObserver(bus, interval=0.25)

    snapshot = observer.snapshot()

    assert snapshot.timestamp > 0
    assert snapshot.cpu_percent is None or 0.0 <= snapshot.cpu_percent <= 100.0
    assert snapshot.ram_percent is None or 0.0 <= snapshot.ram_percent <= 100.0


def test_observer_snapshot_can_be_published():
    bus = EventBus()
    observer = SystemObserver(bus, interval=0.25)
    received = []
    done = threading.Event()

    def handler(event):
        received.append(event)
        done.set()

    bus.subscribe("system.metric", handler)
    bus.start()
    try:
        snapshot = observer.snapshot()
        bus.publish(Event(name="system.metric", payload={
            "timestamp": snapshot.timestamp,
            "cpu_percent": snapshot.cpu_percent,
            "ram_percent": snapshot.ram_percent,
            "active_window": snapshot.active_window,
            "active_process": snapshot.active_process,
        }))
        assert done.wait(1.0)
        assert len(received) == 1
        assert received[0].name == "system.metric"
        assert "active_process" in received[0].payload
    finally:
        observer.stop()
        bus.stop()
