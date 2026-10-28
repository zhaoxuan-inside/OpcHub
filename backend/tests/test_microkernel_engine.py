"""Tests for Microkernel DAG Execution Engine.

Operator-kernel v2: nodes are declarative invocations of registered, business-
agnostic operators (``NodeDef.params`` / ``inputs_map`` / ``when``). The legacy
hard-coded handlers (``gateway_ingress`` / ``auth_guard`` / ``invoice_tax_calc``
/ ``es_audit_sync``) were removed with the v1 service layer.
"""
import pytest
from src.core.microkernel.models import (
    DAGConfig, ExecutionGraph, NodeDef, EdgeDef, ExecutionStatus, NodeType
)
from src.core.microkernel.engine import MicrokernelEngine


@pytest.fixture
def valid_dag_config() -> DAGConfig:
    return DAGConfig(
        version="v1.0.4-test",
        scenario_code="test.tax_calculate_vat_exemption",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="dnode-1",
            nodes=[
                NodeDef(id="dnode-1", action_handler="guard.authn", type=NodeType.GUARD),
                NodeDef(
                    id="dnode-2",
                    action_handler="transform.derive",
                    type=NodeType.BIZ,
                    params={"expr": "args.income * 0.0", "output_key": "applicable_tax_rate"},
                    inputs_map={"income": "$inputs.quarterly_income"},
                ),
                NodeDef(
                    id="dnode-3",
                    action_handler="transform.derive",
                    type=NodeType.BIZ,
                    params={"expr": "args.income * args.rate", "output_key": "estimated_tax_payable"},
                    inputs_map={
                        "income": "$inputs.quarterly_income",
                        "rate": "$nodes.dnode-2.applicable_tax_rate",
                    },
                ),
                NodeDef(
                    id="dnode-4",
                    action_handler="transform.derive",
                    type=NodeType.BIZ,
                    params={"expr": "args.income <= 300000", "output_key": "vat_exemption_eligible"},
                    inputs_map={"income": "$inputs.quarterly_income"},
                ),
            ],
            edges=[
                EdgeDef(from_node="dnode-1", to_node="dnode-2"),
                EdgeDef(from_node="dnode-2", to_node="dnode-3"),
                EdgeDef(from_node="dnode-3", to_node="dnode-4"),
            ]
        )
    )


AUTH_CONTEXT = {"user_id": "usr_engine_maker", "user_role": "MAKER"}


@pytest.mark.asyncio
async def test_successful_dag_execution(valid_dag_config):
    engine = MicrokernelEngine()
    result = await engine.execute_dag(
        valid_dag_config,
        initial_inputs={"quarterly_income": 280000.0},
        initial_context=dict(AUTH_CONTEXT),
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.version == "v1.0.4-test"
    assert len(result.node_traces) == 4
    # All 4 nodes executed successfully
    for trace in result.node_traces:
        assert trace.status == ExecutionStatus.SUCCESS

    # Verify calculation output propagated through $nodes references
    assert result.final_output["vat_exemption_eligible"] is True
    assert result.final_output["applicable_tax_rate"] == 0.0
    assert result.final_output["estimated_tax_payable"] == 0.0


@pytest.mark.asyncio
async def test_guard_rejection_halts_pipeline(valid_dag_config):
    engine = MicrokernelEngine()
    # No identity in context -> guard.authn rejects the first node
    result = await engine.execute_dag(
        valid_dag_config,
        initial_inputs={"quarterly_income": 280000.0},
    )

    assert result.status == ExecutionStatus.GUARD_REJECTED
    assert "Guard check failed" in result.error_message
    # Execution halts on the guard node
    assert len(result.node_traces) == 1
    assert result.node_traces[0].status == ExecutionStatus.GUARD_REJECTED


@pytest.mark.asyncio
async def test_cycle_detection():
    cyclic_config = DAGConfig(
        version="v1.0.4-cycle",
        scenario_code="test.cyclic",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="guard.authn", type=NodeType.GUARD),
                NodeDef(id="n2", action_handler="transform.derive", type=NodeType.BIZ),
            ],
            edges=[
                EdgeDef(from_node="n1", to_node="n2"),
                EdgeDef(from_node="n2", to_node="n1"),  # Creates cycle!
            ]
        )
    )
    engine = MicrokernelEngine()
    result = await engine.execute_dag(cyclic_config)

    assert result.status == ExecutionStatus.CYCLE_DETECTED
    assert "Cyclic dependency" in result.error_message


@pytest.mark.asyncio
async def test_single_entry_and_single_exit_validation():
    # 1. Valid single entry and single exit DAG
    valid_config = DAGConfig(
        version="v1.0.4-valid",
        scenario_code="test.valid_sink",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="n1",
            exit_node="n3",
            nodes=[
                NodeDef(id="n1", action_handler="guard.authn", type=NodeType.GUARD),
                NodeDef(
                    id="n2", action_handler="transform.derive", type=NodeType.BIZ,
                    params={"expr": "args.income * 0.5", "output_key": "half"},
                    inputs_map={"income": "$inputs.quarterly_income"},
                ),
                NodeDef(
                    id="n3", action_handler="transform.derive", type=NodeType.BIZ,
                    params={"expr": "args.half + 1", "output_key": "total"},
                    inputs_map={"half": "$nodes.n2.half"},
                ),
            ],
            edges=[
                EdgeDef(from_node="n1", to_node="n2"),
                EdgeDef(from_node="n2", to_node="n3"),
            ]
        )
    )
    engine = MicrokernelEngine()
    result = await engine.execute_dag(
        valid_config,
        initial_inputs={"quarterly_income": 100000.0},
        initial_context=dict(AUTH_CONTEXT),
    )
    assert result.status == ExecutionStatus.SUCCESS
    assert result.entry_node == "n1"
    assert result.exit_node == "n3"
    assert result.final_output["total"] == 50001.0

    # 2. Multi-exit DAG (unconverged branches) must be rejected
    multi_exit_config = DAGConfig(
        version="v1.0.4-multi-exit",
        scenario_code="test.multi_exit",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="guard.authn", type=NodeType.GUARD),
                NodeDef(id="n2_a", action_handler="transform.derive", type=NodeType.BIZ),
                NodeDef(id="n2_b", action_handler="transform.derive", type=NodeType.BIZ),
            ],
            edges=[
                EdgeDef(from_node="n1", to_node="n2_a"),
                EdgeDef(from_node="n1", to_node="n2_b"),  # Both n2_a and n2_b are sinks!
            ]
        )
    )
    res_multi = await engine.execute_dag(multi_exit_config)
    assert res_multi.status == ExecutionStatus.CYCLE_DETECTED
    assert "Graph must have exactly ONE exit point" in res_multi.error_message
