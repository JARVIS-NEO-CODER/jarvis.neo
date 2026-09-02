import threading

from core.bus import Event, EventBus
from core.context_engine import ContextEngine


class DummyMemory:
    pass


def test_context_engine_publishes_external_gaming_context_and_detaches():
    bus = EventBus()
    context_engine = ContextEngine(bus, DummyMemory())
    received = []
    changed = threading.Event()

    def on_context_changed(event):
        received.append(event)
        changed.set()

    bus.subscribe("context.changed", on_context_changed)
    context_engine.attach_to_bus()
    bus.start()

    try:
        bus.publish(
            Event(
                name="app.started",
                payload={"app": "ets2.exe", "activity_type": "gaming"},
            )
        )

        assert changed.wait(1.0)
        assert len(received) == 1
        assert received[0].payload == {
            "previous_context": "IDLE",
            "current_context": "GAMING",
            "trigger": "ets2.exe",
        }
        assert received[0].priority == 5
        assert context_engine.current_context == "GAMING"

        context_engine.detach_from_bus()
        changed.clear()
        bus.publish(
            Event(
                name="app.started",
                payload={"app": "ets2.exe", "activity_type": "gaming"},
            )
        )
        assert not changed.wait(0.2)
        assert len(received) == 1
        assert context_engine.current_context == "GAMING"
    finally:
        context_engine.detach_from_bus()
        bus.stop()
