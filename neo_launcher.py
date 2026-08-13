"""Launch J.A.R.V.I.S. NEO with the new HUD, without modifying assistant.py."""

import assistant
from ui.neo_window import NeoWindow

# Replace only the window class used by assistant.main().
assistant.JarvisWindow = NeoWindow.build(assistant.JarvisWindow)

if __name__ == "__main__":
    assistant.main()
