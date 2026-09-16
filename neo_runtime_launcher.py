"""Canonical J.A.R.V.I.S. NEO runtime launcher.

Loads the existing platform layer, wires the autonomous agent bridge, then
starts the real assistant runtime. Keeping this bootstrap separate avoids
rewriting the legacy assistant while ensuring the new agent is actually live.
"""
from __future__ import annotations

import assistant
from neo_platform import install as install_platform
from neo_agent.desktop_bridge import install as install_agent_bridge


install_platform(assistant)
install_agent_bridge()


if __name__ == "__main__":
    assistant.main()
