"""Inject the live command deck into the actual legacy JarvisWindow."""
from __future__ import annotations


def install(assistant) -> bool:
    window_cls = getattr(assistant, "JarvisWindow", None)
    if window_cls is None or getattr(window_cls, "_neo_command_deck_wired", False):
        return False
    try:
        from ui.neo_command_deck import NeoCommandDeck
    except Exception:
        return False

    original_init = window_cls.__init__

    def init_with_deck(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            deck = NeoCommandDeck(assistant, self)
            self._neo_command_deck = deck
            if hasattr(self, "right_panel"):
                self.right_panel.insertWidget(0, deck)
            else:
                deck.setParent(self)
                deck.show()
        except Exception as exc:
            try:
                assistant.log.warning(f"Command Deck non chargé : {exc}")
            except Exception:
                pass

    window_cls.__init__ = init_with_deck
    window_cls._neo_command_deck_wired = True
    return True
