"""Runtime UI bridges for the legacy desktop launcher."""
from __future__ import annotations


def install(assistant, session) -> bool:
    """Patch the legacy window without creating Qt widgets off the GUI thread."""
    if getattr(assistant, "_neo_runtime_ui_bridge", False):
        return True

    speech = getattr(assistant, "speech", None)
    original_say = getattr(speech, "say", None) if speech else None
    if original_say is not None and not getattr(original_say, "_neo_session_wrapped", False):
        def say_and_finish(*args, **kwargs):
            try:
                return original_say(*args, **kwargs)
            finally:
                # The 12s follow-up window starts after speech has finished.
                session.touch()
        say_and_finish._neo_session_wrapped = True
        speech.say = say_and_finish

    try:
        from ui.discrete_hud import DiscreteHud
    except Exception:
        return False

    window_cls = getattr(assistant, "JarvisWindow", None)
    if window_cls is None:
        return False
    if getattr(window_cls, "_neo_discrete_patched", False):
        assistant._neo_runtime_ui_bridge = True
        return True

    original_show = window_cls.show
    original_close = window_cls.close

    def show_with_discrete(self):
        # A click on the reactor explicitly requests the full cockpit.
        if getattr(self, "_neo_reveal", False):
            original_show(self)
            return
        original_show(self)
        try:
            hud = getattr(self, "_neo_discrete_hud", None)
            if hud is None:
                hud = DiscreteHud(self)
                self._neo_discrete_hud = hud
            hud.show_discrete()
            self.hide()
        except Exception:
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
