from core.action_engine import ActionEngine
from core.bus import EventBus


def test_safe_actions_publish_events():
    bus = EventBus()
    engine = ActionEngine(event_bus=bus)
    received = []

    bus.subscribe("notification.show", received.append)
    bus.subscribe("state.changed", received.append)
    bus.subscribe("neo.test", received.append)

    engine.execute("action.notify", message="hello")
    engine.execute("action.set_state", key="mode", value="GAMING")
    engine.execute("action.publish_event", event_name="neo.test", payload={"ok": True})

    assert len(received) == 3
