"""Pydantic schemas and models for the Microkernel DAG engine."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    GATEWAY = "GATEWAY"
    GUARD = "GUARD"
    BIZ = "BIZ"
    STORAGE = "STORAGE"
    CUSTOM = "CUSTOM"


class NodeDef(BaseModel):
    """Definition of an atomic node in the DAG graph."""
    id: str
    action_handler: str
    type: NodeType = NodeType.BIZ
    retry: int = Field(default=1, ge=0, le=5)
    timeout_ms: int = Field(default=5000, ge=100)


class EdgeDef(BaseModel):
    """Directional edge from one node to another."""
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")

    model_config = {"populate_by_name": True}


class ExecutionGraph(BaseModel):
    """Execution graph topology."""
    topology: str = "DAG"
    entry_node: str = "dnode-1"
    nodes: list[NodeDef]
    edges: list[EdgeDef]


class DAGConfig(BaseModel):
    """Top-level configuration payload compiled by the visual orchestrator."""
    version: str = "v1.0.4-draft"
    scenario_code: str = "tax.calculate_vat_exemption"
    timestamp: str | None = None
    execution_graph: ExecutionGraph
    enable_saga_compensation: bool = True


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CYCLE_DETECTED = "CYCLE_DETECTED"
    GUARD_REJECTED = "GUARD_REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    COMPENSATION_FAILED = "COMPENSATION_FAILED"


class NodeExecutionTrace(BaseModel):
    node_id: str
    action_handler: str
    type: NodeType
    status: ExecutionStatus
    duration_ms: float
    trace_id: str | None = None
    output: Any = None
    error: str | None = None


class CompensationTrace(BaseModel):
    node_id: str
    action_handler: str
    status: str
    duration_ms: float
    trace_id: str | None = None
    output: Any = None
    error: str | None = None


class ExecutionResult(BaseModel):
    pipeline_id: str
    trace_id: str | None = None
    version: str
    scenario_code: str
    status: ExecutionStatus
    total_duration_ms: float
    entry_node: str
    node_traces: list[NodeExecutionTrace]
    final_output: dict[str, Any]
    error_message: str | None = None
    compensation_traces: list[CompensationTrace] = Field(default_factory=list)

