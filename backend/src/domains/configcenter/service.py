"""配置中心服务：命名空间 / 配置项 / 版本机 / 灰度发布 / 生效值解析。

* 版本机沿用编排目录先例：DRAFT → PUBLISHED → SUPERSEDED；发布携带灰度参数
  （百分比分桶 + uid 白名单），命中灰度取灰度内容，否则取最近稳定版；
  percent=100 全量发布即把该版本提升为稳定版。
* resolve 是宿主运行时数据面高频调用（读直连 handler）：按 (命名空间, 键, 用户)
  确定性解析生效值，不存在时诚实返回 NOT_FOUND 而不报错。
* 权限：管理操作由网关声明 configcenter:read/write + scope:project 强制，
  服务层以 platform 绑定纵深复核。
"""
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.rbac import P_CONFIGCENTER_WRITE, has_permission, normalize_role
from src.domains.configcenter.models import ConfigItem, ConfigNamespace, ConfigVersion, GrayRelease
from src.infrastructure.database.persistence import domain_persistence

FAMILY_NAMESPACES = "configcenter.namespaces"
FAMILY_ITEMS = "configcenter.items"

NS_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,47}$")
ITEM_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{1,63}$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def gray_bucket_of(namespace: str, item_key: str, user_id: str) -> int:
    """灰度稳定分桶（与实验域同构的确定性算法，域内自持避免跨域依赖）。"""
    digest = hashlib.sha256(f"{namespace}:{item_key}:{user_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 10000


def resolve_content(item: ConfigItem, user_id: str, env: str = "") -> Dict[str, Any]:
    """确定性解析生效值（按环境）：白名单/灰度桶 → 灰度内容；否则该环境稳定版。"""
    gray = item.gray_env.get(env) or item.gray_env.get("")
    if gray and user_id:
        in_whitelist = user_id in (gray.whitelist or [])
        hit_bucket = gray_bucket_of(item.namespace, item.key, user_id) % 100 < gray.percent
        if in_whitelist or hit_bucket:
            return {"value": gray.content, "source": "GRAY", "version": gray.version}
    stable_version = item.stable_env.get(env) or item.stable_env.get("") or ""
    if stable_version:
        for v in item.versions:
            if v.version == stable_version:
                return {"value": v.content, "source": "STABLE", "version": v.version}
    return {"value": "", "source": "NOT_FOUND", "version": ""}


class ConfigCenterService:
    """命名空间与配置项注册表（内存索引为运行时读路径）。"""

    def __init__(self) -> None:
        self._namespaces: Dict[str, ConfigNamespace] = {}  # key → ns
        self._items: Dict[str, ConfigItem] = {}  # f"{ns}:{key}" → item

    # ------------------------------------------------------------------
    # 权限与隔离 helpers（与编排目录/实验域同构）
    # ------------------------------------------------------------------
    @staticmethod
    def _actor(context: Optional[Dict[str, Any]]) -> str:
        uid = str((context or {}).get("user_id") or "").strip()
        if not uid:
            raise PermissionError("UNAUTHORIZED:配置中心操作需要登录身份")
        return uid

    @staticmethod
    def _ctx_project(context: Optional[Dict[str, Any]]) -> str:
        return str((context or {}).get("project_id") or "").strip()

    @staticmethod
    def _is_super(context: Optional[Dict[str, Any]]) -> bool:
        if str((context or {}).get("user_role") or "").strip().upper() == "ADMIN":
            return True
        uid = str((context or {}).get("user_id") or "").strip()
        if not uid:
            return False
        try:
            from src.domains.platform.service import platform_service

            return platform_service.is_platform_super(uid)
        except Exception:
            return False

    def _require_write(self, context: Optional[Dict[str, Any]], project_id: str) -> str:
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        if has_permission(role, P_CONFIGCENTER_WRITE):
            return uid
        try:
            from src.domains.platform.service import platform_service

            if platform_service.has_scoped_permission(uid, P_CONFIGCENTER_WRITE, project_id=project_id):
                return uid
        except Exception:
            pass
        raise PermissionError("权限不足：缺少所需权限 'configcenter:write'")

    def _visible(self, project_id: str, ctx_project: str) -> bool:
        return (not project_id) or (not ctx_project) or project_id == ctx_project

    # ------------------------------------------------------------------
    # 命名空间
    # ------------------------------------------------------------------
    def create_namespace(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ctx_project = self._ctx_project(context)
        actor = self._require_write(context, ctx_project)
        key = str(payload.get("key") or "").strip()
        if not NS_KEY_PATTERN.match(key):
            raise ValueError("命名空间标识非法：2-48 位小写字母/数字/下划线/横线，字母开头")
        if key in self._namespaces:
            raise ValueError(f"命名空间已存在：{key}")
        domain_persistence.require(FAMILY_NAMESPACES)
        now = _now_iso()
        ns = ConfigNamespace(
            namespace_id=_new_id("ns"),
            key=key,
            name=str(payload.get("name") or key),
            description=str(payload.get("description") or ""),
            project_id=ctx_project,
            created_by=actor,
            created_at=now,
            updated_at=now,
        )
        self._namespaces[key] = ns
        domain_persistence.write(FAMILY_NAMESPACES, key, ns)
        return ns.model_dump()

    def update_namespace(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ns = self._require_namespace(payload, context, write=True)
        if payload.get("name"):
            ns.name = str(payload["name"])
        if "description" in payload:
            ns.description = str(payload.get("description") or "")
        ns.updated_at = _now_iso()
        domain_persistence.write(FAMILY_NAMESPACES, ns.key, ns)
        return ns.model_dump()

    def delete_namespace(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ns = self._require_namespace(payload, context, write=True)
        if any(i.namespace == ns.key for i in self._items.values()):
            raise ValueError("命名空间下仍有配置项，请先清空")
        domain_persistence.delete(FAMILY_NAMESPACES, ns.key)
        self._namespaces.pop(ns.key, None)
        return {"deleted": ns.key}

    def list_namespaces(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ctx_project = self._ctx_project(context)
        rows = [n.model_dump() for n in self._namespaces.values() if self._visible(n.project_id, ctx_project)]
        rows.sort(key=lambda r: r["created_at"])
        return {"namespaces": rows, "total": len(rows)}

    # ------------------------------------------------------------------
    # 配置项与版本机
    # ------------------------------------------------------------------
    def create_item(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ns_key = str(payload.get("namespace") or "").strip()
        ns = self._namespaces.get(ns_key)
        if ns is None:
            raise KeyError(f"命名空间 {ns_key} 不存在")
        actor = self._require_write(context, ns.project_id)
        key = str(payload.get("key") or "").strip()
        if not ITEM_KEY_PATTERN.match(key):
            raise ValueError("配置键非法：字母开头，仅字母/数字/下划线/点号/横线，长度 2-64")
        item_key = f"{ns_key}:{key}"
        if item_key in self._items:
            raise ValueError(f"配置键已存在：{key}")
        content, value_type = self._validate_content(payload.get("content") or "", str(payload.get("value_type") or "JSON"))
        domain_persistence.require(FAMILY_ITEMS)
        now = _now_iso()
        item = ConfigItem(
            item_id=_new_id("cfg"),
            namespace=ns_key,
            key=key,
            name=str(payload.get("name") or key),
            value_type=value_type,
            description=str(payload.get("description") or ""),
            versions=[ConfigVersion(
                version=str(payload.get("version") or "v1.0.0"),
                status="DRAFT",
                content=content,
                changelog=str(payload.get("changelog") or "初始版本"),
                created_by=actor,
                created_at=now,
            )],
            project_id=ns.project_id,
            created_by=actor,
            created_at=now,
            updated_at=now,
        )
        self._items[item_key] = item
        domain_persistence.write(FAMILY_ITEMS, item_key, item)
        return item.model_dump()

    def update_item(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        item = self._require_item(payload, context, write=True)
        if payload.get("name"):
            item.name = str(payload["name"])
        if "description" in payload:
            item.description = str(payload.get("description") or "")
        item.updated_at = _now_iso()
        domain_persistence.write(FAMILY_ITEMS, f"{item.namespace}:{item.key}", item)
        return item.model_dump()

    def delete_item(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        item = self._require_item(payload, context, write=True)
        domain_persistence.delete(FAMILY_ITEMS, f"{item.namespace}:{item.key}")
        self._items.pop(f"{item.namespace}:{item.key}", None)
        return {"deleted": item.key}

    def save_item_version(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        item = self._require_item(payload, context, write=True)
        content, _ = self._validate_content(payload.get("content") or "", item.value_type)
        version = str(payload.get("version") or "").strip()
        now = _now_iso()
        target = None
        for v in item.versions:
            if v.version == version:
                if v.status != "DRAFT":
                    raise ValueError(f"版本 {version} 已发布（{v.status}），不可编辑；请新建草稿")
                target = v
                break
        if target is None:
            if version:
                target = ConfigVersion(version=version, status="DRAFT", content=content,
                                       changelog=str(payload.get("changelog") or f"新草稿 {version}"),
                                       created_by=self._actor(context), created_at=now)
                item.versions.append(target)
            else:
                latest = item.versions[-1] if item.versions else None
                if latest is not None and latest.status == "DRAFT":
                    target = latest
                else:
                    target = ConfigVersion(version=self._suggest_version(item), status="DRAFT", content=content,
                                           changelog=str(payload.get("changelog") or "新建草稿"),
                                           created_by=self._actor(context), created_at=now)
                    item.versions.append(target)
        target.content = content
        if payload.get("changelog"):
            target.changelog = str(payload["changelog"])
        item.updated_at = now
        domain_persistence.write(FAMILY_ITEMS, f"{item.namespace}:{item.key}", item)
        return item.model_dump()

    def publish_item_version(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        item = self._require_item(payload, context, write=True)
        env = str(payload.get("env") or (context or {}).get("env_key") or "").strip()
        self._guard_protected_env(context, item.project_id, env)
        version = str(payload.get("version") or "").strip()
        target = next((v for v in item.versions if v.version == version), None)
        if target is None:
            raise KeyError(f"配置项 {item.key} 不存在版本 {version}")
        if target.status == "SUPERSEDED":
            raise ValueError(f"版本 {version} 已被取代，仅可发布 DRAFT 或回滚历史 PUBLISHED")
        gray = payload.get("gray") or {}
        percent = int(gray.get("percent", 100))
        if not 0 <= percent <= 100:
            raise ValueError("灰度百分比必须是 0-100 整数")
        whitelist = [str(u).strip() for u in (gray.get("whitelist") or []) if str(u).strip()]
        actor = self._actor(context)
        now = _now_iso()
        for v in item.versions:
            if v.status == "PUBLISHED" and v.version != version:
                v.status = "SUPERSEDED"
        target.status = "PUBLISHED"
        target.published_by = actor
        target.published_at = now
        if percent >= 100 and not whitelist:
            # 全量发布：提升为该环境稳定版并清除该环境灰度
            item.stable_env[env] = version
            item.gray_env.pop(env, None)
        else:
            item.gray_env[env] = GrayRelease(
                version=version,
                content=target.content,
                percent=percent,
                whitelist=whitelist,
                published_by=actor,
                published_at=now,
            )
            if env not in item.stable_env:
                item.stable_env[env] = version
        item.updated_at = now
        domain_persistence.write(FAMILY_ITEMS, f"{item.namespace}:{item.key}", item)
        return item.model_dump()

    def rollback_item(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        item = self._require_item(payload, context, write=True)
        env = str(payload.get("env") or (context or {}).get("env_key") or "").strip()
        self._guard_protected_env(context, item.project_id, env)
        version = str(payload.get("version") or "").strip()
        target = next((v for v in item.versions if v.version == version and v.status in ("PUBLISHED", "SUPERSEDED")), None)
        if target is None:
            raise ValueError(f"仅可回滚到已发布过的版本（{version} 不是）")
        item.stable_env[env] = version
        item.gray_env.pop(env, None)
        item.updated_at = _now_iso()
        domain_persistence.write(FAMILY_ITEMS, f"{item.namespace}:{item.key}", item)
        return item.model_dump()

    def item_history(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        item = self._require_item(payload, context, write=False)
        env = str((context or {}).get("env_key") or payload.get("env") or "").strip()
        return {
            "versions": [v.model_dump() for v in reversed(item.versions)],
            "stable_version": item.stable_env.get(env) or item.stable_env.get("") or "",
            "gray": item.gray_env.get(env) or item.gray_env.get(""),
        }

    # ------------------------------------------------------------------
    # 数据面读
    # ------------------------------------------------------------------
    def list_items(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ns_key = str(payload.get("namespace") or "").strip()
        rows = []
        for item in self._items.values():
            if ns_key and item.namespace != ns_key:
                continue
            if not self._visible(item.project_id, self._ctx_project(context)):
                continue
            rows.append(item.model_dump())
        rows.sort(key=lambda r: (r["namespace"], r["key"]))
        return {"items": rows, "total": len(rows)}

    def resolve(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        env = str(payload.get("env") or (context or {}).get("env_key") or "").strip()
        # 主体解析：身份取登录态；代查（payload.user_id）仅限配置管理者或平台超管
        uid = str((context or {}).get("user_id") or "").strip()
        requested = str(payload.get("user_id") or "").strip()
        if not uid:
            raise PermissionError("UNAUTHORIZED:配置解析需要登录身份")
        if requested and requested != uid:
            if not self._is_super(context):
                item = self._items.get(f"{payload.get('namespace', '')}:{payload.get('key', '')}")
                granted = False
                if item is not None:
                    try:
                        from src.domains.platform.service import platform_service

                        granted = platform_service.has_scoped_permission(
                            uid, P_CONFIGCENTER_WRITE, project_id=item.project_id
                        )
                    except Exception:
                        granted = False
                if not granted:
                    raise PermissionError("权限不足：仅配置管理者可代其他用户解析")
        user_id = requested or uid
        ns_key = str(payload.get("namespace") or "").strip()
        key = str(payload.get("key") or "").strip()
        item = self._items.get(f"{ns_key}:{key}")
        if item is None:
            # 宿主运行时不应因误配键而报错：诚实返回 NOT_FOUND
            return {"namespace": ns_key, "key": key, "env": env, "value": "", "source": "NOT_FOUND", "version": ""}
        return {"namespace": ns_key, "key": key, "env": env, **resolve_content(item, user_id, env)}

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _guard_protected_env(self, context: Dict[str, Any], project_id: str, env: str) -> None:
        """保护级环境闸门：staging/online 的发布/回滚要求项目所有者角色/超管。"""
        if not env:
            return
        try:
            from src.domains.platform.service import platform_service

            platform_service.environment_context_ok(context, project_id)
        except PermissionError:
            raise
        except Exception:
            pass

    def _require_namespace(self, payload: Dict[str, Any], context: Dict[str, Any], write: bool) -> ConfigNamespace:
        key = str(payload.get("namespace") or payload.get("key") or "").strip()
        ns = self._namespaces.get(key)
        if ns is None:
            raise KeyError(f"命名空间 {key} 不存在")
        if write:
            self._require_write(context, ns.project_id)
        elif not self._visible(ns.project_id, self._ctx_project(context)):
            raise KeyError(f"命名空间 {key} 不存在")
        return ns

    def _require_item(self, payload: Dict[str, Any], context: Dict[str, Any], write: bool) -> ConfigItem:
        item_key = f"{payload.get('namespace', '')}:{payload.get('key', '')}"
        if payload.get("item"):
            item_key = str(payload["item"])
        item = self._items.get(item_key)
        if item is None:
            raise KeyError(f"配置项 {item_key} 不存在")
        if write:
            self._require_write(context, item.project_id)
        elif not self._visible(item.project_id, self._ctx_project(context)):
            raise KeyError(f"配置项 {item_key} 不存在")
        return item

    @staticmethod
    def _validate_content(content: str, value_type: str) -> tuple:
        content = str(content or "")
        value_type = value_type if value_type in ("JSON", "TEXT") else "JSON"
        if value_type == "JSON":
            import json

            try:
                json.loads(content)
            except ValueError as exc:
                raise ValueError(f"JSON 内容格式错误：{exc}")
        return content, value_type

    @staticmethod
    def _suggest_version(item: ConfigItem) -> str:
        existing = {v.version for v in item.versions}
        candidate = "v1.0.0"
        serial = 1
        while candidate in existing:
            serial += 1
            candidate = f"v1.0.{serial}"
        return candidate

    # ------------------------------------------------------------------
    # Hydration（启动时由 domain_persistence 回放重建索引）
    # ------------------------------------------------------------------
    def hydrate_namespaces(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows or []:
            try:
                ns = ConfigNamespace(**row)
            except Exception:
                continue
            self._namespaces[ns.key] = ns
        return len(rows or [])

    def hydrate_items(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows or []:
            # 遗留数据迁移：单稳定版/灰度 → 默认环境桶（""）
            if "stable_version" in row and not row.get("stable_env"):
                row["stable_env"] = {"": row.get("stable_version") or ""}
            if row.get("gray") and not row.get("gray_env"):
                row["gray_env"] = {"": row["gray"]}
            row.pop("stable_version", None)
            row.pop("gray", None)
            try:
                item = ConfigItem(**row)
            except Exception:
                continue
            self._items[f"{item.namespace}:{item.key}"] = item
        return len(rows or [])


config_center_service = ConfigCenterService()

domain_persistence.register(FAMILY_NAMESPACES, config_center_service.hydrate_namespaces)
domain_persistence.register(FAMILY_ITEMS, config_center_service.hydrate_items)


# ----------------------------------------------------------------------
# MicroFlow 写路径：配置中心写操作动作表（经 OPC_CONFIGCENTER_PIPELINE 元管线）
# ----------------------------------------------------------------------
CONFIG_ACTIONS: Dict[str, str] = {
    "namespaces.create": "create_namespace",
    "namespaces.update": "update_namespace",
    "namespaces.delete": "delete_namespace",
    "items.create": "create_item",
    "items.update": "update_item",
    "items.delete": "delete_item",
    "items.version.save": "save_item_version",
    "items.publish": "publish_item_version",
    "items.rollback": "rollback_item",
}


def dispatch_config_action(action: str, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    method_name = CONFIG_ACTIONS.get(action)
    if not method_name:
        raise ValueError(f"未知的配置中心操作：{action}")
    method = getattr(config_center_service, method_name)
    return method(payload or {}, context or {})
