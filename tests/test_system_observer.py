from core.bus import EventBus
from core.system_observer import SystemObserver


def test_snapshot_is_structured():
    bus = EventBus()
    observer = SystemObserver(bus, interval=0.25)

    snapshot = observer.snapshot()

    assert snapshot.timestamp > 0
    assert snapshot.cpu_percent is None or 0.0 <= snapshot.cpu_percent <= 100.0
    assert snapshot.ram_percent is None or 0.0 <= snapshot.ram_percent <= 100.0


def test_observer_publishes_system_metric():
    bus = EventBus()
    observer = SystemObserver(bus, interval=0.25)
    received = []
    bus.subscribe("system.metric", received.append)
    bus.start()

    try:
        observer._running = True
        snapshot = observer.snapshot()
        bus.publish(__import__("core.bus", fromlist=["Event"]).Event(
            name="system.metric",
            payload={
                "timestamp": snapshot.timestamp,
                "cpu_percent": snapshot.cpu_percent,
                "ram_percent": snapshot.ram_percent,
                "active_window": snapshot.active_window,
                "active_process": snapshot.active_process,
            },
        ))
        assert bus._queue.get(timeout=1.0) is not None
    finally:
        observer.stop()
        bus.stop()
