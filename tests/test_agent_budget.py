from core.action_engine import ActionEngine
from core.agent_engine import AgentEngine


def test_budget_estimate_is_bounded_without_planner_call():
    engine = AgentEngine(ActionEngine(), max_retries=2, max_steps=5, max_ia_calls=7)
    budget = engine.estimate_budget("cherche puis compare deux résultats")
    assert 1 <= budget["estimated_steps"] <= 5
    assert 1 <= budget["estimated_ia_calls"] <= 7
    assert budget["risk"] in {"faible", "moyenne", "élevée"}
