import threading

from core.action_engine import ActionResult
from core.automation import AutomationEngine, AutomationRule
from core.bus import Event, EventBus


class FakeActions:
    def __init__(self):
        self.executed = []

    def execute(self, action_name, **kwargs):
        self.executed.append((action_name, kwargs))
        return ActionResult(action_name, True, "test action", verified=True)


def test_automation_engine_reacts_to_context_changed_and_detaches():
    bus = EventBus()
    actions = FakeActions()
    automation = AutomationEngine(actions)
    automation.register_rule(
        AutomationRule(
            name="gaming-test",
            context="GAMING",
            minimum_confidence=0.5,
            action="enable_gaming_mode",
            cooldown_seconds=0,
        )
    )
    automation.attach_to_bus(bus)
    bus.start()
    executed = threading.Event()

    original_execute = actions.execute

    def execute_and_signal(action_name, **kwargs):
        result = original_execute(action_name, **kwargs)
        executed.set()
        return result

    actions.execute = execute_and_signal

    try:
        bus.publish(
            Event(
                name="context.changed",
                payload={
                    "previous_context": "IDLE",
                    "current_context": "GAMING",
                    "trigger": "ets2.exe",
                },
            )
        )

        assert executed.wait(1.0)
        assert actions.executed == [("enable_gaming_mode", {})]

        automation.detach_from_bus()
        executed.clear()
        bus.publish(
            Event(
                name="context.changed",
                payload={
                    "previous_context": "IDLE",
                    "current_context": "GAMING",
                    "trigger": "ets2.exe",
                },
            )
        )
        assert not executed.wait(0.2)
        assert actions.executed == [("enable_gaming_mode", {})]
    finally:
        automation.detach_from_bus()
        bus.stop()
