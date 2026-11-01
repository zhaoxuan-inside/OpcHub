"""三层编排资产目录：算子 → 子图 → 场景。

* 算子（Operator）：内置（代码注册的原子算子，只读展示）与自建（沙箱脚本，
  完整的创建/版本/发布/删除生命周期）。
* 子图（Subgraph）：把已发布的算子编排成可复用子流水线，自身走 DRAFT →
  PUBLISHED 版本机，发布时编译为算子级扁平图。
* 场景（Scenario）：算子与子图混合编排；发布时把子图内联展开成扁平 DAG 并
  物化为执行引擎使用的 DAGConfigRecord（拓扑校验：无环、唯一入口、唯一出口）。

所有变更操作必须持有目标资产的排他锁（见 locks.py）；读取（展示）永远开放。
"""
import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.core.microkernel.sandbox import load_operator_from_source
from src.core.microkernel.script_ingestion import (
    OPERATOR_NAME_PATTERN,
    script_ingestion_service,
)
from src.domains.orchestration.locks import AssetLock, lock_manager
from src.domains.orchestration.models import DAGConfigSaveRequest, OperatorDescriptor
from src.domains.orchestration.service import orchestration_service, utc_now_iso
from src.infrastructure.database.persistence import domain_persistence

ASSET_CODE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{1,63}$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")

# 预置算子（代码注册）随平台发布，目录统一以平台版本 v1.0.0 标识
BUILTIN_OPERATOR_VERSION = "v1.0.0"

CATALOG_PIPELINE_SCENARIO = "OPC_ORCHESTRATION_CATALOG_PIPELINE"


def ensure_catalog_pipeline() -> None:
    """Idempotently seed the meta DAG pipeline used by every catalog write.

    catalog 模块可能在进程内被懒加载（全新实例的首个调用若是写操作，模块此前
    从未导入），因此写适配器会在每次写操作前显式调用本函数。
    """
    if any(
        c.scenario_code == CATALOG_PIPELINE_SCENARIO
        for c in orchestration_service.list_dag_configs()
    ):
        return
    orchestration_service.save_dag_config(
        DAGConfigSaveRequest(
            scenario_code=CATALOG_PIPELINE_SCENARIO,
            version="v1.0.0",
            status="ACTIVE",
            topology_graph={
                "topology": "DAG",
                "entry_node": "step_guard",
                "exit_node": "step_telemetry",
                "enable_saga_compensation": False,
                "nodes": [
                    {"id": "step_guard", "action_handler": "orchestration.catalog.guard", "type": "GUARD", "params": {"legacy_inputs": True}},
                    {"id": "step_persist", "action_handler": "orchestration.catalog.persist", "type": "BIZ", "params": {"legacy_inputs": True}},
                    {"id": "step_telemetry", "action_handler": "orchestration.catalog.telemetry.incr", "type": "BIZ", "params": {"legacy_inputs": True}},
                ],
                "edges": [
                    {"from": "step_guard", "to": "step_persist"},
                    {"from": "step_persist", "to": "step_telemetry"},
                ],
            },
        )
    )


# ======================================================================
# Models
# ======================================================================
class VersionStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class OperatorDefinition(BaseModel):
    """算子版本定义：自建算子携带沙箱脚本；内置算子仅引用运行时处理器名。"""
    code: str = ""
    entry_function: str = "action_entry"
    handler_ref: str = ""  # 内置算子的运行时处理器名（= 算子名）
    dispatch_mode: str = "IN_PROCESS"
    remote_endpoint: Optional[str] = None


class OperatorVersion(BaseModel):
    version: str
    status: VersionStatus = VersionStatus.DRAFT
    definition: OperatorDefinition = Field(default_factory=OperatorDefinition)
    changelog: str = ""
    created_by: str
    created_at: str
    published_by: str = ""
    published_at: str = ""


class OperatorAsset(BaseModel):
    name: str
    display_name: str
    domain: str
    description: str
    source: str  # builtin | custom
    current_version: str = ""  # 最新已发布版本（预置算子为平台版本 v1.0.0）
    versions: List[OperatorVersion] = []
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    project_id: str = ""  # 归属项目（空 = 平台内置/未归属，全局只读可见）
    runtime_mode: str = ""  # dispatcher 中的当前调度模式
    in_use: bool = False  # 是否被已发布子图/场景编排引用（读取时计算）
    referenced_by: List[str] = []  # 引用方列表（如「子图 SG_X@v1.0.0」）
    lock_status: Optional[AssetLock] = None  # 展示用，读取时填充


class GraphEdge(BaseModel):
    from_node: str
    to_node: str


class SubgraphNode(BaseModel):
    id: str
    operator: str
    operator_version: str = ""  # 空 = 发布时取该算子最新已发布版本
    type: str = "BIZ"  # GATEWAY | GUARD | BIZ | STORAGE | CACHE
    timeout_ms: int = 3000


class SubgraphGraph(BaseModel):
    entry_node: str
    exit_node: str
    nodes: List[SubgraphNode] = []
    edges: List[GraphEdge] = []


class CompiledNode(BaseModel):
    id: str
    action_handler: str
    type: str = "BIZ"
    timeout_ms: int = 3000


class CompiledGraph(BaseModel):
    entry_node: str
    exit_node: str
    nodes: List[CompiledNode] = []
    edges: List[GraphEdge] = []


class SubgraphVersion(BaseModel):
    version: str
    status: VersionStatus = VersionStatus.DRAFT
    graph: SubgraphGraph = Field(default_factory=SubgraphGraph)
    changelog: str = ""
    created_by: str = ""
    created_at: str = ""
    published_by: str = ""
    published_at: str = ""
    compiled: Optional[CompiledGraph] = None


class SubgraphAsset(BaseModel):
    code: str
    display_name: str
    description: str = ""
    current_version: str = ""
    versions: List[SubgraphVersion] = []
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    project_id: str = ""  # 归属项目（空 = 未归属，仅平台管理者可操作）
    lock_status: Optional[AssetLock] = None


class ScenarioNode(BaseModel):
    id: str
    kind: str = "OPERATOR"  # OPERATOR | SUBGRAPH
    operator: str = ""
    operator_version: str = ""
    subgraph: str = ""
    subgraph_version: str = ""  # 空 = 发布时取该子图最新已发布版本
    type: str = "BIZ"
    timeout_ms: int = 3000


class ScenarioGraph(BaseModel):
    entry_node: str
    exit_node: str
    nodes: List[ScenarioNode] = []
    edges: List[GraphEdge] = []
    enable_saga_compensation: bool = True


class ScenarioVersion(BaseModel):
    version: str
    status: VersionStatus = VersionStatus.DRAFT
    graph: ScenarioGraph = Field(default_factory=ScenarioGraph)
    changelog: str = ""
    created_by: str = ""
    created_at: str = ""
    published_by: str = ""
    published_at: str = ""
    compiled: Optional[CompiledGraph] = None


class ScenarioAsset(BaseModel):
    code: str
    display_name: str
    description: str = ""
    current_version: str = ""
    versions: List[ScenarioVersion] = []
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    project_id: str = ""  # 归属项目（空 = 未归属，仅平台管理者可操作）
    lock_status: Optional[AssetLock] = None


# ======================================================================
# Validation helpers
# ======================================================================
def _validate_no_cycle(node_ids: List[str], edges: List[GraphEdge]) -> None:
    adjacency: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        adjacency[e.from_node].append(e.to_node)
    indegree = {nid: 0 for nid in node_ids}
    for e in edges:
        indegree[e.to_node] += 1
    queue = [nid for nid, d in indegree.items() if d == 0]
    seen = 0
    while queue:
        cur = queue.pop()
        seen += 1
        for nxt in adjacency[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if seen != len(node_ids):
        raise ValueError("编排中存在环路，请移除构成回路的连线")


def _validate_structure(entry_node: str, exit_node: str, node_ids: List[str], edges: List[GraphEdge]) -> None:
    """草稿层结构校验：ID 唯一、入口/出口存在、边引用合法（允许暂存未完成拓扑）。"""
    ids = list(node_ids)
    if len(set(ids)) != len(ids):
        raise ValueError("节点 ID 重复，请保证每个节点 ID 唯一")
    id_set = set(ids)
    if entry_node not in id_set or exit_node not in id_set:
        raise ValueError("入口/出口节点必须存在于节点列表中")
    for e in edges:
        if e.from_node not in id_set or e.to_node not in id_set:
            raise ValueError(f"连线 {e.from_node} → {e.to_node} 引用了不存在的节点")


def _validate_single_entry_exit(entry_node: str, exit_node: str, node_ids: List[str], edges: List[GraphEdge]) -> None:
    """发布层校验：执行引擎要求无环、唯一零入度入口与唯一零出度出口。"""
    _validate_structure(entry_node, exit_node, node_ids, edges)
    _validate_no_cycle(node_ids, edges)
    sources = [nid for nid in node_ids if not any(e.to_node == nid for e in edges)]
    sinks = [nid for nid in node_ids if not any(e.from_node == nid for e in edges)]
    if sources != [entry_node]:
        raise ValueError(
            f"入口节点不唯一：目前存在多个无前置连线的节点 {sources or ['无']}，入口应为 {entry_node}"
        )
    if sinks != [exit_node]:
        raise ValueError(
            f"出口节点不唯一：目前存在多个无后续连线的节点 {sinks or ['无']}，出口应为 {exit_node}"
        )
    if entry_node == exit_node and len(node_ids) > 1:
        raise ValueError("多节点编排的入口与出口不能是同一节点")


def _resolve_draft_row(versions, version: str, create_row):
    """Locate a DRAFT row; an unknown version creates a new draft (publish 状态不可编辑)."""
    for v in versions:
        if v.version == version:
            if v.status != VersionStatus.DRAFT:
                raise ValueError(
                    f"版本 {version} 已发布（{v.status.value}），不可编辑；请基于它新建草稿版本"
                )
            return v
    row = create_row()
    versions.append(row)
    return row


# ======================================================================
# Catalog service
# ======================================================================
class CatalogService:
    """Manages versioned operator / subgraph / scenario assets with exclusive locks."""

    def __init__(self):
        self._operators: Dict[str, OperatorAsset] = {}
        self._subgraphs: Dict[str, SubgraphAsset] = {}
        self._scenarios: Dict[str, ScenarioAsset] = {}
        # Release approval tickets (id -> ticket); persisted in
        # orchestration.release_approvals and hydrated on startup.
        self._release_approvals: "Dict[str, ReleaseApproval]" = {}
        self._seed_catalog_pipeline()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _persist_operator(asset: OperatorAsset) -> None:
        # in_use / referenced_by / lock_status 为读取时计算的展示字段，不入快照
        domain_persistence.write(
            "orchestration.catalog.operators",
            asset.name,
            asset.model_copy(update={"lock_status": None, "in_use": False, "referenced_by": []}),
        )

    @staticmethod
    def _persist_subgraph(asset: SubgraphAsset) -> None:
        domain_persistence.write(
            "orchestration.catalog.subgraphs",
            asset.code,
            asset.model_copy(update={"lock_status": None}),
        )

    @staticmethod
    def _persist_scenario(asset: ScenarioAsset) -> None:
        domain_persistence.write(
            "orchestration.catalog.scenarios",
            asset.code,
            asset.model_copy(update={"lock_status": None}),
        )

    def _seed_catalog_pipeline(self) -> None:
        """Seed the meta DAG pipeline that carries all catalog write operations.

        Idempotent：catalog 模块可能在进程内被懒加载（全新实例的首个调用若是
        写操作，模块此前从未导入），因此写适配器会显式重调本种子。
        """
        ensure_catalog_pipeline()

    @staticmethod
    def _actor(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        uid = str((context or {}).get("user_id") or (payload or {}).get("actor_id") or "").strip()
        if not uid:
            raise PermissionError("UNAUTHORIZED:目录变更操作需要登录后的管理员身份")
        name = str((context or {}).get("user_name") or (payload or {}).get("actor_name") or uid)
        return {"user_id": uid, "user_name": name}

    # ------------------------------------------------------------------
    # 项目隔离 helpers（分租户·分项目治理底座，见 src/domains/platform）
    # ------------------------------------------------------------------
    @staticmethod
    def _ctx_project(context: Dict[str, Any]) -> str:
        """活动项目上下文（网关 scope 强制后由 ctx 注入；平台超管可缺省）。"""
        return str((context or {}).get("project_id") or "").strip()

    @staticmethod
    def _is_super(context: Dict[str, Any]) -> bool:
        """平台超管：legacy ADMIN 通配 或 PLATFORM 通配角色绑定。"""
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

    def _visible(self, asset_project: str, ctx_project: str) -> bool:
        """可见性：未归属/平台内置资产全局可见；项目资产仅本项目（超管缺省上下文见全部）。"""
        return (not asset_project) or (not ctx_project) or asset_project == ctx_project

    def _ensure_writable(self, asset_project: str, context: Dict[str, Any]) -> None:
        """写权限：项目资产仅本项目可写；未归属资产仅平台超管可写。"""
        ctx_project = self._ctx_project(context)
        if not asset_project:
            if not self._is_super(context):
                raise PermissionError("该资产未归属项目，仅平台管理者可操作")
            return
        if ctx_project and asset_project != ctx_project:
            raise KeyError("资产不存在于当前项目")
        if not ctx_project and not self._is_super(context):
            raise PermissionError("请先选择活动项目后再操作项目资产")

    def _can_write_project(self, context: Dict[str, Any], project_id: str) -> bool:
        if not project_id:
            return False
        if self._is_super(context):
            return True
        uid = str((context or {}).get("user_id") or "").strip()
        if not uid:
            return False
        try:
            from src.domains.platform.service import platform_service

            return platform_service.has_scoped_permission(uid, "orchestration:write", project_id=project_id)
        except Exception:
            return False

    def _require_visible(self, asset_project: str, code: str, kind: str, context: Dict[str, Any]) -> None:
        """项目资产对非本项目成员不可见（不泄露存在性，按不存在处理）。"""
        if not self._visible(asset_project, self._ctx_project(context)):
            raise KeyError(f"{kind} {code} 不存在")

    # ------------------------------------------------------------------
    # Operators — 算子
    # ------------------------------------------------------------------
    def _usage_map(self) -> Dict[str, List[str]]:
        """operator name -> 引用方列表（算子“是否被使用”）。

        统计口径：已发布子图版本、已发布场景版本，以及正在运行的系统预置
        流程（ACTIVE 运行时配置；管理场景发布的版本已按版本计入，跳过其
        物化配置避免重复）。
        """
        usage: Dict[str, List[str]] = {}
        for sub in self._subgraphs.values():
            for v in sub.versions:
                if v.status == VersionStatus.PUBLISHED:
                    for n in v.graph.nodes:
                        usage.setdefault(n.operator, []).append(f"子图 {sub.code}@{v.version}")
        managed_codes = set(self._scenarios.keys())
        for sc in self._scenarios.values():
            for v in sc.versions:
                if v.status == VersionStatus.PUBLISHED:
                    for n in v.graph.nodes:
                        if n.kind == "OPERATOR":
                            usage.setdefault(n.operator, []).append(f"场景 {sc.code}@{v.version}")
        for cfg in orchestration_service.list_dag_configs():
            if cfg.scenario_code in managed_codes or cfg.status != "ACTIVE":
                continue
            for n in (cfg.topology_graph or {}).get("nodes", []):
                handler = n.get("action_handler")
                if handler:
                    usage.setdefault(handler, []).append(f"流程 {cfg.scenario_code}@{cfg.version}")
        return usage

    def _builtin_asset(self, name: str, usage: Dict[str, List[str]]) -> OperatorAsset:
        """Synthesize the catalog view of a code-registered builtin operator."""
        desc = self._builtin_descriptor(name)
        holders = sorted(set(usage.get(name, [])))
        return OperatorAsset(
            name=desc.name,
            display_name=desc.name,
            domain=desc.domain,
            description=desc.description,
            source="builtin",
            current_version=BUILTIN_OPERATOR_VERSION,
            versions=[
                OperatorVersion(
                    version=BUILTIN_OPERATOR_VERSION,
                    status=VersionStatus.PUBLISHED,
                    definition=OperatorDefinition(handler_ref=desc.name),
                    changelog="平台预置版本",
                    created_by="platform",
                    created_at="",
                )
            ],
            runtime_mode=desc.mode.value,
            in_use=bool(holders),
            referenced_by=holders,
        )

    def list_operators(self, context: Optional[Dict[str, Any]] = None) -> List[OperatorAsset]:
        ctx_project = self._ctx_project(context)
        usage = self._usage_map()
        rows: List[OperatorAsset] = []
        for asset in self._operators.values():
            if not self._visible(asset.project_id, ctx_project):
                continue
            asset.lock_status = lock_manager.status("operator", asset.name)
            descriptor = self._builtin_descriptor(asset.name)
            # MicroFlow executes in-process; the legacy dispatcher mode is retired.
            asset.runtime_mode = descriptor.mode.value if descriptor else ""
            holders = sorted(set(usage.get(asset.name, [])))
            asset.in_use = bool(holders)
            asset.referenced_by = holders
            rows.append(asset)

        managed = set(self._operators.keys())
        for desc in self._sdk_descriptors():
            if desc.name in managed:
                continue
            rows.append(self._builtin_asset(desc.name, usage))
        rows.sort(key=lambda a: (a.source != "builtin", a.domain, a.name))
        return rows

    def get_operator(self, name: str, context: Optional[Dict[str, Any]] = None) -> OperatorAsset:
        usage = self._usage_map()
        asset = self._operators.get(name)
        if asset:
            self._require_visible(asset.project_id, name, "算子", context)
            asset.lock_status = lock_manager.status("operator", name)
            holders = sorted(set(usage.get(name, [])))
            asset.in_use = bool(holders)
            asset.referenced_by = holders
            return asset
        desc = self._builtin_descriptor(name)
        if desc:
            return self._builtin_asset(name, usage)
        raise KeyError(f"算子 {name} 不存在")

    @staticmethod
    def _sdk_descriptors():
        """Operator descriptors from the SDK registry (MicroFlow bridge input)."""
        from src.core.operators.sdk import REGISTRY

        return [
            OperatorDescriptor(name=d.name, domain=d.category, description=d.description)
            for d in REGISTRY
        ]

    def _builtin_descriptor(self, name: str):
        for desc in self._sdk_descriptors():
            if desc.name == name:
                return desc
        return None

    def _resolve_custom_operator_version(
        self,
        name: str,
        version_ref: str,
        ctx_project: str = "",
    ) -> OperatorVersion:
        """Resolve a managed custom operator reference to a PUBLISHED version."""
        asset = self._operators.get(name)
        if not asset or (ctx_project and not self._visible(asset.project_id, ctx_project)):
            raise KeyError(f"算子 {name} 不存在，请先创建并发布")
        if version_ref:
            for v in asset.versions:
                if v.version == version_ref and v.status == VersionStatus.PUBLISHED:
                    return v
            raise ValueError(f"算子 {name}@{version_ref} 未发布或不存在，仅可编排已发布版本")
        if not asset.current_version:
            raise ValueError(f"自建算子 {name} 尚未发布任何版本，无法被编排")
        for v in asset.versions:
            if v.version == asset.current_version and v.status == VersionStatus.PUBLISHED:
                return v
        raise ValueError(f"算子 {name} 的当前版本 {asset.current_version} 状态异常")

    def create_operator(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        ctx_project = self._ctx_project(context)
        if not ctx_project and not self._is_super(context):
            raise PermissionError("请先选择活动项目后再创建目录资产")
        name = str(payload.get("name") or "").strip()
        display_name = str(payload.get("display_name") or name).strip()
        domain = str(payload.get("domain") or "custom").strip() or "custom"
        description = str(payload.get("description") or "").strip()
        code = str(payload.get("code") or "")
        entry_function = str(payload.get("entry_function") or "action_entry").strip() or "action_entry"
        version = str(payload.get("version") or "v1.0.0").strip()

        if not OPERATOR_NAME_PATTERN.match(name):
            raise ValueError("算子名需以字母开头，仅含字母/数字/下划线/点号，长度 2-64")
        if not VERSION_PATTERN.match(version):
            raise ValueError("版本号需以字母或数字开头，仅含字母/数字/点号/横线/下划线")
        if name in self._operators:
            raise ValueError(f"算子 {name} 已存在")
        if self._builtin_descriptor(name):
            raise ValueError(f"算子名 {name} 与内置算子冲突，请更换名称")

        # Firewalls 1-3: draft scripts must pass the sandbox before entering the catalog
        try:
            loaded = load_operator_from_source(code, entry_function)
        except ValueError as exc:
            raise ValueError(f"算子脚本未通过沙箱校验：{exc}") from exc

        lock_manager.require("operator", name, actor["user_id"])
        now = utc_now_iso()
        asset = OperatorAsset(
            name=name,
            display_name=display_name,
            domain=domain,
            description=description,
            source="custom",
            current_version="",
            versions=[
                OperatorVersion(
                    version=version,
                    status=VersionStatus.DRAFT,
                    definition=OperatorDefinition(
                        code=code,
                        entry_function=loaded.entry_function,
                        dispatch_mode=str(payload.get("dispatch_mode") or "IN_PROCESS"),
                        remote_endpoint=payload.get("remote_endpoint"),
                    ),
                    changelog=str(payload.get("changelog") or "初始版本"),
                    created_by=actor["user_id"],
                    created_at=now,
                )
            ],
            created_by=actor["user_id"],
            created_at=now,
            updated_at=now,
            project_id=ctx_project,
        )
        self._operators[name] = asset
        self._persist_operator(asset)
        return asset.model_dump()

    def save_operator_version(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        name = str(payload.get("name") or "").strip()
        asset = self._operators.get(name)
        if not asset:
            raise KeyError(f"算子 {name} 不存在或为内置算子（内置算子不支持版本编辑）")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("operator", name, actor["user_id"])

        version = str(payload.get("version") or "").strip()
        now = utc_now_iso()

        def _build_definition(base: Optional[OperatorVersion]) -> OperatorDefinition:
            src = payload.get("definition") or {}
            code = str(src.get("code") if "code" in src else (base.definition.code if base else ""))
            entry_function = str(
                src.get("entry_function")
                if "entry_function" in src
                else (base.definition.entry_function if base else "action_entry")
            )
            if not code:
                raise ValueError("自建算子的脚本内容不能为空")
            try:
                loaded = load_operator_from_source(code, entry_function)
            except ValueError as exc:
                raise ValueError(f"算子脚本未通过沙箱校验：{exc}") from exc
            return OperatorDefinition(
                code=code,
                entry_function=loaded.entry_function,
                dispatch_mode=str(src.get("dispatch_mode") or (base.definition.dispatch_mode if base else "IN_PROCESS")),
                remote_endpoint=src.get("remote_endpoint") if "remote_endpoint" in src else (base.definition.remote_endpoint if base else None),
            )

        if not version:
            # 未指定版本：最新版本仍为草稿时就地更新，否则派生新草稿版本
            latest = asset.versions[-1] if asset.versions else None
            if latest is not None and latest.status == VersionStatus.DRAFT:
                latest.definition = _build_definition(latest)
                if "changelog" in payload:
                    latest.changelog = str(payload.get("changelog") or "")
            else:
                base = latest
                asset.versions.append(
                    OperatorVersion(
                        version=self._suggest_next_version(asset),
                        status=VersionStatus.DRAFT,
                        definition=_build_definition(base),
                        changelog=str(payload.get("changelog") or f"基于 {base.version if base else '空'} 新建的草稿"),
                        created_by=actor["user_id"],
                        created_at=now,
                    )
                )
        else:
            row = _resolve_draft_row(
                asset.versions,
                version,
                lambda: OperatorVersion(
                    version=version,
                    status=VersionStatus.DRAFT,
                    definition=_build_definition(None),
                    changelog=str(payload.get("changelog") or f"新草稿 {version}"),
                    created_by=actor["user_id"],
                    created_at=now,
                ),
            )
            row.definition = _build_definition(row)
            if "changelog" in payload:
                row.changelog = str(payload.get("changelog") or "")
        if "display_name" in payload:
            asset.display_name = str(payload.get("display_name") or asset.display_name)
        if "description" in payload:
            asset.description = str(payload.get("description") or "")
        asset.updated_at = now
        self._persist_operator(asset)
        return asset.model_dump()

    def publish_operator(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        name = str(payload.get("name") or "").strip()
        version = str(payload.get("version") or "").strip()
        asset = self._operators.get(name)
        if not asset:
            raise KeyError(f"算子 {name} 不存在或为内置算子（内置算子由平台代码发布）")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("operator", name, actor["user_id"])

        row = None
        for v in asset.versions:
            if v.version == version:
                row = v
                break
        if not row:
            raise KeyError(f"算子 {name} 不存在版本 {version}")
        if row.status == VersionStatus.PUBLISHED:
            raise ValueError(f"版本 {version} 已是发布状态")
        if row.status == VersionStatus.SUPERSEDED:
            raise ValueError(f"版本 {version} 已被取代，请基于当前版本新建草稿后再发布")

        # re-validate the script, then Firewall 4: register into the runtime method pool
        try:
            load_operator_from_source(row.definition.code, row.definition.entry_function)
        except ValueError as exc:
            raise ValueError(f"发布前沙箱复检失败：{exc}") from exc
        script_ingestion_service.upload_and_register(
            name=name,
            code=row.definition.code,
            operator_id=actor["user_id"],
            entry_function=row.definition.entry_function,
            description=asset.description or asset.display_name,
            overwrite=True,
        )
        now = utc_now_iso()
        for v in asset.versions:
            if v.status == VersionStatus.PUBLISHED:
                v.status = VersionStatus.SUPERSEDED
        row.status = VersionStatus.PUBLISHED
        row.published_by = actor["user_id"]
        row.published_at = now
        asset.current_version = row.version
        asset.updated_at = now
        self._persist_operator(asset)
        return asset.model_dump()

    def operator_reference_holders(self, name: str) -> List[str]:
        """Published subgraph / scenario versions that compose this operator."""
        holders: List[str] = []
        for sub in self._subgraphs.values():
            for v in sub.versions:
                if v.status == VersionStatus.PUBLISHED and any(n.operator == name for n in v.graph.nodes):
                    holders.append(f"子图 {sub.code}@{v.version}")
        for sc in self._scenarios.values():
            for v in sc.versions:
                if v.status == VersionStatus.PUBLISHED and any(n.operator == name for n in v.graph.nodes):
                    holders.append(f"场景 {sc.code}@{v.version}")
        return holders

    def delete_operator(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        name = str(payload.get("name") or "").strip()
        asset = self._operators.get(name)
        if not asset:
            if self._builtin_descriptor(name):
                raise ValueError(f"算子 {name} 为平台内置算子（代码注册），不可删除")
            raise KeyError(f"算子 {name} 不存在")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("operator", name, actor["user_id"])

        holders = self.operator_reference_holders(name)
        if holders:
            raise ValueError(f"算子 {name} 仍被已发布的 {'、'.join(holders)} 引用，请先下线或重新编排这些版本")

        if asset.current_version:
            script_ingestion_service.unregister(name, actor["user_id"])
        del self._operators[name]
        domain_persistence.delete("orchestration.catalog.operators", name)
        lock_manager.release("operator", name, actor["user_id"], force=True)
        return {"name": name, "deleted": True}

    # ------------------------------------------------------------------
    # Subgraphs — 子图
    # ------------------------------------------------------------------
    def list_subgraphs(self, context: Optional[Dict[str, Any]] = None) -> List[SubgraphAsset]:
        ctx_project = self._ctx_project(context)
        rows = []
        for asset in self._subgraphs.values():
            if not self._visible(asset.project_id, ctx_project):
                continue
            asset.lock_status = lock_manager.status("subgraph", asset.code)
            rows.append(asset)
        rows.sort(key=lambda a: a.code)
        return rows

    def get_subgraph(self, code: str, context: Optional[Dict[str, Any]] = None) -> SubgraphAsset:
        asset = self._subgraphs.get(code)
        if not asset:
            raise KeyError(f"子图 {code} 不存在")
        self._require_visible(asset.project_id, code, "子图", context)
        asset.lock_status = lock_manager.status("subgraph", code)
        return asset

    def _resolve_subgraph_version(self, code: str, version_ref: str, ctx_project: str = "") -> SubgraphVersion:
        asset = self._subgraphs.get(code)
        if not asset or (ctx_project and not self._visible(asset.project_id, ctx_project)):
            raise KeyError(f"子图 {code} 不存在")
        target = version_ref or asset.current_version
        for v in asset.versions:
            if v.version == target and v.status == VersionStatus.PUBLISHED:
                return v
        raise ValueError(f"子图 {code}@{target or '最新'} 未发布或不存在，仅可编排已发布子图版本")

    def _validate_subgraph_graph(self, graph: SubgraphGraph, strict: bool, ctx_project: str = "") -> None:
        if not graph.nodes:
            raise ValueError("子图至少需要一个算子节点")
        _validate_structure(graph.entry_node, graph.exit_node, [n.id for n in graph.nodes], graph.edges)
        for n in graph.nodes:
            op = self._operators.get(n.operator)
            if op and self._visible(op.project_id, ctx_project):
                if strict and (n.operator_version and not any(
                    v.version == n.operator_version and v.status == VersionStatus.PUBLISHED
                    for v in op.versions
                )):
                    raise ValueError(f"节点 {n.id} 引用的算子 {n.operator}@{n.operator_version} 未发布")
            elif not self._builtin_descriptor(n.operator):
                raise ValueError(f"节点 {n.id} 引用了不存在的算子 {n.operator}")
        if strict:
            _validate_single_entry_exit(graph.entry_node, graph.exit_node, [n.id for n in graph.nodes], graph.edges)

    def create_subgraph(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        ctx_project = self._ctx_project(context)
        if not ctx_project and not self._is_super(context):
            raise PermissionError("请先选择活动项目后再创建目录资产")
        code = str(payload.get("code") or "").strip()
        if not ASSET_CODE_PATTERN.match(code):
            raise ValueError("子图编码需以字母开头，仅含字母/数字/下划线/点号/横线，长度 2-64")
        if code in self._subgraphs:
            raise ValueError(f"子图 {code} 已存在")
        lock_manager.require("subgraph", code, actor["user_id"])
        now = utc_now_iso()
        asset = SubgraphAsset(
            code=code,
            display_name=str(payload.get("display_name") or code),
            description=str(payload.get("description") or ""),
            versions=[
                SubgraphVersion(
                    version=str(payload.get("version") or "v1.0.0"),
                    status=VersionStatus.DRAFT,
                    graph=SubgraphGraph(entry_node="", exit_node="", nodes=[], edges=[]),
                    changelog="初始版本",
                    created_by=actor["user_id"],
                    created_at=now,
                )
            ],
            created_by=actor["user_id"],
            created_at=now,
            updated_at=now,
            project_id=ctx_project,
        )
        self._subgraphs[code] = asset
        self._persist_subgraph(asset)
        return asset.model_dump()

    def save_subgraph_version(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        asset = self._subgraphs.get(code)
        if not asset:
            raise KeyError(f"子图 {code} 不存在")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("subgraph", code, actor["user_id"])
        now = utc_now_iso()
        version = str(payload.get("version") or "").strip()

        graph = SubgraphGraph(**(payload.get("graph") or {}))
        self._validate_subgraph_graph(graph, strict=False, ctx_project=self._ctx_project(context))

        if not version:
            # 未指定版本：最新版本仍为草稿时就地更新，否则派生新草稿版本
            latest = asset.versions[-1] if asset.versions else None
            if latest is not None and latest.status == VersionStatus.DRAFT:
                latest.graph = graph
                if "changelog" in payload:
                    latest.changelog = str(payload.get("changelog") or "")
            else:
                asset.versions.append(
                    SubgraphVersion(
                        version=self._suggest_next_version(asset),
                        status=VersionStatus.DRAFT,
                        graph=graph,
                        changelog=str(payload.get("changelog") or f"基于 {latest.version if latest else '空'} 新建的草稿"),
                        created_by=actor["user_id"],
                        created_at=now,
                    )
                )
        else:
            row = _resolve_draft_row(
                asset.versions,
                version,
                lambda: SubgraphVersion(
                    version=version,
                    status=VersionStatus.DRAFT,
                    graph=graph,
                    changelog=str(payload.get("changelog") or f"新草稿 {version}"),
                    created_by=actor["user_id"],
                    created_at=now,
                ),
            )
            row.graph = graph
            if "changelog" in payload:
                row.changelog = str(payload.get("changelog") or "")
        if "display_name" in payload:
            asset.display_name = str(payload.get("display_name") or asset.display_name)
        if "description" in payload:
            asset.description = str(payload.get("description") or "")
        asset.updated_at = now
        self._persist_subgraph(asset)
        return asset.model_dump()

    def publish_subgraph(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        version = str(payload.get("version") or "").strip()
        asset = self._subgraphs.get(code)
        if not asset:
            raise KeyError(f"子图 {code} 不存在")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("subgraph", code, actor["user_id"])

        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"子图 {code} 不存在版本 {version}")
        if row.status != VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 状态为 {row.status.value}，只有草稿可以发布")

        compiled = self._compile_subgraph(row, ctx_project=self._ctx_project(context))
        now = utc_now_iso()
        for v in asset.versions:
            if v.status == VersionStatus.PUBLISHED:
                v.status = VersionStatus.SUPERSEDED
        row.status = VersionStatus.PUBLISHED
        row.compiled = compiled
        row.published_by = actor["user_id"]
        row.published_at = now
        asset.current_version = row.version
        asset.updated_at = now
        self._persist_subgraph(asset)
        return asset.model_dump()

    def _compile_subgraph(self, row: SubgraphVersion, ctx_project: str = "") -> CompiledGraph:
        """Resolve operator references into an executable flat operator graph."""
        graph = row.graph
        self._validate_subgraph_graph(graph, strict=True, ctx_project=ctx_project)
        nodes: List[CompiledNode] = []
        for n in graph.nodes:
            op = self._operators.get(n.operator)
            if op and self._visible(op.project_id, ctx_project):
                self._resolve_custom_operator_version(n.operator, n.operator_version, ctx_project)
                handler = n.operator
            else:
                desc = self._builtin_descriptor(n.operator)
                if not desc:
                    raise ValueError(f"节点 {n.id} 引用了不存在的算子 {n.operator}")
                handler = desc.name
            nodes.append(CompiledNode(id=n.id, action_handler=handler, type=n.type, timeout_ms=n.timeout_ms))
        _validate_single_entry_exit(graph.entry_node, graph.exit_node, [n.id for n in nodes], graph.edges)
        return CompiledGraph(entry_node=graph.entry_node, exit_node=graph.exit_node, nodes=nodes, edges=list(graph.edges))

    # ------------------------------------------------------------------
    # Scenarios — 场景
    # ------------------------------------------------------------------
    def list_scenarios(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ctx_project = self._ctx_project(context)
        rows: List[Dict[str, Any]] = []
        managed_codes = set()
        for asset in self._scenarios.values():
            if not self._visible(asset.project_id, ctx_project):
                continue
            managed_codes.add(asset.code)
            asset.lock_status = lock_manager.status("scenario", asset.code)
            rows.append({**asset.model_dump(), "source": "managed"})
        # 运行时内置管线（仅展示/执行，未纳入版本管理）
        for cfg in orchestration_service.list_dag_configs():
            if cfg.scenario_code in managed_codes or cfg.scenario_code == CATALOG_PIPELINE_SCENARIO:
                continue
            rows.append(
                {
                    "code": cfg.scenario_code,
                    "display_name": cfg.scenario_code,
                    "description": "",
                    "current_version": cfg.version if cfg.status == "ACTIVE" else "",
                    "versions": [],
                    "created_by": cfg.created_by,
                    "created_at": cfg.created_at,
                    "updated_at": cfg.created_at,
                    "lock_status": None,
                    "source": "runtime",
                    "runtime_status": cfg.status,
                }
            )
        rows.sort(key=lambda r: (r.get("source") != "managed", r["code"]))
        return rows

    def get_scenario(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        asset = self._scenarios.get(code)
        if asset:
            self._require_visible(asset.project_id, code, "场景", context)
            asset.lock_status = lock_manager.status("scenario", code)
            return {**asset.model_dump(), "source": "managed"}
        cfgs = [c for c in orchestration_service.list_dag_configs() if c.scenario_code == code]
        if cfgs:
            active = next((c for c in cfgs if c.status == "ACTIVE"), cfgs[-1])
            return {
                "code": code,
                "display_name": code,
                "description": "",
                "current_version": active.version if active.status == "ACTIVE" else "",
                "versions": [],
                "created_by": active.created_by,
                "created_at": active.created_at,
                "updated_at": active.created_at,
                "lock_status": None,
                "source": "runtime",
                "runtime_status": active.status,
                "runtime_topology": active.topology_graph,
            }
        raise KeyError(f"场景 {code} 不存在")

    def create_scenario(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        ctx_project = self._ctx_project(context)
        if not ctx_project and not self._is_super(context):
            raise PermissionError("请先选择活动项目后再创建目录资产")
        code = str(payload.get("code") or "").strip()
        if not ASSET_CODE_PATTERN.match(code):
            raise ValueError("场景编码需以字母开头，仅含字母/数字/下划线/点号/横线，长度 2-64")
        if code in self._scenarios:
            raise ValueError(f"场景 {code} 已存在")
        lock_manager.require("scenario", code, actor["user_id"])
        now = utc_now_iso()
        asset = ScenarioAsset(
            code=code,
            display_name=str(payload.get("display_name") or code),
            description=str(payload.get("description") or ""),
            versions=[
                ScenarioVersion(
                    version=str(payload.get("version") or "v1.0.0"),
                    status=VersionStatus.DRAFT,
                    graph=ScenarioGraph(entry_node="", exit_node="", nodes=[], edges=[]),
                    changelog="初始版本",
                    created_by=actor["user_id"],
                    created_at=now,
                )
            ],
            created_by=actor["user_id"],
            created_at=now,
            updated_at=now,
            project_id=ctx_project,
        )
        self._scenarios[code] = asset
        self._persist_scenario(asset)
        return asset.model_dump()

    def _validate_scenario_graph(self, graph: ScenarioGraph, strict: bool, ctx_project: str = "") -> None:
        if not graph.nodes:
            raise ValueError("场景至少需要一个节点")
        _validate_structure(graph.entry_node, graph.exit_node, [n.id for n in graph.nodes], graph.edges)
        for n in graph.nodes:
            if n.kind == "SUBGRAPH":
                sub = self._subgraphs.get(n.subgraph)
                if not sub or (ctx_project and not self._visible(sub.project_id, ctx_project)):
                    raise ValueError(f"节点 {n.id} 引用了不存在的子图 {n.subgraph}")
                if strict:
                    self._resolve_subgraph_version(n.subgraph, n.subgraph_version, ctx_project)
            elif n.kind == "OPERATOR":
                op = self._operators.get(n.operator)
                if op and self._visible(op.project_id, ctx_project):
                    if strict:
                        self._resolve_custom_operator_version(n.operator, n.operator_version, ctx_project)
                elif not self._builtin_descriptor(n.operator):
                    raise ValueError(f"节点 {n.id} 引用了不存在的算子 {n.operator}")
            else:
                raise ValueError(f"节点 {n.id} 的类型 {n.kind} 非法（仅支持 OPERATOR / SUBGRAPH）")

    def save_scenario_version(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        asset = self._scenarios.get(code)
        if not asset:
            raise KeyError(f"场景 {code} 不存在（运行时内置管线需先创建管理版本）")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("scenario", code, actor["user_id"])
        now = utc_now_iso()
        version = str(payload.get("version") or "").strip()

        graph = ScenarioGraph(**(payload.get("graph") or {}))
        self._validate_scenario_graph(graph, strict=False, ctx_project=self._ctx_project(context))

        if not version:
            # 未指定版本：最新版本仍为草稿时就地更新，否则派生新草稿版本
            latest = asset.versions[-1] if asset.versions else None
            if latest is not None and latest.status == VersionStatus.DRAFT:
                latest.graph = graph
                if "changelog" in payload:
                    latest.changelog = str(payload.get("changelog") or "")
            else:
                asset.versions.append(
                    ScenarioVersion(
                        version=self._suggest_next_version(asset),
                        status=VersionStatus.DRAFT,
                        graph=graph,
                        changelog=str(payload.get("changelog") or f"基于 {latest.version if latest else '空'} 新建的草稿"),
                        created_by=actor["user_id"],
                        created_at=now,
                    )
                )
        else:
            row = _resolve_draft_row(
                asset.versions,
                version,
                lambda: ScenarioVersion(
                    version=version,
                    status=VersionStatus.DRAFT,
                    graph=graph,
                    changelog=str(payload.get("changelog") or f"新草稿 {version}"),
                    created_by=actor["user_id"],
                    created_at=now,
                ),
            )
            row.graph = graph
            if "changelog" in payload:
                row.changelog = str(payload.get("changelog") or "")
        if "display_name" in payload:
            asset.display_name = str(payload.get("display_name") or asset.display_name)
        if "description" in payload:
            asset.description = str(payload.get("description") or "")
        asset.updated_at = now
        self._persist_scenario(asset)
        return asset.model_dump()

    def publish_scenario(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        version = str(payload.get("version") or "").strip()
        asset = self._scenarios.get(code)
        if not asset:
            raise KeyError(f"场景 {code} 不存在")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("scenario", code, actor["user_id"])

        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"场景 {code} 不存在版本 {version}")
        if row.status != VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 状态为 {row.status.value}，只有草稿可以发布")

        deployed = self._deploy_scenario_version(code, row, ctx_project=self._ctx_project(context))
        now = utc_now_iso()
        for v in asset.versions:
            if v.status == VersionStatus.PUBLISHED:
                v.status = VersionStatus.SUPERSEDED
        row.status = VersionStatus.PUBLISHED
        row.published_by = actor["user_id"]
        row.published_at = now
        asset.current_version = row.version
        asset.updated_at = now
        self._persist_scenario(asset)
        return {**asset.model_dump(), "deployed_dag": deployed}

    def _compile_scenario(self, row: ScenarioVersion, ctx_project: str = "") -> CompiledGraph:
        """Expand subgraph nodes inline and produce the executable flat DAG."""
        graph = row.graph
        self._validate_scenario_graph(graph, strict=True, ctx_project=ctx_project)

        nodes: List[CompiledNode] = []
        edges: List[GraphEdge] = []
        port_map: Dict[str, Tuple[str, str]] = {}  # scenario node id -> (entry id, exit id)

        for n in graph.nodes:
            if n.kind == "SUBGRAPH":
                sub_ver = self._resolve_subgraph_version(n.subgraph, n.subgraph_version, ctx_project)
                compiled_sub = sub_ver.compiled or self._compile_subgraph(sub_ver, ctx_project)
                prefix = f"{n.id}::"
                for cn in compiled_sub.nodes:
                    nodes.append(CompiledNode(id=prefix + cn.id, action_handler=cn.action_handler, type=cn.type, timeout_ms=cn.timeout_ms))
                for e in compiled_sub.edges:
                    edges.append(GraphEdge(from_node=prefix + e.from_node, to_node=prefix + e.to_node))
                port_map[n.id] = (prefix + compiled_sub.entry_node, prefix + compiled_sub.exit_node)
            else:
                op = self._operators.get(n.operator)
                if op and self._visible(op.project_id, ctx_project):
                    self._resolve_custom_operator_version(n.operator, n.operator_version, ctx_project)
                    handler = n.operator
                else:
                    desc = self._builtin_descriptor(n.operator)
                    if not desc:
                        raise ValueError(f"节点 {n.id} 引用了不存在的算子 {n.operator}")
                    handler = desc.name
                nodes.append(CompiledNode(id=n.id, action_handler=handler, type=n.type, timeout_ms=n.timeout_ms))
                port_map[n.id] = (n.id, n.id)

        for e in graph.edges:
            edges.append(GraphEdge(from_node=port_map[e.from_node][1], to_node=port_map[e.to_node][0]))

        flat_ids = [n.id for n in nodes]
        deduped = {("edge", e.from_node, e.to_node): e for e in edges}
        flat_edges = list(deduped.values())
        entry_id = port_map[graph.entry_node][0]
        exit_id = port_map[graph.exit_node][1]
        _validate_single_entry_exit(entry_id, exit_id, flat_ids, flat_edges)
        return CompiledGraph(entry_node=entry_id, exit_node=exit_id, nodes=nodes, edges=flat_edges)

    def delete_scenario(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        asset = self._scenarios.get(code)
        if not asset:
            raise KeyError(f"场景 {code} 不在管理目录中（运行时内置管线不通过此入口删除）")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("scenario", code, actor["user_id"])

        removed_configs = []
        for cfg in orchestration_service.list_dag_configs(code):
            if orchestration_service.delete_dag_config(code, cfg.version):
                removed_configs.append(cfg.version)
        del self._scenarios[code]
        domain_persistence.delete("orchestration.catalog.scenarios", code)
        lock_manager.release("scenario", code, actor["user_id"], force=True)
        return {"code": code, "deleted": True, "removed_runtime_versions": removed_configs}

    # ------------------------------------------------------------------
    # misc
    # ------------------------------------------------------------------
    @staticmethod
    def _suggest_next_version(asset) -> str:
        existing = {v.version for v in asset.versions}
        base = None
        for v in asset.versions:
            m = re.match(r"^v(\d+)\.(\d+)\.(\d+)$", v.version)
            if m:
                cur = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if base is None or cur > base:
                    base = cur
        if base is None:
            candidate = "v1.0.0"
            suffix = 1
            while candidate in existing:
                suffix += 1
                candidate = f"v1.0.{suffix}"
            return candidate
        major, minor, patch = base
        while True:
            candidate = f"v{major}.{minor}.{patch + 1}"
            if candidate not in existing:
                return candidate
            patch += 1

    def subgraph_reference_holders(self, code: str) -> List[str]:
        holders: List[str] = []
        for sc in self._scenarios.values():
            for v in sc.versions:
                if v.status == VersionStatus.PUBLISHED and any(n.subgraph == code for n in v.graph.nodes):
                    holders.append(f"场景 {sc.code}@{v.version}")
        return holders

    # ------------------------------------------------------------------
    # hydration
    # ------------------------------------------------------------------
    def hydrate_operators(self, rows: List[Dict]) -> int:
        for r in rows or []:
            try:
                asset = OperatorAsset(**r)
            except Exception:
                continue
            self._operators[asset.name] = asset
        return len(rows or [])

    def hydrate_subgraphs(self, rows: List[Dict]) -> int:
        for r in rows or []:
            try:
                asset = SubgraphAsset(**r)
            except Exception:
                continue
            self._subgraphs[asset.code] = asset
        return len(rows or [])

    def hydrate_scenarios(self, rows: List[Dict]) -> int:
        for r in rows or []:
            try:
                asset = ScenarioAsset(**r)
            except Exception:
                continue
            self._scenarios[asset.code] = asset
        return len(rows or [])

    # ------------------------------------------------------------------
    # M1-1: deployment helper / rollback / release approvals
    # ------------------------------------------------------------------
    def _deploy_scenario_version(self, code: str, row: ScenarioVersion, ctx_project: str = "") -> Dict[str, Any]:
        """Compile (or reuse) a version graph, materialize and activate its DAG config."""
        compiled = row.compiled or self._compile_scenario(row, ctx_project)
        topology = {
            "topology": "DAG",
            "entry_node": compiled.entry_node,
            "exit_node": compiled.exit_node,
            "enable_saga_compensation": row.graph.enable_saga_compensation,
            "nodes": [
                {"id": n.id, "action_handler": n.action_handler, "type": n.type, "timeout_ms": n.timeout_ms}
                for n in compiled.nodes
            ],
            "edges": [{"from": e.from_node, "to": e.to_node} for e in compiled.edges],
        }
        orchestration_service.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code=code,
                version=row.version,
                topology_graph=topology,
                status="ACTIVE",
                created_by="catalog",
            )
        )
        orchestration_service.activate_dag_config(code, row.version)
        row.compiled = compiled
        return {
            "scenario_code": code,
            "version": row.version,
            "compiled_hash": orchestration_service.get_dag_config(code, row.version).compiled_hash,
        }

    def rollback_scenario(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Roll a scenario back to a previously published version (Argo CD semantics)."""
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        version = str(payload.get("version") or "").strip()
        asset = self._scenarios.get(code)
        if not asset:
            raise KeyError(f"场景 {code} 不存在")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("scenario", code, actor["user_id"])
        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"场景 {code} 不存在版本 {version}")
        if row.status == VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 是草稿，只有已发布/被取代版本可以回滚")

        now = utc_now_iso()
        for v in asset.versions:
            if v.status == VersionStatus.PUBLISHED:
                v.status = VersionStatus.SUPERSEDED
        row.status = VersionStatus.PUBLISHED
        row.published_by = actor["user_id"]
        row.published_at = now
        row.changelog = (f"{row.changelog} | " if row.changelog else "") + f"回滚 by {actor['user_id']} @ {now}"
        asset.current_version = row.version
        asset.updated_at = now
        deployed = self._deploy_scenario_version(code, row, ctx_project=self._ctx_project(context))
        self._persist_scenario(asset)
        return {**asset.model_dump(), "deployed_dag": deployed}

    def rollback_subgraph(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Roll a subgraph back to a published version.

        The rolled-back compiled graph binds at scenario compile time: running
        scenarios keep their inlined copy until republished (honest boundary).
        """
        actor = self._actor(payload, context)
        code = str(payload.get("code") or "").strip()
        version = str(payload.get("version") or "").strip()
        asset = self._subgraphs.get(code)
        if not asset:
            raise KeyError(f"子图 {code} 不存在")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("subgraph", code, actor["user_id"])
        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"子图 {code} 不存在版本 {version}")
        if row.status == VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 是草稿，只有已发布/被取代版本可以回滚")
        if row.compiled is None:
            row.compiled = self._compile_subgraph(row, ctx_project=self._ctx_project(context))

        now = utc_now_iso()
        for v in asset.versions:
            if v.status == VersionStatus.PUBLISHED:
                v.status = VersionStatus.SUPERSEDED
        row.status = VersionStatus.PUBLISHED
        row.published_by = actor["user_id"]
        row.published_at = now
        asset.current_version = row.version
        asset.updated_at = now
        self._persist_subgraph(asset)
        return asset.model_dump()

    def rollback_operator(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Roll a custom operator back to a published version (sandbox re-check + re-register)."""
        actor = self._actor(payload, context)
        name = str(payload.get("name") or "").strip()
        version = str(payload.get("version") or "").strip()
        asset = self._operators.get(name)
        if not asset:
            raise KeyError(f"算子 {name} 不存在或为内置算子")
        self._ensure_writable(asset.project_id, context)
        lock_manager.require("operator", name, actor["user_id"])
        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"算子 {name} 不存在版本 {version}")
        if row.status == VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 是草稿，只有已发布/被取代版本可以回滚")
        try:
            load_operator_from_source(row.definition.code, row.definition.entry_function)
        except ValueError as exc:
            raise ValueError(f"回滚前沙箱复检失败：{exc}") from exc
        script_ingestion_service.upload_and_register(
            name=name,
            code=row.definition.code,
            operator_id=actor["user_id"],
            entry_function=row.definition.entry_function,
            description=asset.description or asset.display_name,
            overwrite=True,
        )
        now = utc_now_iso()
        for v in asset.versions:
            if v.status == VersionStatus.PUBLISHED:
                v.status = VersionStatus.SUPERSEDED
        row.status = VersionStatus.PUBLISHED
        row.published_by = actor["user_id"]
        row.published_at = now
        asset.current_version = row.version
        asset.updated_at = now
        self._persist_operator(asset)
        return asset.model_dump()

    # -- release approvals (second-person rule, Apollo semantics) --------
    def request_release_approval(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        kind = str(payload.get("asset_kind") or "scenario").strip()
        code = str(payload.get("code") or "").strip()
        version = str(payload.get("version") or "").strip()
        if kind not in ("scenario", "subgraph", "operator"):
            raise ValueError(f"不支持的资产类型：{kind}")
        asset = {"scenario": self._scenarios, "subgraph": self._subgraphs, "operator": self._operators}[kind].get(code)
        if not asset:
            raise KeyError(f"{kind} {code} 不存在")
        self._require_visible(asset.project_id, code, kind, context)
        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"{kind} {code} 不存在版本 {version}")
        if row.status == VersionStatus.PUBLISHED:
            raise ValueError(f"版本 {version} 已是当前发布版本，无需审批")
        for pending in self._release_approvals.values():
            if (
                pending.status == "PENDING"
                and pending.asset_kind == kind
                and pending.code == code
                and pending.version == version
            ):
                raise ValueError(f"{code}@{version} 已有待审批的发布请求（{pending.id}）")
        approval = ReleaseApproval(
            id=uuid.uuid4().hex[:16],
            asset_kind=kind,
            code=code,
            version=version,
            requested_by=actor["user_id"],
            requested_at=utc_now_iso(),
            note=str(payload.get("note") or ""),
            project_id=str(asset.project_id or ""),
        )
        self._release_approvals[approval.id] = approval
        domain_persistence.write("orchestration.release_approvals", approval.id, approval.model_dump())
        return approval.model_dump()

    def approve_release(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Second-person approval: the approver must differ from the requester."""
        actor = self._actor(payload, context)
        approval_id = str(payload.get("approval_id") or "").strip()
        approval = self._release_approvals.get(approval_id)
        if not approval:
            raise KeyError(f"审批单 {approval_id} 不存在")
        self._require_visible(approval.project_id, approval.code, "审批单", context)
        if approval.status != "PENDING":
            raise ValueError(f"审批单 {approval_id} 状态为 {approval.status}")
        if approval.requested_by == actor["user_id"]:
            raise ValueError("发布审批需要第二人确认：审批人不能与发起人相同")

        # A DRAFT version publishes; a SUPERSEDED version rolls back into place.
        # Both execute under the REQUESTER's identity (they hold the edit lock
        # and authored the change); the approver only authorizes.
        asset = {"scenario": self._scenarios, "subgraph": self._subgraphs, "operator": self._operators}[approval.asset_kind][approval.code]
        row = next(v for v in asset.versions if v.version == approval.version)
        if row.status == "DRAFT":
            action = {"scenario": "scenarios.publish", "subgraph": "subgraphs.publish",
                      "operator": "operators.publish"}[approval.asset_kind]
        else:
            action = {"scenario": "scenarios.rollback", "subgraph": "subgraphs.rollback",
                      "operator": "operators.rollback"}[approval.asset_kind]
        code_field = {"scenario": "code", "subgraph": "code", "operator": "name"}[approval.asset_kind]
        publish_context = {**context, "user_id": approval.requested_by}
        try:
            result = dispatch_catalog_action(action, {code_field: approval.code, "version": approval.version}, publish_context)
        except Exception:
            raise
        approval.status = "APPROVED"
        approval.approver = actor["user_id"]
        approval.approved_at = utc_now_iso()
        domain_persistence.write("orchestration.release_approvals", approval.id, approval.model_dump())
        return {"approval": approval.model_dump(), "published": result}

    def reject_release(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
        approval_id = str(payload.get("approval_id") or "").strip()
        approval = self._release_approvals.get(approval_id)
        if not approval:
            raise KeyError(f"审批单 {approval_id} 不存在")
        self._require_visible(approval.project_id, approval.code, "审批单", context)
        if approval.status != "PENDING":
            raise ValueError(f"审批单 {approval_id} 状态为 {approval.status}")
        approval.status = "REJECTED"
        approval.approver = actor["user_id"]
        approval.approved_at = utc_now_iso()
        approval.note = (f"{approval.note} | " if approval.note else "") + str(payload.get("note") or "已驳回")
        domain_persistence.write("orchestration.release_approvals", approval.id, approval.model_dump())
        return approval.model_dump()

    def list_release_approvals(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        status = str(payload.get("status") or "").strip()
        ctx_project = self._ctx_project(context)
        rows = [
            a.model_dump() for a in self._release_approvals.values()
            if self._visible(a.project_id, ctx_project)
        ]
        if status:
            rows = [r for r in rows if r["status"] == status]
        rows.sort(key=lambda r: r["requested_at"], reverse=True)
        return {"approvals": rows, "total": len(rows)}

    # -- cross-project sharing（显式复制，项目完全隔离下的唯一复用通道） ----
    def copy_asset(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """把一个目录资产显式复制到另一个项目（目标项目需编排写权限）。

        版本历史原样保留（含各版本的原作者/发布人溯源）；副本归属目标项目，
        由执行复制的人在目标项目内继续演进。
        """
        actor = self._actor(payload, context)
        kind = str(payload.get("asset_kind") or "scenario").strip()
        code = str(payload.get("code") or "").strip()
        target_project_id = str(payload.get("target_project_id") or "").strip()
        if kind not in ("scenario", "subgraph", "operator"):
            raise ValueError(f"不支持的资产类型：{kind}")
        if not target_project_id:
            raise ValueError("必须指定目标项目 target_project_id")
        if not self._can_write_project(context, target_project_id):
            raise PermissionError("权限不足：缺少目标项目的编排写权限")

        stores = {"scenario": self._scenarios, "subgraph": self._subgraphs, "operator": self._operators}
        asset = stores[kind].get(code)
        if not asset:
            raise KeyError(f"{kind} {code} 不存在")
        # 源可见性：项目资产需对发起人可读（源项目成员或超管），否则按不存在处理
        if asset.project_id and not self._is_super(context):
            uid = actor["user_id"]
            try:
                from src.domains.platform.service import platform_service

                readable = platform_service.has_scoped_permission(uid, "orchestration:read", project_id=asset.project_id)
            except Exception:
                readable = False
            if not readable:
                raise KeyError(f"{kind} {code} 不存在")

        new_code = str(payload.get("new_code") or "").strip()
        if new_code and new_code != code and not ASSET_CODE_PATTERN.match(new_code):
            raise ValueError("新编码需以字母开头，仅含字母/数字/下划线/点号/横线，长度 2-64")
        if not new_code:
            # 编码全局唯一（运行时算子池按名注册）：目标已占用时自动派生空闲编码
            new_code = code
            serial = 1
            while new_code in stores[kind]:
                serial += 1
                new_code = f"{code}_{serial}"
        elif new_code in stores[kind]:
            raise ValueError(f"编码 {new_code} 已存在，请换一个编码")

        copied = asset.model_copy(deep=True, update={
            ("name" if kind == "operator" else "code"): new_code,
            "project_id": target_project_id,
            "created_by": actor["user_id"],
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "lock_status": None,
        })
        stores[kind][new_code] = copied
        if kind == "operator":
            self._persist_operator(copied)
        elif kind == "subgraph":
            self._persist_subgraph(copied)
        else:
            self._persist_scenario(copied)
        return copied.model_dump()

    def hydrate_release_approvals(self, rows: List[Dict]) -> int:
        for r in rows or []:
            if isinstance(r, dict) and r.get("id"):
                self._release_approvals[r["id"]] = ReleaseApproval(**r)
        return len(self._release_approvals)


catalog_service = CatalogService()

# 写操作动作表：所有目录变更统一经 OPC_ORCHESTRATION_CATALOG_PIPELINE 的
# guard → persist → telemetry 算子链执行（写走 DAG 的框架约定）。
class ReleaseApproval(BaseModel):
    """One publish-approval ticket (second-person rule; persisted audit trail)."""
    id: str
    asset_kind: str
    code: str
    version: str
    requested_by: str
    requested_at: str
    status: str = "PENDING"
    approver: str = ""
    approved_at: str = ""
    note: str = ""
    project_id: str = ""  # 发起时所在项目（空 = 未归属资产）


CATALOG_ACTIONS: Dict[str, str] = {
    "operators.create": "create_operator",
    "operators.version.save": "save_operator_version",
    "operators.publish": "publish_operator",
    "operators.delete": "delete_operator",
    "subgraphs.create": "create_subgraph",
    "subgraphs.version.save": "save_subgraph_version",
    "subgraphs.publish": "publish_subgraph",
    "scenarios.create": "create_scenario",
    "scenarios.version.save": "save_scenario_version",
    "scenarios.publish": "publish_scenario",
    "scenarios.delete": "delete_scenario",
    "scenarios.rollback": "rollback_scenario",
    "subgraphs.rollback": "rollback_subgraph",
    "operators.rollback": "rollback_operator",
    "approvals.request": "request_release_approval",
    "approvals.approve": "approve_release",
    "approvals.reject": "reject_release",
    "assets.copy": "copy_asset",
}


def dispatch_catalog_action(action: str, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one catalog mutation by action name (called by the persist operator)."""
    method_name = CATALOG_ACTIONS.get(action)
    if not method_name:
        raise ValueError(f"未知的目录操作：{action}")
    method = getattr(catalog_service, method_name)
    return method(payload or {}, context or {})


domain_persistence.register("orchestration.catalog.operators", catalog_service.hydrate_operators)
domain_persistence.register("orchestration.catalog.subgraphs", catalog_service.hydrate_subgraphs)
domain_persistence.register("orchestration.catalog.scenarios", catalog_service.hydrate_scenarios)
domain_persistence.register("orchestration.release_approvals", catalog_service.hydrate_release_approvals)
