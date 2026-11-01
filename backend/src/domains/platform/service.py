"""平台治理服务：分租户 · 分用户 · 分权限 · 分项目的授权底座。

授权模型（可配置 RBAC）：
* 角色 = 权限点列表（数据）。builtin 角色由平台内置、不可删除；租户可创建
  归属本租户的自定义角色（tenant_id 归属）。
* 授权 = RoleBinding（用户 × 角色 × scope）。有效权限 = PLATFORM 绑定 ∪
  （活动租户匹配的）TENANT 绑定 ∪ （活动项目匹配的）PROJECT 绑定 的角色权限并集。
* legacy users.role（token role claim）仍由网关静态矩阵先行短路：ADMIN 通配
  直通、MAKER/GUEST 存量行为不变 —— 可配置角色在其上做增量授予，因此旧
  场景零回归。

持久化：domain_persistence write-behind + 启动 hydrate。授权数据为安全关键，
每次变异前 require() —— PostgreSQL 不可用时拒绝变更（strict），绝不静默降级。

错误约定（对齐网关 envelope 语义）：ValueError→400、KeyError→404、
PermissionError→403。
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.core.rbac import (
    ALL_PERMISSIONS,
    P_PLATFORM_ROLE_MANAGE,
    P_PLATFORM_TENANT_MANAGE,
    P_PLATFORM_USER_MANAGE,
    P_TENANT_MEMBER_MANAGE,
    P_TENANT_PROJECT_CREATE,
    P_TENANT_ROLE_MANAGE,
    USER_PERMISSIONS,
    has_permission,
    normalize_role,
)
from src.domains.platform.models import Project, Role, RoleBinding, ScopeKind, Tenant
from src.infrastructure.database.persistence import domain_persistence

# domain_snapshots 文档族（启动 hydrate 重建内存索引）
FAMILY_TENANTS = "platform.tenants"
FAMILY_PROJECTS = "platform.projects"
FAMILY_ROLES = "platform.roles"
FAMILY_BINDINGS = "platform.role_bindings"

TENANT_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
PROJECT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
ROLE_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,47}$")

BUILTIN_ADMIN_UID = "usr_admin_builtin"
LEGACY_ROLES = ("ADMIN", "MAKER", "GUEST")
MIN_PASSWORD_LENGTH = 8

# 内置角色（id 稳定，供绑定引用；builtin=True 不可删除）
ROLE_PLATFORM_ADMIN = "rol_platform_admin"
ROLE_PLATFORM_MAKER = "rol_platform_maker"
ROLE_TENANT_ADMIN = "rol_tenant_admin"
ROLE_TENANT_MEMBER = "rol_tenant_member"
ROLE_PROJECT_OWNER = "rol_project_owner"
ROLE_PROJECT_EDITOR = "rol_project_editor"
ROLE_PROJECT_VIEWER = "rol_project_viewer"

BUILTIN_ROLES: List[Role] = [
    Role(
        role_id=ROLE_PLATFORM_ADMIN,
        scope=ScopeKind.PLATFORM,
        code="platform_admin",
        name="平台超级管理员",
        description="平台级通配权限（legacy ADMIN 同义）",
        permissions=["*"],
        builtin=True,
    ),
    Role(
        role_id=ROLE_PLATFORM_MAKER,
        scope=ScopeKind.PLATFORM,
        code="platform_maker",
        name="平台创客",
        description="与 legacy MAKER/USER 静态矩阵等价的平台角色",
        permissions=sorted(USER_PERMISSIONS),
        builtin=True,
    ),
    Role(
        role_id=ROLE_TENANT_ADMIN,
        scope=ScopeKind.TENANT,
        code="tenant_admin",
        name="租户管理员",
        description="管理本租户成员与项目，可创建自定义角色；可只读浏览本租户项目资产",
        permissions=[P_TENANT_MEMBER_MANAGE, P_TENANT_PROJECT_CREATE, P_TENANT_ROLE_MANAGE, "orchestration:read"],
        builtin=True,
    ),
    Role(
        role_id=ROLE_TENANT_MEMBER,
        scope=ScopeKind.TENANT,
        code="tenant_member",
        name="租户成员",
        description="租户在册成员（无固有权限，经项目角色获得访问）",
        permissions=[],
        builtin=True,
    ),
    Role(
        role_id=ROLE_PROJECT_OWNER,
        scope=ScopeKind.PROJECT,
        code="project_owner",
        name="项目所有者",
        description="项目管理与成员授权 + 编排读写",
        permissions=["orchestration:read", "orchestration:write", "project:manage", "project:member_manage"],
        builtin=True,
    ),
    Role(
        role_id=ROLE_PROJECT_EDITOR,
        scope=ScopeKind.PROJECT,
        code="project_editor",
        name="项目编辑者",
        description="编排目录读写（创建/版本/发布/回滚/审批）",
        permissions=["orchestration:read", "orchestration:write"],
        builtin=True,
    ),
    Role(
        role_id=ROLE_PROJECT_VIEWER,
        scope=ScopeKind.PROJECT,
        code="project_viewer",
        name="项目查看者",
        description="编排目录只读",
        permissions=["orchestration:read"],
        builtin=True,
    ),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class PlatformService:
    """租户 / 项目 / 角色 / 绑定注册表 + 授权判定（内存索引为运行时读路径）。"""

    def __init__(self) -> None:
        self._tenants: Dict[str, Tenant] = {}
        self._projects: Dict[str, Project] = {}
        self._roles: Dict[str, Role] = {}
        self._bindings: Dict[str, RoleBinding] = {}
        self._seed_builtin_roles()

    # ------------------------------------------------------------------
    # 内置角色种子（幂等）
    # ------------------------------------------------------------------
    def _seed_builtin_roles(self) -> None:
        for role in BUILTIN_ROLES:
            if role.role_id in self._roles:
                continue
            self._roles[role.role_id] = role
            domain_persistence.write(FAMILY_ROLES, role.role_id, role)

    # ------------------------------------------------------------------
    # 基础 helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _actor(context: Optional[Dict[str, Any]]) -> str:
        uid = str((context or {}).get("user_id") or "").strip()
        if not uid:
            raise PermissionError("UNAUTHORIZED:平台治理操作需要登录身份")
        return uid

    def _require_permission(
        self,
        context: Optional[Dict[str, Any]],
        permission: str,
        tenant_id: str = "",
        project_id: str = "",
    ) -> str:
        """权限断言：legacy 静态矩阵先行，可配置绑定按 scope 兜底。返回 actor uid。"""
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        if has_permission(role, permission):
            return uid
        if self.has_scoped_permission(uid, permission, tenant_id=tenant_id, project_id=project_id):
            return uid
        raise PermissionError(f"权限不足：缺少所需权限 '{permission}'")

    # ------------------------------------------------------------------
    # 授权核心：有效权限解析
    # ------------------------------------------------------------------
    def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(role_id)

    def _role_permissions(self, role_id: str) -> Set[str]:
        role = self._roles.get(role_id)
        if role is None:
            return set()
        return set(role.permissions or [])

    def effective_permissions(
        self,
        uid: str,
        tenant_id: str = "",
        project_id: str = "",
    ) -> Set[str]:
        """用户在给定 scope 上下文下的有效权限并集。

        PLATFORM 绑定恒生效；TENANT 绑定仅当 tenant_id 匹配；PROJECT 绑定仅当
        project_id 匹配。scope 上下文为空时只计入 PLATFORM 绑定。
        """
        perms: Set[str] = set()
        if not uid:
            return perms
        for b in self._bindings.values():
            if b.user_id != uid or b.status != "ACTIVE":
                continue
            if b.scope == ScopeKind.PLATFORM:
                pass
            elif b.scope == ScopeKind.TENANT:
                if not tenant_id or b.tenant_id != tenant_id:
                    continue
            elif b.scope == ScopeKind.PROJECT:
                if not project_id or b.project_id != project_id:
                    continue
            else:
                continue
            perms |= self._role_permissions(b.role_id)
        return perms

    def is_platform_super(self, uid: str) -> bool:
        return "*" in self.effective_permissions(uid)

    def has_scoped_permission(
        self,
        uid: str,
        permission: str,
        tenant_id: str = "",
        project_id: str = "",
    ) -> bool:
        perms = self.effective_permissions(uid, tenant_id=tenant_id, project_id=project_id)
        return permission in perms or "*" in perms

    # ------------------------------------------------------------------
    # 绑定 primitives（幂等授权）
    # ------------------------------------------------------------------
    def _grant_binding(
        self,
        user_id: str,
        role_id: str,
        scope: ScopeKind,
        granted_by: str = "",
        tenant_id: str = "",
        project_id: str = "",
    ) -> RoleBinding:
        role = self._roles.get(role_id)
        if role is None:
            raise KeyError(f"角色不存在：{role_id}")
        if role.scope != scope:
            raise ValueError(f"角色 {role.code} 的 scope（{role.scope.value}）与授权范围（{scope.value}）不一致")
        if scope == ScopeKind.TENANT and not tenant_id:
            raise ValueError("租户角色授权必须指定租户")
        if scope == ScopeKind.PROJECT and not project_id:
            raise ValueError("项目角色授权必须指定项目")
        for b in self._bindings.values():
            if (
                b.user_id == user_id
                and b.role_id == role_id
                and b.tenant_id == tenant_id
                and b.project_id == project_id
            ):
                if b.status != "ACTIVE":
                    b.status = "ACTIVE"
                    domain_persistence.write(FAMILY_BINDINGS, b.binding_id, b)
                return b
        binding = RoleBinding(
            binding_id=_new_id("bnd"),
            user_id=user_id,
            role_id=role_id,
            scope=scope,
            tenant_id=tenant_id,
            project_id=project_id,
            granted_by=granted_by,
            granted_at=_now_iso(),
        )
        self._bindings[binding.binding_id] = binding
        domain_persistence.require(FAMILY_BINDINGS)
        domain_persistence.write(FAMILY_BINDINGS, binding.binding_id, binding)
        return binding

    def _revoke_bindings(
        self,
        user_id: str,
        scope: ScopeKind,
        tenant_id: str = "",
        project_id: str = "",
        keep_role_id: str = "",
    ) -> int:
        """撤销用户在给定 scope 下的绑定（可保留某角色）；返回撤销数量。"""
        removed = 0
        for b in list(self._bindings.values()):
            if b.user_id != user_id or b.scope != scope or b.status != "ACTIVE":
                continue
            if scope == ScopeKind.TENANT and b.tenant_id != tenant_id:
                continue
            if scope == ScopeKind.PROJECT and b.project_id != project_id:
                continue
            if keep_role_id and b.role_id == keep_role_id:
                continue
            b.status = "DISABLED"
            domain_persistence.write(FAMILY_BINDINGS, b.binding_id, b)
            removed += 1
        return removed

    # ------------------------------------------------------------------
    # 租户
    # ------------------------------------------------------------------
    def create_tenant(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._require_permission(context, P_PLATFORM_TENANT_MANAGE)
        code = str(payload.get("code") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not TENANT_CODE_PATTERN.match(code):
            raise ValueError("租户编码非法：2-32 位小写字母/数字/连字符，字母开头")
        if not name:
            raise ValueError("租户名称不能为空")
        if any(t.code == code for t in self._tenants.values()):
            raise ValueError(f"租户编码已存在：{code}")
        domain_persistence.require(FAMILY_TENANTS)
        tenant = Tenant(
            tenant_id=_new_id("tnt"),
            code=code,
            name=name,
            description=str(payload.get("description") or ""),
            created_by=actor,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        self._tenants[tenant.tenant_id] = tenant
        domain_persistence.write(FAMILY_TENANTS, tenant.tenant_id, tenant)
        # 创建人自动成为租户管理员
        self._grant_binding(actor, ROLE_TENANT_ADMIN, ScopeKind.TENANT, granted_by=actor, tenant_id=tenant.tenant_id)
        return tenant.model_dump()

    def update_tenant(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._require_permission(context, P_PLATFORM_TENANT_MANAGE)
        tenant = self._tenants.get(str(payload.get("tenant_id") or ""))
        if tenant is None:
            raise KeyError("租户不存在")
        if payload.get("name"):
            tenant.name = str(payload["name"]).strip()
        if "description" in payload:
            tenant.description = str(payload.get("description") or "")
        tenant.updated_at = _now_iso()
        domain_persistence.write(FAMILY_TENANTS, tenant.tenant_id, tenant)
        return tenant.model_dump()

    def set_tenant_status(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._require_permission(context, P_PLATFORM_TENANT_MANAGE)
        tenant = self._tenants.get(str(payload.get("tenant_id") or ""))
        if tenant is None:
            raise KeyError("租户不存在")
        status = str(payload.get("status") or "").strip().upper()
        if status not in ("ACTIVE", "SUSPENDED"):
            raise ValueError("租户状态仅支持 ACTIVE / SUSPENDED")
        tenant.status = status
        tenant.updated_at = _now_iso()
        domain_persistence.write(FAMILY_TENANTS, tenant.tenant_id, tenant)
        return tenant.model_dump()

    def list_tenants(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """平台管理者见全部租户；普通用户只见自己在册租户。"""
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        is_manager = has_permission(role, P_PLATFORM_TENANT_MANAGE) or self.is_platform_super(uid)
        rows = [t.model_dump() for t in self._tenants.values()]
        if not is_manager:
            mine = {b.tenant_id for b in self._bindings.values() if b.user_id == uid and b.scope == ScopeKind.TENANT and b.status == "ACTIVE"}
            rows = [r for r in rows if r["tenant_id"] in mine]
        rows.sort(key=lambda r: r["created_at"])
        return {"tenants": rows, "total": len(rows)}

    def tenant_members(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        uid = self._actor(context)
        tenant_id = str(payload.get("tenant_id") or "")
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise KeyError("租户不存在")
        if not (
            has_permission(normalize_role((context or {}).get("user_role", "")), P_PLATFORM_TENANT_MANAGE)
            or self.has_scoped_permission(uid, P_TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
            or self.has_scoped_permission(uid, P_TENANT_PROJECT_CREATE, tenant_id=tenant_id)
        ):
            raise PermissionError("权限不足：仅租户管理员或平台管理者可查看成员")
        rows = []
        for b in self._bindings.values():
            if b.scope != ScopeKind.TENANT or b.tenant_id != tenant_id or b.status != "ACTIVE":
                continue
            user = self._find_user(b.user_id) or {}
            role = self._roles.get(b.role_id)
            rows.append(
                {
                    "binding_id": b.binding_id,
                    "user_id": b.user_id,
                    "email": user.get("email", ""),
                    "nickname": user.get("nickname", ""),
                    "role_id": b.role_id,
                    "role_name": role.name if role else b.role_id,
                    "granted_at": b.granted_at,
                }
            )
        rows.sort(key=lambda r: r["granted_at"])
        return {"members": rows, "total": len(rows)}

    def add_tenant_member(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = str(payload.get("tenant_id") or "")
        if self._tenants.get(tenant_id) is None:
            raise KeyError("租户不存在")
        if self._tenants[tenant_id].status != "ACTIVE":
            raise ValueError("租户已停用，无法添加成员")
        actor = self._require_permission(context, P_TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
        user = self._resolve_user(payload)
        role_id = str(payload.get("role_id") or ROLE_TENANT_MEMBER)
        role = self._roles.get(role_id)
        if role is None or role.scope != ScopeKind.TENANT:
            raise ValueError("角色必须是租户域角色")
        if role.tenant_id and role.tenant_id != tenant_id:
            raise ValueError("自定义角色不属于该租户")
        binding = self._grant_binding(user["uid"], role_id, ScopeKind.TENANT, granted_by=actor, tenant_id=tenant_id)
        return binding.model_dump()

    def set_tenant_member_role(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = str(payload.get("tenant_id") or "")
        if self._tenants.get(tenant_id) is None:
            raise KeyError("租户不存在")
        actor = self._require_permission(context, P_TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
        user = self._resolve_user(payload)
        role_id = str(payload.get("role_id") or "")
        role = self._roles.get(role_id)
        if role is None or role.scope != ScopeKind.TENANT:
            raise ValueError("角色必须是租户域角色")
        if role.tenant_id and role.tenant_id != tenant_id:
            raise ValueError("自定义角色不属于该租户")
        self._assert_tenant_admin_remains(tenant_id, excluding_user=user["uid"], next_role_id=role_id)
        self._revoke_bindings(user["uid"], ScopeKind.TENANT, tenant_id=tenant_id)
        binding = self._grant_binding(user["uid"], role_id, ScopeKind.TENANT, granted_by=actor, tenant_id=tenant_id)
        return binding.model_dump()

    def remove_tenant_member(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = str(payload.get("tenant_id") or "")
        if self._tenants.get(tenant_id) is None:
            raise KeyError("租户不存在")
        actor = self._require_permission(context, P_TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
        user = self._resolve_user(payload)
        self._assert_tenant_admin_remains(tenant_id, excluding_user=user["uid"], next_role_id="")
        removed = self._revoke_bindings(user["uid"], ScopeKind.TENANT, tenant_id=tenant_id)
        # 成员移出租户时同步移出该租户下所有项目
        tenant_project_ids = {p.project_id for p in self._projects.values() if p.tenant_id == tenant_id}
        for b in list(self._bindings.values()):
            if b.user_id == user["uid"] and b.scope == ScopeKind.PROJECT and b.project_id in tenant_project_ids and b.status == "ACTIVE":
                b.status = "DISABLED"
                domain_persistence.write(FAMILY_BINDINGS, b.binding_id, b)
        return {"removed": removed}

    def _assert_tenant_admin_remains(self, tenant_id: str, excluding_user: str, next_role_id: str) -> None:
        if next_role_id == ROLE_TENANT_ADMIN:
            return
        admins = [
            b for b in self._bindings.values()
            if b.scope == ScopeKind.TENANT and b.tenant_id == tenant_id
            and b.status == "ACTIVE" and b.role_id == ROLE_TENANT_ADMIN and b.user_id != excluding_user
        ]
        if not admins:
            raise ValueError("租户至少保留一名租户管理员")

    # ------------------------------------------------------------------
    # 项目
    # ------------------------------------------------------------------
    def create_project(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = str(payload.get("tenant_id") or "")
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise KeyError("租户不存在")
        if tenant.status != "ACTIVE":
            raise ValueError("租户已停用，无法创建项目")
        actor = self._require_permission(context, P_TENANT_PROJECT_CREATE, tenant_id=tenant_id)
        key = str(payload.get("key") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not PROJECT_KEY_PATTERN.match(key):
            raise ValueError("项目标识非法：2-32 位小写字母/数字/连字符，字母开头")
        if not name:
            raise ValueError("项目名称不能为空")
        if any(p.tenant_id == tenant_id and p.key == key for p in self._projects.values()):
            raise ValueError(f"项目标识在租户内已存在：{key}")
        domain_persistence.require(FAMILY_PROJECTS)
        project = Project(
            project_id=_new_id("prj"),
            tenant_id=tenant_id,
            key=key,
            name=name,
            description=str(payload.get("description") or ""),
            created_by=actor,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        self._projects[project.project_id] = project
        domain_persistence.write(FAMILY_PROJECTS, project.project_id, project)
        # 创建人自动成为项目所有者
        self._grant_binding(actor, ROLE_PROJECT_OWNER, ScopeKind.PROJECT, granted_by=actor, project_id=project.project_id)
        return project.model_dump()

    def update_project(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        project = self._require_project(payload, context)
        if payload.get("name"):
            project.name = str(payload["name"]).strip()
        if "description" in payload:
            project.description = str(payload.get("description") or "")
        project.updated_at = _now_iso()
        domain_persistence.write(FAMILY_PROJECTS, project.project_id, project)
        return project.model_dump()

    def set_project_status(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        project = self._require_project(payload, context)
        status = str(payload.get("status") or "").strip().upper()
        if status not in ("ACTIVE", "ARCHIVED"):
            raise ValueError("项目状态仅支持 ACTIVE / ARCHIVED")
        project.status = status
        project.updated_at = _now_iso()
        domain_persistence.write(FAMILY_PROJECTS, project.project_id, project)
        return project.model_dump()

    def _require_project(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Project:
        project = self._projects.get(str(payload.get("project_id") or ""))
        if project is None:
            raise KeyError("项目不存在")
        uid = self._actor(context)
        if not (
            has_permission(normalize_role((context or {}).get("user_role", "")), P_PLATFORM_TENANT_MANAGE)
            or self.has_scoped_permission(uid, "project:manage", project_id=project.project_id)
            or self.has_scoped_permission(uid, P_TENANT_MEMBER_MANAGE, tenant_id=project.tenant_id)
        ):
            raise PermissionError("权限不足：仅项目所有者、租户管理员或平台管理者可管理项目")
        return project

    def list_projects(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        uid = self._actor(context)
        visible = self._visible_projects(uid)
        tenant_filter = str(payload.get("tenant_id") or "")
        if tenant_filter:
            visible = [p for p in visible if p.tenant_id == tenant_filter]
        rows = []
        for p in sorted(visible, key=lambda x: x.created_at):
            row = p.model_dump()
            row["my_role"] = self._project_role_name(uid, p)
            rows.append(row)
        return {"projects": rows, "total": len(rows)}

    def _visible_projects(self, uid: str) -> List[Project]:
        """可见项目 = 有 PROJECT 绑定的项目 ∪ 在册租户下的全部 ACTIVE 项目。"""
        project_ids = {
            b.project_id for b in self._bindings.values()
            if b.user_id == uid and b.scope == ScopeKind.PROJECT and b.status == "ACTIVE"
        }
        tenant_ids = {
            b.tenant_id for b in self._bindings.values()
            if b.user_id == uid and b.scope == ScopeKind.TENANT and b.status == "ACTIVE"
        }
        rows = []
        for p in self._projects.values():
            if p.project_id in project_ids or (p.tenant_id in tenant_ids and p.status == "ACTIVE"):
                rows.append(p)
        return rows

    def _project_role_name(self, uid: str, project: Project) -> str:
        for b in self._bindings.values():
            if (
                b.user_id == uid and b.scope == ScopeKind.PROJECT
                and b.project_id == project.project_id and b.status == "ACTIVE"
            ):
                role = self._roles.get(b.role_id)
                return role.name if role else b.role_id
        return ""

    def project_members(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        project = self._projects.get(str(payload.get("project_id") or ""))
        if project is None:
            raise KeyError("项目不存在")
        uid = self._actor(context)
        if not (
            has_permission(normalize_role((context or {}).get("user_role", "")), P_PLATFORM_TENANT_MANAGE)
            or self.has_scoped_permission(uid, "project:member_manage", project_id=project.project_id)
            or self.has_scoped_permission(uid, P_TENANT_MEMBER_MANAGE, tenant_id=project.tenant_id)
        ):
            raise PermissionError("权限不足：仅项目所有者、租户管理员或平台管理者可查看成员")
        rows = []
        for b in self._bindings.values():
            if b.scope != ScopeKind.PROJECT or b.project_id != project.project_id or b.status != "ACTIVE":
                continue
            user = self._find_user(b.user_id) or {}
            role = self._roles.get(b.role_id)
            rows.append(
                {
                    "binding_id": b.binding_id,
                    "user_id": b.user_id,
                    "email": user.get("email", ""),
                    "nickname": user.get("nickname", ""),
                    "role_id": b.role_id,
                    "role_name": role.name if role else b.role_id,
                    "granted_at": b.granted_at,
                }
            )
        rows.sort(key=lambda r: r["granted_at"])
        return {"members": rows, "total": len(rows)}

    def add_project_member(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        project = self._projects.get(str(payload.get("project_id") or ""))
        if project is None:
            raise KeyError("项目不存在")
        if project.status != "ACTIVE":
            raise ValueError("项目已归档，无法添加成员")
        actor = self._require_project_member_manage(context, project)
        user = self._resolve_user(payload)
        # 项目成员必须先在册于所属租户（组织归属一致性）
        in_tenant = any(
            b.user_id == user["uid"] and b.scope == ScopeKind.TENANT
            and b.tenant_id == project.tenant_id and b.status == "ACTIVE"
            for b in self._bindings.values()
        )
        if not in_tenant:
            raise ValueError("该用户尚未加入项目所属租户，请先添加为租户成员")
        role_id = str(payload.get("role_id") or ROLE_PROJECT_VIEWER)
        role = self._roles.get(role_id)
        if role is None or role.scope != ScopeKind.PROJECT:
            raise ValueError("角色必须是项目域角色")
        binding = self._grant_binding(user["uid"], role_id, ScopeKind.PROJECT, granted_by=actor, project_id=project.project_id)
        return binding.model_dump()

    def set_project_member_role(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        project = self._projects.get(str(payload.get("project_id") or ""))
        if project is None:
            raise KeyError("项目不存在")
        actor = self._require_project_member_manage(context, project)
        user = self._resolve_user(payload)
        role_id = str(payload.get("role_id") or "")
        role = self._roles.get(role_id)
        if role is None or role.scope != ScopeKind.PROJECT:
            raise ValueError("角色必须是项目域角色")
        self._assert_project_owner_remains(project.project_id, excluding_user=user["uid"], next_role_id=role_id)
        self._revoke_bindings(user["uid"], ScopeKind.PROJECT, project_id=project.project_id)
        binding = self._grant_binding(user["uid"], role_id, ScopeKind.PROJECT, granted_by=actor, project_id=project.project_id)
        return binding.model_dump()

    def remove_project_member(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        project = self._projects.get(str(payload.get("project_id") or ""))
        if project is None:
            raise KeyError("项目不存在")
        self._require_project_member_manage(context, project)
        user = self._resolve_user(payload)
        self._assert_project_owner_remains(project.project_id, excluding_user=user["uid"], next_role_id="")
        removed = self._revoke_bindings(user["uid"], ScopeKind.PROJECT, project_id=project.project_id)
        return {"removed": removed}

    def _require_project_member_manage(self, context: Dict[str, Any], project: Project) -> str:
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        if has_permission(role, P_PLATFORM_TENANT_MANAGE):
            return uid
        if self.has_scoped_permission(uid, "project:member_manage", project_id=project.project_id):
            return uid
        if self.has_scoped_permission(uid, P_TENANT_MEMBER_MANAGE, tenant_id=project.tenant_id):
            return uid
        raise PermissionError("权限不足：仅项目所有者、租户管理员或平台管理者可管理项目成员")

    def _assert_project_owner_remains(self, project_id: str, excluding_user: str, next_role_id: str) -> None:
        if next_role_id == ROLE_PROJECT_OWNER:
            return
        owners = [
            b for b in self._bindings.values()
            if b.scope == ScopeKind.PROJECT and b.project_id == project_id
            and b.status == "ACTIVE" and b.role_id == ROLE_PROJECT_OWNER and b.user_id != excluding_user
        ]
        if not owners:
            raise ValueError("项目至少保留一名项目所有者")

    # ------------------------------------------------------------------
    # 角色管理（可配置 RBAC）
    # ------------------------------------------------------------------
    def list_roles(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self._actor(context)
        scope = str(payload.get("scope") or "").strip().upper()
        tenant_id = str(payload.get("tenant_id") or "")
        rows = []
        for r in self._roles.values():
            if scope and r.scope.value != scope:
                continue
            if tenant_id and r.tenant_id and r.tenant_id != tenant_id:
                continue
            rows.append(r.model_dump())
        rows.sort(key=lambda r: (r["scope"], r["builtin"] is False, r["code"]))
        return {"roles": rows, "total": len(rows)}

    def permission_catalog(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self._actor(context)
        items = [
            {"permission": p, "builtin_role": self._permission_builtin_role(p)}
            for p in sorted(ALL_PERMISSIONS)
        ]
        return {"permissions": items, "total": len(items)}

    def _permission_builtin_role(self, permission: str) -> str:
        if permission in USER_PERMISSIONS:
            return "MAKER"
        return "ADMIN"

    def create_role(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        scope_raw = str(payload.get("scope") or "").strip().upper()
        if scope_raw not in (ScopeKind.TENANT.value, ScopeKind.PROJECT.value):
            raise ValueError("自定义角色仅支持 TENANT / PROJECT 域（平台域角色由平台管理者经内置角色管理）")
        tenant_id = str(payload.get("tenant_id") or "")
        if not tenant_id:
            raise ValueError("自定义角色必须归属一个租户")
        self._require_role_manage(context, tenant_id)
        code = str(payload.get("code") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not ROLE_CODE_PATTERN.match(code):
            raise ValueError("角色编码非法：2-48 位小写字母/数字/下划线，字母开头")
        if not name:
            raise ValueError("角色名称不能为空")
        if any(
            r.scope.value == scope_raw and r.code == code and r.tenant_id == tenant_id
            for r in self._roles.values()
        ):
            raise ValueError(f"角色编码已存在：{code}")
        permissions = self._validate_permissions(payload.get("permissions") or [])
        domain_persistence.require(FAMILY_ROLES)
        role = Role(
            role_id=_new_id("rol"),
            scope=ScopeKind(scope_raw),
            code=code,
            name=name,
            description=str(payload.get("description") or ""),
            permissions=permissions,
            builtin=False,
            tenant_id=tenant_id,
            created_by=self._actor(context),
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        self._roles[role.role_id] = role
        domain_persistence.write(FAMILY_ROLES, role.role_id, role)
        return role.model_dump()

    def update_role(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        role = self._roles.get(str(payload.get("role_id") or ""))
        if role is None:
            raise KeyError("角色不存在")
        if role.builtin:
            raise PermissionError("内置角色不可修改（平台内置权限语义由代码保证）")
        self._require_role_manage(context, role.tenant_id)
        if payload.get("name"):
            role.name = str(payload["name"]).strip()
        if "description" in payload:
            role.description = str(payload.get("description") or "")
        if "permissions" in payload:
            role.permissions = self._validate_permissions(payload.get("permissions") or [])
        role.updated_at = _now_iso()
        domain_persistence.write(FAMILY_ROLES, role.role_id, role)
        return role.model_dump()

    def delete_role(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        role = self._roles.get(str(payload.get("role_id") or ""))
        if role is None:
            raise KeyError("角色不存在")
        if role.builtin:
            raise PermissionError("内置角色不可删除")
        self._require_role_manage(context, role.tenant_id)
        in_use = any(b.role_id == role.role_id and b.status == "ACTIVE" for b in self._bindings.values())
        if in_use:
            raise ValueError("角色仍有生效中的授权绑定，请先调整成员角色后再删除")
        domain_persistence.delete(FAMILY_ROLES, role.role_id)
        self._roles.pop(role.role_id, None)
        return {"deleted": role.role_id}

    def _require_role_manage(self, context: Dict[str, Any], tenant_id: str) -> str:
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        if has_permission(role, P_PLATFORM_ROLE_MANAGE):
            return uid
        if tenant_id and self.has_scoped_permission(uid, P_TENANT_ROLE_MANAGE, tenant_id=tenant_id):
            return uid
        raise PermissionError("权限不足：仅平台管理者或租户管理员可管理角色")

    def _validate_permissions(self, permissions: Any) -> List[str]:
        if not isinstance(permissions, list):
            raise ValueError("权限必须是权限点列表")
        cleaned: List[str] = []
        for p in permissions:
            p = str(p).strip()
            if not p:
                continue
            if p != "*" and p not in ALL_PERMISSIONS:
                raise ValueError(f"未知权限点：{p}")
            if p not in cleaned:
                cleaned.append(p)
        return cleaned

    # ------------------------------------------------------------------
    # 我的 scope（驱动前端租户/项目切换器）
    # ------------------------------------------------------------------
    def my_scope(self, context: Dict[str, Any]) -> Dict[str, Any]:
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        is_super = role == "ADMIN" or self.is_platform_super(uid)

        def _role_summary(role_id: str) -> Dict[str, Any]:
            r = self._roles.get(role_id)
            return {
                "role_id": role_id,
                "name": r.name if r else role_id,
                "code": r.code if r else "",
                "permissions": sorted(r.permissions or []) if r else [],
            }

        tenants: List[Dict[str, Any]] = []
        for b in self._bindings.values():
            if b.user_id != uid or b.scope != ScopeKind.TENANT or b.status != "ACTIVE":
                continue
            tenant = self._tenants.get(b.tenant_id)
            if tenant is None:
                continue
            tenants.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "code": tenant.code,
                    "name": tenant.name,
                    "status": tenant.status,
                    "role": _role_summary(b.role_id),
                }
            )
        projects: List[Dict[str, Any]] = []
        for p in self._visible_projects(uid):
            tenant = self._tenants.get(p.tenant_id)
            projects.append(
                {
                    "project_id": p.project_id,
                    "tenant_id": p.tenant_id,
                    "tenant_name": tenant.name if tenant else "",
                    "key": p.key,
                    "name": p.name,
                    "status": p.status,
                    "role": _role_summary(self._project_role_id(uid, p.project_id)),
                }
            )
        platform_roles = [_role_summary(b.role_id) for b in self._bindings.values() if b.user_id == uid and b.scope == ScopeKind.PLATFORM and b.status == "ACTIVE"]
        return {
            "user_id": uid,
            "is_platform_super": is_super,
            "tenants": tenants,
            "projects": projects,
            "platform_roles": platform_roles,
        }

    def _project_role_id(self, uid: str, project_id: str) -> str:
        for b in self._bindings.values():
            if (
                b.user_id == uid and b.scope == ScopeKind.PROJECT
                and b.project_id == project_id and b.status == "ACTIVE"
            ):
                return b.role_id
        return ""

    # ------------------------------------------------------------------
    # 用户管理（平台级）
    # ------------------------------------------------------------------
    @staticmethod
    def _find_user(uid_or_email: str) -> Optional[Dict[str, Any]]:
        from src.domains.user.entities import account_entity

        key = str(uid_or_email or "").strip()
        if not key:
            return None
        doc = account_entity.adapter.get(key)
        if doc:
            return doc
        lowered = key.lower()
        for row in account_entity.adapter.all():
            if str(row.get("email", "")).lower() == lowered:
                return row
        return None

    def _resolve_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self._find_user(str(payload.get("user_id") or payload.get("email") or ""))
        if user is None:
            raise KeyError("用户不存在")
        if user.get("is_active") is False and payload.get("allow_inactive") is not True:
            raise ValueError("用户已被停用")
        return user

    @staticmethod
    def _sanitize_user(doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "uid": doc.get("uid", ""),
            "email": doc.get("email", ""),
            "nickname": doc.get("nickname", ""),
            "role": doc.get("role", ""),
            "account_type": doc.get("account_type", ""),
            "company_name": doc.get("company_name", ""),
            "is_active": doc.get("is_active", True),
            "created_at": doc.get("created_at", ""),
        }

    def list_users(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self._require_permission(context, P_PLATFORM_USER_MANAGE)
        from src.domains.user.entities import account_entity

        q = str(payload.get("q") or "").strip().lower()
        rows = []
        for doc in account_entity.adapter.all():
            if q and q not in str(doc.get("email", "")).lower() and q not in str(doc.get("nickname", "")).lower() and q not in str(doc.get("uid", "")).lower():
                continue
            rows.append(self._sanitize_user(doc))
        rows.sort(key=lambda r: r.get("created_at") or "")
        limit = int(payload.get("limit") or 100)
        return {"users": rows[:limit], "total": len(rows)}

    def set_user_role(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._require_permission(context, P_PLATFORM_USER_MANAGE)
        from src.domains.user.entities import account_entity

        user = self._resolve_user(payload)
        uid = user["uid"]
        if uid == BUILTIN_ADMIN_UID:
            raise ValueError("内置平台管理员的角色不可变更")
        new_role = str(payload.get("role") or "").strip().upper()
        if new_role not in LEGACY_ROLES:
            raise ValueError("平台角色仅支持 ADMIN / MAKER / GUEST")
        if uid == actor and new_role != "ADMIN":
            raise ValueError("不能降级自己的平台角色")
        doc = dict(user)
        doc["role"] = new_role
        account_entity.adapter.update(uid, doc)
        return self._sanitize_user(doc)

    def set_user_active(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._require_permission(context, P_PLATFORM_USER_MANAGE)
        from src.domains.user.entities import account_entity

        user = self._resolve_user(payload)
        uid = user["uid"]
        if uid == BUILTIN_ADMIN_UID:
            raise ValueError("内置平台管理员不可停用")
        active = bool(payload.get("is_active", True))
        if uid == actor and not active:
            raise ValueError("不能停用自己的账号")
        doc = dict(user)
        doc["is_active"] = active
        account_entity.adapter.update(uid, doc)
        return self._sanitize_user(doc)

    def reset_user_password(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self._require_permission(context, P_PLATFORM_USER_MANAGE)
        from src.core.security import hash_password
        from src.domains.user.entities import account_entity

        user = self._resolve_user(payload)
        new_password = str(payload.get("new_password") or "")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"新密码长度至少 {MIN_PASSWORD_LENGTH} 位")
        doc = dict(user)
        doc["password_hash"] = hash_password(new_password)
        doc["must_change_password"] = True  # 强制首次登录轮换
        account_entity.adapter.update(user["uid"], doc)
        return {"uid": user["uid"], "must_change_password": True}

    # ------------------------------------------------------------------
    # Hydration（启动时由 domain_persistence 回放重建索引）
    # ------------------------------------------------------------------
    def hydrate_tenants(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            tenant = Tenant(**row)
            self._tenants[tenant.tenant_id] = tenant
        return len(rows)

    def hydrate_projects(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            project = Project(**row)
            self._projects[project.project_id] = project
        return len(rows)

    def hydrate_roles(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            role = Role(**row)
            self._roles.setdefault(role.role_id, role)
        return len(rows)

    def hydrate_bindings(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            binding = RoleBinding(**row)
            self._bindings[binding.binding_id] = binding
        return len(rows)


platform_service = PlatformService()

domain_persistence.register(FAMILY_TENANTS, platform_service.hydrate_tenants)
domain_persistence.register(FAMILY_PROJECTS, platform_service.hydrate_projects)
domain_persistence.register(FAMILY_ROLES, platform_service.hydrate_roles)
domain_persistence.register(FAMILY_BINDINGS, platform_service.hydrate_bindings)
