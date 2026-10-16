"""Tests for Microkernel DAG Execution Engine."""
import pytest
from src.core.microkernel.models import (
    DAGConfig, ExecutionGraph, NodeDef, EdgeDef, ExecutionStatus, NodeType
)
from src.core.microkernel.engine import MicrokernelEngine


@pytest.fixture
def valid_dag_config() -> DAGConfig:
    return DAGConfig(
        version="v1.0.4-test",
        scenario_code="tax.calculate_vat_exemption",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="dnode-1",
            nodes=[
                NodeDef(id="dnode-1", action_handler="gateway_ingress", type=NodeType.GATEWAY),
                NodeDef(id="dnode-2", action_handler="auth_guard", type=NodeType.GUARD),
                NodeDef(id="dnode-3", action_handler="invoice_tax_calc", type=NodeType.BIZ),
                NodeDef(id="dnode-4", action_handler="es_audit_sync", type=NodeType.STORAGE),
            ],
            edges=[
                EdgeDef(from_node="dnode-1", to_node="dnode-2"),
                EdgeDef(from_node="dnode-2", to_node="dnode-3"),
                EdgeDef(from_node="dnode-3", to_node="dnode-4"),
            ]
        )
    )


@pytest.mark.asyncio
async def test_successful_dag_execution(valid_dag_config):
    engine = MicrokernelEngine()
    result = await engine.execute_dag(
        valid_dag_config,
        initial_inputs={"quarterly_income": 280000.0, "auth_token": "valid_token"}
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.version == "v1.0.4-test"
    assert len(result.node_traces) == 4
    # All 4 nodes executed successfully
    for trace in result.node_traces:
        assert trace.status == ExecutionStatus.SUCCESS

    # Verify tax calculation output
    assert result.final_output["vat_exemption_eligible"] is True
    assert result.final_output["applicable_tax_rate"] == 0.0
    assert result.final_output["estimated_tax_payable"] == 0.0
    assert result.final_output["audit_recorded"] is True


@pytest.mark.asyncio
async def test_guard_rejection_halts_pipeline(valid_dag_config):
    engine = MicrokernelEngine()
    # Pass invalid token to trigger guard rejection
    result = await engine.execute_dag(
        valid_dag_config,
        initial_inputs={"quarterly_income": 280000.0, "auth_token": "invalid_token"}
    )

    assert result.status == ExecutionStatus.GUARD_REJECTED
    assert "Guard check failed" in result.error_message
    # Execution should have halted after node-2
    assert len(result.node_traces) == 2
    assert result.node_traces[1].status == ExecutionStatus.GUARD_REJECTED


@pytest.mark.asyncio
async def test_cycle_detection():
    cyclic_config = DAGConfig(
        version="v1.0.4-cycle",
        scenario_code="test.cyclic",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="n1",
            nodes=[
                NodeDef(id="n1", action_handler="gateway_ingress", type=NodeType.GATEWAY),
                NodeDef(id="n2", action_handler="auth_guard", type=NodeType.GUARD),
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
