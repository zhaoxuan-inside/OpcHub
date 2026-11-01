"""平台治理场景适配器：网关统一分发的薄壳（payload/context → platform_service）。

管理类场景的权限声明见 backend/config/gateway_routes.yaml 第 14 节；双重权威
（平台 OR 租户/项目 scope）的成员与角色操作由 service 层自行断言。
"""
from typing import Any, Dict

from src.core.rbac import P_PLATFORM_AUDIT_READ, P_PLATFORM_TENANT_MANAGE, has_permission, normalize_role
from src.domains.platform.service import platform_service


# ---------------------------------------------------------------------------
# 我的 scope（前端租户/项目切换器数据源）
# ---------------------------------------------------------------------------
def platform_scope_my_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.my_scope(context)


# ---------------------------------------------------------------------------
# 租户
# ---------------------------------------------------------------------------
def platform_tenant_create_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.create_tenant(payload or {}, context)


def platform_tenant_update_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.update_tenant(payload or {}, context)


def platform_tenant_status_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.set_tenant_status(payload or {}, context)


def platform_tenant_list_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.list_tenants(payload or {}, context)


def platform_tenant_members_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.tenant_members(payload or {}, context)


def platform_tenant_member_add_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.add_tenant_member(payload or {}, context)


def platform_tenant_member_set_role_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.set_tenant_member_role(payload or {}, context)


def platform_tenant_member_remove_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.remove_tenant_member(payload or {}, context)


# ---------------------------------------------------------------------------
# 项目
# ---------------------------------------------------------------------------
def platform_project_create_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.create_project(payload or {}, context)


def platform_project_update_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.update_project(payload or {}, context)


def platform_project_status_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.set_project_status(payload or {}, context)


def platform_project_list_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.list_projects(payload or {}, context)


def platform_project_members_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.project_members(payload or {}, context)


def platform_project_member_add_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.add_project_member(payload or {}, context)


def platform_project_member_set_role_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.set_project_member_role(payload or {}, context)


def platform_project_member_remove_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.remove_project_member(payload or {}, context)


# ---------------------------------------------------------------------------
# 角色与权限点（可配置 RBAC）
# ---------------------------------------------------------------------------
def platform_role_list_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.list_roles(payload or {}, context)


def platform_role_create_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.create_role(payload or {}, context)


def platform_role_update_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.update_role(payload or {}, context)


def platform_role_delete_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.delete_role(payload or {}, context)


def platform_permissions_list_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.permission_catalog(payload or {}, context)


# ---------------------------------------------------------------------------
# 用户管理（平台级）
# ---------------------------------------------------------------------------
def platform_user_list_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.list_users(payload or {}, context)


def platform_user_set_role_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.set_user_role(payload or {}, context)


def platform_user_set_active_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.set_user_active(payload or {}, context)


def platform_user_reset_password_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return platform_service.reset_user_password(payload or {}, context)


# ---------------------------------------------------------------------------
# 审计日志检索（运维平台数据源）
# ---------------------------------------------------------------------------
def _is_platform_auditor(context: Dict[str, Any]) -> bool:
    uid = str((context or {}).get("user_id") or "")
    if not uid:
        return False
    if has_permission(normalize_role((context or {}).get("user_role", "")), P_PLATFORM_TENANT_MANAGE):
        return True
    return platform_service.has_scoped_permission(uid, P_PLATFORM_AUDIT_READ)


async def platform_audit_list_adapter(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_platform_auditor(context):
        raise PermissionError("权限不足：缺少所需权限 'platform:audit_read'")
    from src.core.audit import audit_service

    payload = payload or {}
    limit = max(1, min(int(payload.get("limit") or 100), 500))
    logs = await audit_service.list_logs(
        limit=limit,
        actor_id=str(payload.get("actor_id") or "") or None,
        action=str(payload.get("action") or "") or None,
    )
    return {"logs": logs, "total": len(logs)}
