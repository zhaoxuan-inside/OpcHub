"""运维域模型：MicroFlow 场景运行记录（每次 execute_scenario 一条）。"""
from typing import Any, Dict, List

from pydantic import BaseModel


class RunRecord(BaseModel):
    trace_id: str  # 主键（单次执行唯一）
    scenario_code: str
    status: str  # SUCCESS | FAILED | GUARD_REJECTED | CANCELLED...
    execution_time_ms: float = 0.0
    user_id: str = ""
    project_id: str = ""  # 活动项目上下文（scope 路由才有）
    started_at: str = ""
    error_type: str = ""
    error_message: str = ""
    node_count: int = 0
    failed_nodes: List[str] = []
    node_traces: List[Dict[str, Any]] = []  # 单节点 output 截断后留存（瀑布图数据源）
