import threading
import time

from core.bus import Event, EventBus


def wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_subscribe_and_publish():
    bus = EventBus()
    received = []
    done = threading.Event()

    bus.subscribe("app.started", lambda event: (received.append(event), done.set()))
    bus.start()
    try:
        bus.publish(Event(name="app.started", payload={"app": "ets2.exe"}))
        assert done.wait(1.0)
        assert len(received) == 1
        assert received[0].payload["app"] == "ets2.exe"
    finally:
        bus.stop()


def test_priority_ordering():
    bus = EventBus()
    received = []
    done = threading.Event()

    def handler(event):
        received.append(event.name)
        if len(received) == 2:
            done.set()

    bus.subscribe("low", handler)
    bus.subscribe("high", handler)
    bus.start()
    try:
        bus.publish(Event(name="low", priority=20))
        bus.publish(Event(name="high", priority=0))
        assert done.wait(1.0)
        assert received == ["high", "low"]
    finally:
        bus.stop()


def test_same_priority_sequence():
    bus = EventBus()
    received = []
    done = threading.Event()

    def handler(event):
        received.append(event.payload["index"])
        if len(received) == 3:
            done.set()

    bus.subscribe("sequence", handler)
    bus.start()
    try:
        for index in range(3):
            bus.publish(Event(name="sequence", payload={"index": index}, priority=10))
        assert done.wait(1.0)
        assert received == [0, 1, 2]
    finally:
        bus.stop()


def test_wildcard_subscription():
    bus = EventBus()
    received = []
    done = threading.Event()

    def handler(event):
        received.append(event.name)
        if len(received) == 2:
            done.set()

    bus.subscribe("*", handler)
    bus.start()
    try:
        bus.publish(Event(name="app.started"))
        bus.publish(Event(name="system.warning"))
        assert done.wait(1.0)
        assert set(received) == {"app.started", "system.warning"}
    finally:
        bus.stop()


def test_handler_exception_isolation():
    bus = EventBus()
    received = []
    done = threading.Event()

    def failing_handler(event):
        raise RuntimeError("boom")

    def healthy_handler(event):
        received.append(event.name)
        done.set()

    bus.subscribe("test", failing_handler)
    bus.subscribe("test", healthy_handler)
    bus.start()
    try:
        bus.publish(Event(name="test"))
        assert done.wait(1.0)
        assert received == ["test"]
    finally:
        bus.stop()
