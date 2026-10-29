"""Data models for DAG Pipeline Configs, Frontend Layouts, and Scenario Execution."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.core.microkernel.dispatcher import DispatchMode, OperatorDescriptor


class DAGConfigSaveRequest(BaseModel):
    scenario_code: str
    version: str
    topology_graph: Dict[str, Any]
    status: str = "ACTIVE"
    created_by: str = "usr_admin_001"


class DAGConfigRecord(BaseModel):
    id: str
    scenario_code: str
    version: str
    status: str
    topology_graph: Dict[str, Any]
    compiled_hash: str
    created_by: str
    created_at: str


class FrontendLayoutSaveRequest(BaseModel):
    layout_name: str = "main_console_layout"
    version: str = "v1.0.4"
    grid_schema: Dict[str, Any]
    widgets: List[Dict[str, Any]]


class FrontendLayoutRecord(BaseModel):
    id: str
    layout_name: str
    version: str
    grid_schema: Dict[str, Any]
    widgets: List[Dict[str, Any]]
    updated_at: str


class OperatorModeUpdateRequest(BaseModel):
    name: str
    mode: DispatchMode
    remote_endpoint: Optional[str] = None


class ScenarioExecuteRequest(BaseModel):
    scenario_code: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    # Caller/gateway context propagated into every operator (user_id, user_role,
    # token, trace metadata…). Operators must not read identity from payload.
    context: Dict[str, Any] = Field(default_factory=dict)
    override_dispatch_mode: Optional[DispatchMode] = None


class ScenarioExecuteResponse(BaseModel):
    scenario_code: str
    status: str
    execution_time_ms: float
    trace_id: str
    effective_dispatch_mode: str
    node_traces: List[Dict[str, Any]]
    final_output: Dict[str, Any]
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    compensation_traces: List[Dict[str, Any]] = Field(default_factory=list)
