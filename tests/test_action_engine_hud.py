from core.action_engine import ActionEngine
from core.bus import EventBus


class DummyMemory:
    def __init__(self):
        self.events = []

    def record_event(self, *args, **kwargs):
        self.events.append((args, kwargs))


def test_show_hud_publishes_safe_event():
    bus = EventBus()
    memory = DummyMemory()
    engine = ActionEngine(memory=memory, event_bus=bus)
    received = []

    bus.subscribe("hud.show", received.append)
    bus.start()
    try:
        result = engine.execute(
            "action.show_hud",
            target="system_monitor",
            reason="context_changed",
        )

        assert result.success is True
        assert result.verified is True

        event = None
        import time
        deadline = time.time() + 1.0
        while time.time() < deadline and not received:
            time.sleep(0.01)
        if received:
            event = received[0]

        assert event is not None
        assert event.name == "hud.show"
        assert event.payload == {
            "target": "system_monitor",
            "reason": "context_changed",
        }
        assert event.priority == 10
    finally:
        bus.stop()


def test_show_hud_rejects_unknown_target():
    engine = ActionEngine(memory=DummyMemory(), event_bus=EventBus())

    result = engine.execute("action.show_hud", target="unknown_view")

    assert result.success is False
    assert "HUD target inconnu" in result.message
