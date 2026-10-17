from core.action_engine import ActionEngine, ActionDefinition
from core.agent_engine import AgentEngine
from core.goal_planner import GoalPlan, GoalPlanner, GoalStep
from core.goal_verifier import GoalVerification, GoalVerifier
from tests.fakes import ControlledObserver, RecoveryPlanner


class ControlledGoalVerifier:
    """Test-only verifier that uses the controlled observer's known window."""

    def verify(self, objective, **kwargs):
        after = kwargs.get("after")
        action_success = kwargs.get("action_success", False)
        action_verified = kwargs.get("action_verified", False)
        achieved = bool(
            action_success
            and action_verified
            and after is not None
            and "test app" in (after.active_window or "").lower()
        )
        return GoalVerification(
            achieved,
            1.0 if achieved else 0.0,
            "Controlled test window detected." if achieved else "Controlled test window not detected.",
            {"test_window_detected": achieved},
        )


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
    verifier = ControlledGoalVerifier()
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

    agent = AgentEngine(engine, planner=TwoStepPlanner(), observer=ControlledObserver(), verifier=ControlledGoalVerifier(), max_retries=0)
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



def test_agent_enforces_ia_call_budget_before_replanning():
    engine = ActionEngine()
    engine.register(ActionDefinition(
        "test.fail",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("controlled failure")),
        description="Controlled failure",
    ))

    class CountingPlanner:
        def __init__(self):
            self.plan_calls = 0
            self.replan_calls = 0

        def plan(self, objective):
            self.plan_calls += 1
            return GoalPlan(objective, (GoalStep("test.fail"),))

        def replan(self, objective, **kwargs):
            self.replan_calls += 1
            return GoalPlan(objective, (GoalStep("test.fail"),))

    planner = CountingPlanner()
    agent = AgentEngine(
        engine,
        planner=planner,
        observer=ControlledObserver(),
        max_retries=2,
        max_ia_calls=1,
    )
    result = agent.run("Effectue une action")

    assert result.success is False
    assert "Budget IA épuisé" in (result.error or "")
    assert result.ia_calls == 1
    assert planner.plan_calls == 1
    assert planner.replan_calls == 0


def test_agent_passes_capability_context_to_goal_verifier():
    from core.goal_verifier import GoalVerification

    engine = ActionEngine()
    engine.register(ActionDefinition(
        "test.context",
        lambda **kwargs: "ok",
        description="Test action context",
    ))

    class OneStepPlanner:
        def plan(self, objective):
            return GoalPlan(objective, (GoalStep("test.context", {"value": "expected"}),))

    class RecordingVerifier:
        def __init__(self):
            self.received = None

        def verify(self, objective, **kwargs):
            self.received = kwargs
            return GoalVerification(True, 1.0, "verified by test", {"ok": True})

    verifier = RecordingVerifier()
    agent = AgentEngine(
        engine,
        planner=OneStepPlanner(),
        observer=ControlledObserver(),
        verifier=verifier,
        max_retries=0,
    )
    result = agent.run("Effectue une action")

    assert result.success is True
    assert verifier.received["action_name"] == "test.context"
    assert verifier.received["action_kwargs"] == {"value": "expected"}
    assert verifier.received["action_message"] == "ok"
