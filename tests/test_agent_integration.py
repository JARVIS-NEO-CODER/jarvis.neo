from core.action_engine import ActionEngine, ActionDefinition, ControlMode
from core.goal_planner import GoalPlanner
from core.goal_verifier import GoalVerifier

def test_capability_registry_planner_integration():
    engine=ActionEngine(); planner=GoalPlanner(engine)
    assert "action.launch_app" in planner.available_actions()
    assert planner.capability_manifest()
    assert engine.capabilities.require("action.launch_app").permission == ControlMode.AGENT.value

def test_full_pipeline_planner_action_observation_verification_recovery():
    engine=ActionEngine(); calls=[]
    engine.register(ActionDefinition("test.first", lambda **k: (_ for _ in ()).throw(RuntimeError("simulated")), description="Fails"))
    engine.register(ActionDefinition("test.recovery", lambda **k: calls.append("recovery") or "ok", description="Recovery"))
    class Planner:
        def plan(self, objective, manifest): return {"steps":[{"action":"test.first","kwargs":{}}]}
        def replan(self, objective, manifest, **kwargs): return {"steps":[{"action":"test.recovery","kwargs":{}}]}
    planner=GoalPlanner(engine, Planner())
    assert planner.plan("test").steps[0].action == "test.first"
    assert planner.replan("test", failure="failed", observation={}, attempted_actions=("test.first",)).steps[0].action == "test.recovery"
    assert calls == []

def test_goal_verifier_rejects_unverified_failure():
    result=GoalVerifier().verify("Lance Test App", before=None, after=None, action_success=False, action_verified=False)
    assert result.achieved is False
