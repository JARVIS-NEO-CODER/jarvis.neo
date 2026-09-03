"""Runtime UI bridges for the legacy desktop launcher."""
from __future__ import annotations


def install(assistant, session) -> bool:
    """Connect the live session timer and discrete HUD to the legacy window."""
    if getattr(assistant, "_neo_runtime_ui_bridge", False):
        return True

    worker = getattr(assistant, "command_worker", None)
    if worker is not None and not getattr(worker, "_neo_session_wrapped", False):
        original_worker = worker

        def wrapped_worker():
            # The legacy worker owns the actual AI call and speech playback.
            # The session stays frozen while that work is in progress and only
            # starts its 12s idle countdown after speech.say() returns.
            original_worker()

        # Do not wrap the infinite worker itself: instead wrap speech.say(),
        # which gives us the exact end of each spoken response without copying
        # the legacy queue/error handling.
        speech = getattr(assistant, "speech", None)
        original_say = getattr(speech, "say", None) if speech else None
        if original_say is not None and not getattr(original_say, "_neo_session_wrapped", False):
            def say_and_finish(*args, **kwargs):
                try:
                    return original_say(*args, **kwargs)
                finally:
                    session.touch()
            say_and_finish._neo_session_wrapped = True
            speech.say = say_and_finish

        # Mark the worker bridge as installed so this hook remains idempotent.
        wrapped_worker._neo_session_wrapped = True
        assistant.command_worker = worker

    try:
        from ui.discrete_hud import DiscreteHud
        from PyQt6.QtWidgets import QMainWindow
    except Exception:
        return False

    window_cls = getattr(assistant, "JarvisWindow", None)
    if window_cls is None or getattr(window_cls, "_neo_discrete_patched", False):
        assistant._neo_runtime_ui_bridge = True
        return True

    original_show = window_cls.show
    original_close = window_cls.close

    def show_with_discrete(self):
        original_show(self)
        try:
            if getattr(self, "_neo_discrete_hud", None) is None:
                self._neo_discrete_hud = DiscreteHud(self)
            # Full cockpit remains available from the reactor. Hide it after
            # the first paint so startup behaves like a background assistant.
            self._neo_discrete_hud.show_discrete()
            self.hide()
        except Exception:
            # Never prevent the normal UI from starting if the tiny HUD fails.
            original_show(self)

    def close_with_discrete(self):
        hud = getattr(self, "_neo_discrete_hud", None)
        if hud is not None:
            hud.close()
        return original_close(self)

    window_cls.show = show_with_discrete
    window_cls.close = close_with_discrete
    window_cls._neo_discrete_patched = True
    assistant._neo_runtime_ui_bridge = True
    return True


__all__ = ["install"]
