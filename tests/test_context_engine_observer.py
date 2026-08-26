import threading

from core.bus import Event, EventBus
from core.context_engine import ContextEngine
from core.memory import NeoMemory


def test_system_metric_drives_context_change(tmp_path):
    bus = EventBus()
    memory = NeoMemory(tmp_path / "memory.db")
    engine = ContextEngine(memory=memory)
    engine.attach_to_bus(bus)

    received = []
    done = threading.Event()

    def on_changed(event):
        received.append(event)
        done.set()

    bus.subscribe("context.changed", on_changed)
    bus.start()
    try:
        bus.publish(
            Event(
                name="system.metric",
                payload={
                    "cpu_percent": 42.0,
                    "ram_percent": 50.0,
                    "active_window": "Example",
                    "active_process": "example.exe",
                },
            )
        )
        assert done.wait(1.0)
        assert received[-1].payload == {
            "previous_context": "IDLE",
            "current_context": "ACTIVE",
            "trigger": "example.exe",
        }
    finally:
        engine.detach_from_bus()
        bus.stop()


def test_context_engine_accepts_external_activity_classification(tmp_path):
    bus = EventBus()
    memory = NeoMemory(tmp_path / "memory.db")
    engine = ContextEngine(memory=memory)
    engine.attach_to_bus(bus)

    received = []
    done = threading.Event()

    def on_changed(event):
        received.append(event)
        done.set()

    bus.subscribe("context.changed", on_changed)
    bus.start()
    try:
        bus.publish(
            Event(
                name="app.started",
                payload={"app": "some-game.exe", "activity_type": "gaming"},
            )
        )
        assert done.wait(1.0)
        assert received[-1].payload["current_context"] == "GAMING"
        assert received[-1].payload["trigger"] == "some-game.exe"
    finally:
        engine.detach_from_bus()
        bus.stop()
