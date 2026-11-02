"""平台治理域模型：租户 / 项目 / 角色 / 角色绑定。

* 租户（Tenant）：组织实体，成员经授权进入；项目挂在租户下。
* 项目（Project）：编排资产与支撑平台操作的作用域单位，项目间完全隔离。
* 角色（Role）：可配置 RBAC 的核心 —— 权限点列表存于角色实体；builtin 角色
  由平台内置、不可删除，租户可创建自定义角色（归属 tenant_id）。
* 角色绑定（RoleBinding）：用户 × 角色 × scope；scope 决定权限生效范围
  （PLATFORM 全局 / TENANT 租户内 / PROJECT 项目内）。
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ScopeKind(str, Enum):
    PLATFORM = "PLATFORM"
    TENANT = "TENANT"
    PROJECT = "PROJECT"


class Tenant(BaseModel):
    tenant_id: str
    code: str
    name: str
    status: str = "ACTIVE"  # ACTIVE | SUSPENDED
    description: str = ""
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class Project(BaseModel):
    project_id: str
    tenant_id: str
    key: str
    name: str
    status: str = "ACTIVE"  # ACTIVE | ARCHIVED
    description: str = ""
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class Role(BaseModel):
    role_id: str
    scope: ScopeKind
    code: str
    name: str
    description: str = ""
    permissions: List[str] = []
    builtin: bool = False
    tenant_id: str = ""  # 自定义角色归属租户（PLATFORM 内置角色为空）
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class RoleBinding(BaseModel):
    binding_id: str
    user_id: str
    role_id: str
    scope: ScopeKind
    tenant_id: str = ""  # TENANT scope 必填
    project_id: str = ""  # PROJECT scope 必填
    status: str = "ACTIVE"  # ACTIVE | DISABLED
    granted_by: str = ""
    granted_at: str = ""


class Environment(BaseModel):
    """项目内执行环境：每项目内置 dev/test/staging/prod 四环境（builtin 不可删）。

    staging/online 为保护级：发布/灰度/回滚类变更要求项目所有者角色（编辑者
    不足以变更线上），owner/平台超管直通。
    """
    env_id: str  # env_
    project_id: str
    key: str  # dev | test | staging | online（内置四键）
    name: str
    description: str = ""
    protected: bool = False
    builtin: bool = True
    created_at: str = ""
    updated_at: str = ""
