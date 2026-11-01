"""实验域模型：实验 / 分配记录 / 结果上报。"""
from typing import List

from pydantic import BaseModel


class Variant(BaseModel):
    key: str
    name: str = ""
    weight: float = 1.0  # 相对权重（读出与试算时展示归一化百分比）


class Experiment(BaseModel):
    experiment_id: str
    key: str
    name: str
    description: str = ""
    status: str = "DRAFT"  # DRAFT | RUNNING | STOPPED | ARCHIVED
    variants: List[Variant] = []
    traffic_percent: int = 100  # 0-100，命中桶 %100 < traffic_percent 进入实验
    project_id: str = ""  # 归属项目（项目域隔离，与编排目录同构）
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class Outcome(BaseModel):
    metric: str
    value: float
    reported_at: str


class AssignmentRecord(BaseModel):
    assignment_id: str  # asg_
    experiment_key: str
    user_id: str
    variant_key: str
    in_experiment: bool
    project_id: str = ""
    outcomes: List[Outcome] = []
    assigned_at: str = ""
