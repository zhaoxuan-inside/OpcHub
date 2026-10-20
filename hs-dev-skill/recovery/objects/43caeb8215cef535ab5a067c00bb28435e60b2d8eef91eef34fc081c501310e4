"""Unit and Integration Tests for Microkernel Six-Tuple Saga Reverse Compensation Engine."""
import pytest
from src.core.microkernel import (
    microkernel_engine,
    registry,
    DAGConfig,
    ExecutionGraph,
    NodeDef,
    EdgeDef,
    NodeType,
    ExecutionStatus,
)


@pytest.fixture(autouse=True)
def clean_test_handlers():
    """Ensure mock test handlers are cleaned up around each test."""
    yield
    # Cleanup any test handlers if present
    for name in ["test.step1", "test.step2", "test.failing_step", "test.guard_fail"]:
        registry._handlers.pop(name, None)
        registry._compensators.pop(name, None)


@pytest.mark.asyncio
async def test_successful_dag_does_not_trigger_compensation():
    """Verify that a successful pipeline does not trigger any compensations."""
    registry.register(
        "test.step1",
        lambda inputs, ctx: {"step1_done": True},
        compensator=lambda inputs, ctx: {"compensated_step1": True},
    )
    registry.register(
        "test.step2",
        lambda inputs, ctx: {"step2_done": True},
        compensator=lambda inputs, ctx: {"compensated_step2": True},
    )

    config = DAGConfig(
        scenario_code="test.saga.success",
        version="v1.0.0",
        enable_saga_compensation=True,
        execution_graph=ExecutionGraph(
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="test.step1", type=NodeType.BIZ),
                NodeDef(id="n2", action_handler="test.step2", type=NodeType.BIZ),
            ],
            edges=[EdgeDef(from_node="n1", to_node="n2")],
        ),
    )

    result = await microkernel_engine.execute_dag(config, initial_inputs={"init": 1})
    assert result.status == ExecutionStatus.SUCCESS
    assert result.final_output.get("step1_done") is True
    assert result.final_output.get("step2_done") is True
    assert len(result.compensation_traces) == 0


@pytest.mark.asyncio
async def test_saga_reverse_compensation_on_error():
    """Verify that when a downstream node fails, preceding completed nodes are compensated in reverse order."""
    state = {
        "quota_reserved": False,
        "deposit_deducted": False,
        "compensation_order": [],
    }

    # Step 1: Reserve quota
    def step1_action(inputs, ctx):
        state["quota_reserved"] = True
        return {"quota": "RESERVED_100"}

    def step1_compensate(inputs, ctx):
        state["quota_reserved"] = False
        state["compensation_order"].append("step1")
        return {"quota_refunded": True}

    # Step 2: Deduct deposit
    def step2_action(inputs, ctx):
        state["deposit_deducted"] = True
        return {"deposit_tx": "TX_9981"}

    def step2_compensate(inputs, ctx):
        state["deposit_deducted"] = False
        state["compensation_order"].append("step2")
        return {"deposit_returned": True}

    # Step 3: Failing operator
    def step3_action(inputs, ctx):
        raise ValueError("Simulated downstream payment gateway timeout")

    registry.register("test.step1", step1_action, compensator=step1_compensate)
    registry.register("test.step2", step2_action, compensator=step2_compensate)
    registry.register("test.failing_step", step3_action)

    config = DAGConfig(
        scenario_code="test.saga.rollback",
        version="v1.0.0",
        enable_saga_compensation=True,
        execution_graph=ExecutionGraph(
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="test.step1", type=NodeType.BIZ),
                NodeDef(id="n2", action_handler="test.step2", type=NodeType.BIZ),
                NodeDef(id="n3", action_handler="test.failing_step", type=NodeType.BIZ),
            ],
            edges=[
                EdgeDef(from_node="n1", to_node="n2"),
                EdgeDef(from_node="n2", to_node="n3"),
            ],
        ),
    )

    result = await microkernel_engine.execute_dag(config, initial_inputs={"maker_id": "usr_maker_1"})

    # Assertions on pipeline status
    assert result.status == ExecutionStatus.ROLLED_BACK
    assert "Simulated downstream payment gateway timeout" in (result.error_message or "")

    # Assertions on reverse order execution: step2 MUST be compensated before step1
    assert state["compensation_order"] == ["step2", "step1"]
    assert state["deposit_deducted"] is False
    assert state["quota_reserved"] is False

    # Assertions on compensation traces
    assert len(result.compensation_traces) == 2
    assert result.compensation_traces[0].node_id == "n2"
    assert result.compensation_traces[0].status == "SUCCESS"
    assert result.compensation_traces[0].action_handler == "test.step2_compensate"
    assert result.compensation_traces[1].node_id == "n1"
    assert result.compensation_traces[1].status == "SUCCESS"
    assert result.compensation_traces[1].action_handler == "test.step1_compensate"


@pytest.mark.asyncio
async def test_saga_rollback_on_guard_rejection():
    """Verify that when a Guard rejects execution, completed prior nodes are compensated cleanly."""
    state = {"resource_locked": False, "compensated": False}

    def lock_res(inputs, ctx):
        state["resource_locked"] = True
        return {"lock_id": "lock_007"}

    def unlock_res(inputs, ctx):
        state["resource_locked"] = False
        state["compensated"] = True
        return {"unlocked": True}

    def guard_fail(inputs, ctx):
        raise PermissionError("Identity verification invalid for sensitive operation")

    registry.register("test.step1", lock_res, compensator=unlock_res)
    registry.register("test.guard_fail", guard_fail)

    config = DAGConfig(
        scenario_code="test.saga.guard",
        version="v1.0.0",
        enable_saga_compensation=True,
        execution_graph=ExecutionGraph(
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="test.step1", type=NodeType.BIZ),
                NodeDef(id="n2", action_handler="test.guard_fail", type=NodeType.GUARD),
            ],
            edges=[EdgeDef(from_node="n1", to_node="n2")],
        ),
    )

    result = await microkernel_engine.execute_dag(config, initial_inputs={})
    assert result.status == ExecutionStatus.ROLLED_BACK
    assert "Guard check failed" in (result.error_message or "")
    assert state["resource_locked"] is False
    assert state["compensated"] is True
    assert len(result.compensation_traces) == 1
    assert result.compensation_traces[0].status == "SUCCESS"


@pytest.mark.asyncio
async def test_saga_compensation_failure_reporting():
    """Verify that if a compensator raises an error, status marks as COMPENSATION_FAILED."""
    def action_step(inputs, ctx):
        return {"data": 1}

    def faulty_compensator(inputs, ctx):
        raise RuntimeError("Database connection lost during compensation rollback")

    def fail_step(inputs, ctx):
        raise ValueError("Intentional business failure")

    registry.register("test.step1", action_step, compensator=faulty_compensator)
    registry.register("test.failing_step", fail_step)

    config = DAGConfig(
        scenario_code="test.saga.faulty_comp",
        version="v1.0.0",
        enable_saga_compensation=True,
        execution_graph=ExecutionGraph(
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="test.step1", type=NodeType.BIZ),
                NodeDef(id="n2", action_handler="test.failing_step", type=NodeType.BIZ),
            ],
            edges=[EdgeDef(from_node="n1", to_node="n2")],
        ),
    )

    result = await microkernel_engine.execute_dag(config, initial_inputs={})
    assert result.status == ExecutionStatus.COMPENSATION_FAILED
    assert len(result.compensation_traces) == 1
    assert result.compensation_traces[0].status == "FAILED"
    assert "Database connection lost" in result.compensation_traces[0].error
