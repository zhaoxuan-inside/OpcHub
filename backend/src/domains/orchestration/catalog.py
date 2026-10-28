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
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.core.microkernel.dispatcher import dispatcher
from src.core.microkernel.sandbox import load_operator_from_source
from src.core.microkernel.script_ingestion import (
    OPERATOR_NAME_PATTERN,
    script_ingestion_service,
)
from src.domains.orchestration.locks import AssetLock, lock_manager
from src.domains.orchestration.models import DAGConfigSaveRequest
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

    def list_operators(self) -> List[OperatorAsset]:
        usage = self._usage_map()
        rows: List[OperatorAsset] = []
        for asset in self._operators.values():
            asset.lock_status = lock_manager.status("operator", asset.name)
            descriptor = self._builtin_descriptor(asset.name)
            if descriptor:
                asset.runtime_mode = descriptor.mode.value
            elif asset.current_version:
                asset.runtime_mode = dispatcher.get_operator_mode(asset.name)[0].value
            else:
                asset.runtime_mode = ""
            holders = sorted(set(usage.get(asset.name, [])))
            asset.in_use = bool(holders)
            asset.referenced_by = holders
            rows.append(asset)

        managed = set(self._operators.keys())
        for desc in dispatcher.list_descriptors():
            if desc.name in managed:
                continue
            rows.append(self._builtin_asset(desc.name, usage))
        rows.sort(key=lambda a: (a.source != "builtin", a.domain, a.name))
        return rows

    def get_operator(self, name: str) -> OperatorAsset:
        usage = self._usage_map()
        asset = self._operators.get(name)
        if asset:
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
    def _builtin_descriptor(name: str):
        for desc in dispatcher.list_descriptors():
            if desc.name == name:
                return desc
        return None

    def _resolve_custom_operator_version(self, name: str, version_ref: str) -> OperatorVersion:
        """Resolve a managed custom operator reference to a PUBLISHED version."""
        asset = self._operators.get(name)
        if not asset:
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
        # 版本定义即算子调度配置的权威来源：发布时同步调度模式
        from src.core.microkernel.dispatcher import DispatchMode

        dispatcher.set_operator_mode(
            name,
            DispatchMode(row.definition.dispatch_mode or "IN_PROCESS"),
            row.definition.remote_endpoint,
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
    def list_subgraphs(self) -> List[SubgraphAsset]:
        rows = []
        for asset in self._subgraphs.values():
            asset.lock_status = lock_manager.status("subgraph", asset.code)
            rows.append(asset)
        rows.sort(key=lambda a: a.code)
        return rows

    def get_subgraph(self, code: str) -> SubgraphAsset:
        asset = self._subgraphs.get(code)
        if not asset:
            raise KeyError(f"子图 {code} 不存在")
        asset.lock_status = lock_manager.status("subgraph", code)
        return asset

    def _resolve_subgraph_version(self, code: str, version_ref: str) -> SubgraphVersion:
        asset = self._subgraphs.get(code)
        if not asset:
            raise KeyError(f"子图 {code} 不存在")
        target = version_ref or asset.current_version
        for v in asset.versions:
            if v.version == target and v.status == VersionStatus.PUBLISHED:
                return v
        raise ValueError(f"子图 {code}@{target or '最新'} 未发布或不存在，仅可编排已发布子图版本")

    def _validate_subgraph_graph(self, graph: SubgraphGraph, strict: bool) -> None:
        if not graph.nodes:
            raise ValueError("子图至少需要一个算子节点")
        _validate_structure(graph.entry_node, graph.exit_node, [n.id for n in graph.nodes], graph.edges)
        for n in graph.nodes:
            if self._operators.get(n.operator):
                if strict and (n.operator_version and not any(
                    v.version == n.operator_version and v.status == VersionStatus.PUBLISHED
                    for v in self._operators[n.operator].versions
                )):
                    raise ValueError(f"节点 {n.id} 引用的算子 {n.operator}@{n.operator_version} 未发布")
            elif not self._builtin_descriptor(n.operator):
                raise ValueError(f"节点 {n.id} 引用了不存在的算子 {n.operator}")
        if strict:
            _validate_single_entry_exit(graph.entry_node, graph.exit_node, [n.id for n in graph.nodes], graph.edges)

    def create_subgraph(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._actor(payload, context)
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
        lock_manager.require("subgraph", code, actor["user_id"])
        now = utc_now_iso()
        version = str(payload.get("version") or "").strip()

        graph = SubgraphGraph(**(payload.get("graph") or {}))
        self._validate_subgraph_graph(graph, strict=False)

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
        lock_manager.require("subgraph", code, actor["user_id"])

        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"子图 {code} 不存在版本 {version}")
        if row.status != VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 状态为 {row.status.value}，只有草稿可以发布")

        compiled = self._compile_subgraph(row)
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

    def _compile_subgraph(self, row: SubgraphVersion) -> CompiledGraph:
        """Resolve operator references into an executable flat operator graph."""
        graph = row.graph
        self._validate_subgraph_graph(graph, strict=True)
        nodes: List[CompiledNode] = []
        for n in graph.nodes:
            if self._operators.get(n.operator):
                self._resolve_custom_operator_version(n.operator, n.operator_version)
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
    def list_scenarios(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        managed_codes = set()
        for asset in self._scenarios.values():
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

    def get_scenario(self, code: str) -> Dict[str, Any]:
        asset = self._scenarios.get(code)
        if asset:
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
        )
        self._scenarios[code] = asset
        self._persist_scenario(asset)
        return asset.model_dump()

    def _validate_scenario_graph(self, graph: ScenarioGraph, strict: bool) -> None:
        if not graph.nodes:
            raise ValueError("场景至少需要一个节点")
        _validate_structure(graph.entry_node, graph.exit_node, [n.id for n in graph.nodes], graph.edges)
        for n in graph.nodes:
            if n.kind == "SUBGRAPH":
                sub = self._subgraphs.get(n.subgraph)
                if not sub:
                    raise ValueError(f"节点 {n.id} 引用了不存在的子图 {n.subgraph}")
                if strict:
                    self._resolve_subgraph_version(n.subgraph, n.subgraph_version)
            elif n.kind == "OPERATOR":
                if self._operators.get(n.operator):
                    if strict:
                        self._resolve_operator_handler(n.operator, n.operator_version)
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
        lock_manager.require("scenario", code, actor["user_id"])
        now = utc_now_iso()
        version = str(payload.get("version") or "").strip()

        graph = ScenarioGraph(**(payload.get("graph") or {}))
        self._validate_scenario_graph(graph, strict=False)

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
        lock_manager.require("scenario", code, actor["user_id"])

        row = next((v for v in asset.versions if v.version == version), None)
        if not row:
            raise KeyError(f"场景 {code} 不存在版本 {version}")
        if row.status != VersionStatus.DRAFT:
            raise ValueError(f"版本 {version} 状态为 {row.status.value}，只有草稿可以发布")

        compiled = self._compile_scenario(row)
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
                created_by=actor["user_id"],
            )
        )
        orchestration_service.activate_dag_config(code, row.version)

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
        self._persist_scenario(asset)
        return {
            **asset.model_dump(),
            "deployed_dag": {
                "scenario_code": code,
                "version": row.version,
                "compiled_hash": orchestration_service.get_dag_config(code, row.version).compiled_hash,
            },
        }

    def _compile_scenario(self, row: ScenarioVersion) -> CompiledGraph:
        """Expand subgraph nodes inline and produce the executable flat DAG."""
        graph = row.graph
        self._validate_scenario_graph(graph, strict=True)

        nodes: List[CompiledNode] = []
        edges: List[GraphEdge] = []
        port_map: Dict[str, Tuple[str, str]] = {}  # scenario node id -> (entry id, exit id)

        for n in graph.nodes:
            if n.kind == "SUBGRAPH":
                sub_ver = self._resolve_subgraph_version(n.subgraph, n.subgraph_version)
                compiled_sub = sub_ver.compiled or self._compile_subgraph(sub_ver)
                prefix = f"{n.id}::"
                for cn in compiled_sub.nodes:
                    nodes.append(CompiledNode(id=prefix + cn.id, action_handler=cn.action_handler, type=cn.type, timeout_ms=cn.timeout_ms))
                for e in compiled_sub.edges:
                    edges.append(GraphEdge(from_node=prefix + e.from_node, to_node=prefix + e.to_node))
                port_map[n.id] = (prefix + compiled_sub.entry_node, prefix + compiled_sub.exit_node)
            else:
                if self._operators.get(n.operator):
                    self._resolve_custom_operator_version(n.operator, n.operator_version)
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


catalog_service = CatalogService()

# 写操作动作表：所有目录变更统一经 OPC_ORCHESTRATION_CATALOG_PIPELINE 的
# guard → persist → telemetry 算子链执行（写走 DAG 的框架约定）。
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
