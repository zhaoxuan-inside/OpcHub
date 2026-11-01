"""平台治理场景适配器：网关统一分发的薄壳。

* 读场景直连 handler（payload/context → platform_service），符合框架"读直连"约定；
* 写场景统一经 OPC_PLATFORM_GOVERNANCE_PIPELINE 的 guard → persist → telemetry
  算子链执行（platform_write_adapter），载荷须 {action, payload} 信封。

权限声明见 backend/config/gateway_routes.yaml 第 14 节；双重权威（平台 OR
租户/项目 scope）的成员与角色操作由 service 层自行断言。
"""
from typing import Any, Dict

from src.core.rbac import P_PLATFORM_AUDIT_READ, P_PLATFORM_TENANT_MANAGE, has_permission, normalize_role
from src.domains.platform.service import platform_service


def _actor_display_name(uid: str) -> str:
    from src.domains.user.entities import account_entity

    doc = account_entity.adapter.get(uid) if uid else None
    return str((doc or {}).get("nickname") or (doc or {}).get("email") or uid)


async def platform_write_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Execute one platform governance mutation via OPC_PLATFORM_GOVERNANCE_PIPELINE.

    写走 DAG：guard（动作/身份）→ persist（双重权威断言 + 变更）→ telemetry。
    引擎会把节点异常压平成字符串，这里把节点前缀剥掉并按 error_type 还原
    语义化错误（PermissionError→403 / KeyError→404 / ValueError→400）。
    """
    from src.domains.orchestration.models import ScenarioExecuteRequest
    from src.domains.orchestration.service import orchestration_service
    from src.domains.platform.governance_ops import ensure_platform_pipeline

    # 元管线幂等自愈（治理算子模块可能此前从未导入）
    ensure_platform_pipeline()

    action = str((p or {}).get("action") or "")
    ctx = dict(c or {})
    uid = str(ctx.get("user_id") or "")
    if uid:
        ctx.setdefault("user_name", _actor_display_name(uid))

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PLATFORM_GOVERNANCE_PIPELINE",
            version="v1.0.0",
            inputs={"action": action, "payload": (p or {}).get("payload") or {}},
            context=ctx,
        )
    )
    if res.status != "SUCCESS":
        message = res.error_message or "Platform governance pipeline failed"
        # 剥掉执行引擎附加的英文节点前缀，把校验原文（中文）交给前端展示
        for prefix in (
            "Node step_persist execution error: ",
            "Node step_guard execution error: ",
            "Guard check failed: ",
        ):
            if message.startswith(prefix):
                message = message[len(prefix):]
                break
        # error_type 由算子桥忠实携带原始异常类（PermissionError/KeyError/ValueError），
        # 不用消息关键词猜测（"未知权限点" 一类文案会误伤启发式）
        if res.error_type == "PermissionError":
            raise PermissionError(message)
        if res.error_type == "KeyError":
            raise KeyError(message)
        raise ValueError(message)
    return res.final_output.get("platform_result") or res.final_output


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
        result=str(payload.get("result") or "") or None,
        since=str(payload.get("since") or "") or None,
    )
    return {"logs": logs, "total": len(logs)}


# 与目录元管线同构：模块导入即幂等种子，flow_engine 启动构建时纳入 release；
# 写适配器每次写操作前仍会显式重调（懒加载自愈）。
from src.domains.platform.governance_ops import ensure_platform_pipeline as _ensure

_ensure()
