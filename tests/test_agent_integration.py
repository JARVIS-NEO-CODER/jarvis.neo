from core.action_engine import ActionEngine, ActionDefinition
from core.agent_engine import AgentEngine
from core.goal_planner import GoalPlan, GoalPlanner, GoalStep
from core.goal_verifier import GoalVerifier
from tests.fakes import ControlledObserver, RecoveryPlanner


def test_capability_registry_planner_integration():
    engine = ActionEngine()
    planner = GoalPlanner(engine)
    assert "action.launch_app" in planner.available_actions()
    assert planner.capability_manifest()


def test_full_pipeline_recovery_and_objective_verification():
    engine = ActionEngine()
    calls = []
    engine.register(ActionDefinition("test.first", lambda **k: (_ for _ in ()).throw(RuntimeError("simulated failure")), description="Controlled failure"))
    engine.register(ActionDefinition("test.recovery", lambda **k: calls.append("recovery") or "ok", description="Controlled recovery"))
    planner = GoalPlanner(engine, RecoveryPlanner())
    verifier = GoalVerifier()
    observer = ControlledObserver()
    agent = AgentEngine(engine, planner=planner, observer=observer, verifier=verifier, max_retries=1)
    result = agent.run("Lance Test App")
    assert result.success is True
    assert result.recovery_attempts == 1
    assert result.verification is not None
    assert result.verification.achieved is True
    assert calls == ["recovery"]


def test_goal_verifier_rejects_unverified_failure():
    result = GoalVerifier().verify("Lance Test App", before=None, after=None, action_success=False, action_verified=False)
    assert result.achieved is False


def test_agent_executes_every_step_before_marking_multistep_goal_complete():
    engine = ActionEngine()
    calls = []
    engine.register(ActionDefinition("test.prepare", lambda **k: calls.append("prepare") or "prepared", description="Prepare task"))
    engine.register(ActionDefinition("test.verify", lambda **k: calls.append("verify") or "verified", description="Verify task"))

    class TwoStepPlanner:
        def plan(self, objective):
            return GoalPlan(objective, (
                GoalStep("test.prepare", description="Prepare"),
                GoalStep("test.verify", description="Verify"),
            ))

    agent = AgentEngine(engine, planner=TwoStepPlanner(), observer=ControlledObserver(), max_retries=0)
    result = agent.run("Lance Test App")

    assert result.success is True
    assert calls == ["prepare", "verify"]
    assert len(result.results) == 2


def test_agent_reports_planning_errors_instead_of_crashing():
    class BrokenPlanner:
        def plan(self, objective):
            raise RuntimeError("planner unavailable")

    agent = AgentEngine(ActionEngine(), planner=BrokenPlanner(), max_retries=0)
    result = agent.run("Lance Test App")

    assert result.success is False
    assert "planner unavailable" in (result.error or "")
    assert agent.running is False


def test_agent_does_not_repeat_failed_plan_when_replanning_fails():
    engine = ActionEngine()
    calls = []
    engine.register(ActionDefinition(
        "test.always_fails",
        lambda **k: calls.append("attempt") or (_ for _ in ()).throw(RuntimeError("controlled failure")),
        description="Controlled failure",
    ))

    class BrokenRecoveryPlanner:
        def plan(self, objective):
            return GoalPlan(objective, (GoalStep("test.always_fails"),))

        def replan(self, objective, **kwargs):
            raise RuntimeError("replanning unavailable")

    agent = AgentEngine(engine, planner=BrokenRecoveryPlanner(), max_retries=2)
    result = agent.run("Effectue une action")

    assert result.success is False
    assert "replanning unavailable" in (result.error or "")
    assert calls == ["attempt"]
