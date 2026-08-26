import threading

from core.action_engine import ActionEngine
from core.automation import AutomationEngine
from core.bus import EventBus
from core.context_engine import ContextEngine
from core.hud_bridge import HudBridge
from core.runtime import NeoRuntime


def test_runtime_attach_detach_wires_hud():
    bus = EventBus()
    hud_events = []
    received = threading.Event()
    hud = HudBridge(lambda payload: (hud_events.append(payload), received.set()))
    runtime = NeoRuntime(
        bus,
        ContextEngine(),
        AutomationEngine(ActionEngine(event_bus=bus)),
        hud,
    )

    runtime.attach()
    bus.start()
    try:
        bus.emit("hud.show", {"target": "context"})
        assert received.wait(1.0)
        assert hud_events == [{"target": "context"}]
        assert runtime.attached
    finally:
        runtime.detach()
        bus.stop()

    assert not runtime.attached
