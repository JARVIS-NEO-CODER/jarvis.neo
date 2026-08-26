import tempfile
import unittest
from pathlib import Path

from core.action_engine import ActionEngine
from core.automation import AutomationEngine
from core.context_engine import ContextEngine
from core.core_bridge import CoreBridge
from core.memory import NeoMemory
from core.performance_manager import PerformanceManager, PerformanceProfile


class CoreBridgeTests(unittest.TestCase):
    def make_bridge(self):
        directory = tempfile.TemporaryDirectory()
        memory = NeoMemory(Path(directory.name) / "test.db")
        bridge = CoreBridge(
            memory=memory,
            context=ContextEngine(memory=memory),
            actions=ActionEngine(memory=memory),
            automation=AutomationEngine(),
            performance=PerformanceManager(),
        )
        return directory, bridge

    def test_tick_detects_unknown_context_without_ai(self):
        directory, bridge = self.make_bridge()
        try:
            result = bridge.tick(force=True) if hasattr(bridge, "tick") else None
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "unknown")
        finally:
            bridge.shutdown()
            directory.cleanup()

    def test_gaming_policy_is_lightweight(self):
        manager = PerformanceManager()
        policy = manager.apply_context("gaming")
        self.assertEqual(manager.profile, PerformanceProfile.GAMING)
        self.assertFalse(policy.allow_ollama)
        self.assertFalse(policy.allow_vision)
        self.assertFalse(policy.allow_heavy_background_tasks)


if __name__ == "__main__":
    unittest.main()
