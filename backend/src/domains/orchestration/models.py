"""Data models for DAG Pipeline Configs and Frontend Layouts."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
