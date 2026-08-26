import threading
import time

from core.neo_pipeline import NeoPipeline


def test_pipeline_starts_and_stops_cleanly():
    seen = []
    ready = threading.Event()

    def on_hud(payload):
        seen.append(payload)
        ready.set()

    pipeline = NeoPipeline(hud_callback=on_hud, interval=0.25)
    pipeline.start()
    try:
        assert pipeline.running
        pipeline.bus.emit("hud.show", {"target": "context"})
        assert ready.wait(1.0)
        assert seen == [{"target": "context"}]
    finally:
        pipeline.stop()

    assert not pipeline.running


def test_pipeline_stop_is_idempotent():
    pipeline = NeoPipeline(interval=0.25)
    pipeline.start()
    pipeline.stop()
    pipeline.stop()
    assert not pipeline.running
