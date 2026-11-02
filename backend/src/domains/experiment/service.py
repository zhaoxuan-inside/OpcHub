"""实验域服务：实验生命周期、确定性分流、结果上报与读出。

* 分流（assign）是数据面高频调用：sha256 稳定分桶（同一用户永远落在同一变体）、
  traffic_percent 门控、权重归一切分；首次命中落分配记录（粘性），此后幂等返回。
* 生命周期：DRAFT → RUNNING ⇄ STOPPED → ARCHIVED；RUNNING 状态下允许调
  变体权重与流量（真实 A/B 实践），改 key/变体键需回 DRAFT。
* 持久化：experiment.experiments / experiment.assignments（domain_persistence
  write-behind + hydrate）；变异前 require()（strict，无 DB 拒绝）。
* 权限：管理操作由网关声明 experiment:manage + scope:project 强制，服务层
  以 platform 绑定纵深复核；assign/report_outcome 仅要求登录身份（宿主客户端
  数据面调用）。
"""
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.core.rbac import P_EXPERIMENT_MANAGE, has_permission, normalize_role
from src.domains.experiment.models import AssignmentRecord, Experiment, Outcome, Variant
from src.infrastructure.database.persistence import domain_persistence

FAMILY_EXPERIMENTS = "experiment.experiments"
FAMILY_ASSIGNMENTS = "experiment.assignments"

EXPERIMENT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,47}$")
VARIANT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
BUCKETS = 10000  # 分桶空间：0..9999

# 状态机：DRAFT → RUNNING ⇄ STOPPED → ARCHIVED
STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    "DRAFT": {"RUNNING"},
    "RUNNING": {"STOPPED"},
    "STOPPED": {"RUNNING", "ARCHIVED"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def bucket_of(experiment_key: str, user_id: str) -> int:
    """稳定分桶：同一 (实验, 用户) 永远得到同一桶号 0..9999。"""
    digest = hashlib.sha256(f"{experiment_key}:{user_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % BUCKETS


def pick_variant(bucket: int, variants: List[Variant], traffic_percent: int) -> str:
    """流量门控 + 权重归一切分。未入流返回空串（宿主按控制组处理）。"""
    if traffic_percent <= 0 or not variants:
        return ""
    if bucket % 100 >= traffic_percent:
        return ""
    total = sum(max(0.0, v.weight) for v in variants)
    if total <= 0:
        # 权重全为 0：均分（诚实兜底而非静默偏向）
        cursor = BUCKETS / len(variants)
        return variants[int(bucket // cursor) % len(variants)].key
    cumulative = 0.0
    for v in variants:
        cumulative += max(0.0, v.weight) / total * BUCKETS
        if bucket < cumulative:
            return v.key
    return variants[-1].key


class ExperimentService:
    """实验注册表 + 分配记录（内存索引为运行时读路径）。"""

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._assignments: Dict[str, AssignmentRecord] = {}  # key: exp_key:user_id

    # ------------------------------------------------------------------
    # 权限与隔离 helpers（与编排目录同构）
    # ------------------------------------------------------------------
    @staticmethod
    def _actor(context: Optional[Dict[str, Any]]) -> str:
        uid = str((context or {}).get("user_id") or "").strip()
        if not uid:
            raise PermissionError("UNAUTHORIZED:实验操作需要登录身份")
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

    def _require_manage(self, context: Optional[Dict[str, Any]], project_id: str) -> str:
        uid = self._actor(context)
        role = normalize_role((context or {}).get("user_role", ""))
        if has_permission(role, P_EXPERIMENT_MANAGE):
            return uid
        try:
            from src.domains.platform.service import platform_service

            if platform_service.has_scoped_permission(
                uid, P_EXPERIMENT_MANAGE, project_id=project_id
            ):
                return uid
        except Exception:
            pass
        raise PermissionError("权限不足：缺少所需权限 'experiment:manage'")

    def _visible(self, experiment_project: str, ctx_project: str) -> bool:
        return (not experiment_project) or (not ctx_project) or experiment_project == ctx_project

    def _require_readable(self, experiment: Experiment, context: Optional[Dict[str, Any]]) -> None:
        from src.core.rbac import P_EXPERIMENT_READ

        if self._visible(experiment.project_id, self._ctx_project(context)):
            return
        uid = self._actor(context)
        try:
            from src.domains.platform.service import platform_service

            if platform_service.has_scoped_permission(
                uid, P_EXPERIMENT_READ, project_id=experiment.project_id
            ):
                return
        except Exception:
            pass
        raise KeyError(f"实验 {experiment.key} 不存在")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def create_experiment(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ctx_project = self._ctx_project(context)
        actor = self._require_manage(context, ctx_project)
        key = str(payload.get("key") or "").strip()
        if not EXPERIMENT_KEY_PATTERN.match(key):
            raise ValueError("实验标识非法：2-48 位小写字母/数字/下划线/横线，字母开头")
        if key in self._experiments:
            raise ValueError(f"实验标识已存在：{key}")
        variants = self._validate_variants(payload.get("variants") or [])
        traffic = self._validate_traffic(payload.get("traffic_percent", 100))
        env_key = str(payload.get("env_key") or "").strip()[:32]
        domain_persistence.require(FAMILY_EXPERIMENTS)
        now = _now_iso()
        experiment = Experiment(
            experiment_id=_new_id("exp"),
            key=key,
            name=str(payload.get("name") or key),
            description=str(payload.get("description") or ""),
            variants=variants,
            traffic_percent=traffic,
            env_key=env_key,
            project_id=ctx_project,
            created_by=actor,
            created_at=now,
            updated_at=now,
        )
        self._experiments[key] = experiment
        domain_persistence.write(FAMILY_EXPERIMENTS, key, experiment)
        return experiment.model_dump()

    def update_experiment(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self._require_experiment(payload, context, manage=True)
        if experiment.status == "ARCHIVED":
            raise ValueError("实验已归档，不可修改")
        if "name" in payload:
            experiment.name = str(payload["name"])
        if "description" in payload:
            experiment.description = str(payload["description"])
        if "traffic_percent" in payload:
            experiment.traffic_percent = self._validate_traffic(payload["traffic_percent"])
        if "env_key" in payload:
            experiment.env_key = str(payload.get("env_key") or "").strip()[:32]
        if "variants" in payload:
            new_variants = self._validate_variants(payload["variants"])
            if experiment.status == "RUNNING" and {v.key for v in new_variants} != {v.key for v in experiment.variants}:
                raise ValueError("运行中的实验不可增删变体（只可调权重），请先停止")
            experiment.variants = new_variants
        experiment.updated_at = _now_iso()
        domain_persistence.write(FAMILY_EXPERIMENTS, experiment.key, experiment)
        return experiment.model_dump()

    def set_experiment_status(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self._require_experiment(payload, context, manage=True)
        target = str(payload.get("status") or "").strip().upper()
        if target not in STATUS_TRANSITIONS.get(experiment.status, set()):
            raise ValueError(f"状态不允许从 {experiment.status} 变更为 {target}")
        if target == "RUNNING" and not experiment.variants:
            raise ValueError("启动实验前至少配置一个变体")
        experiment.status = target
        experiment.updated_at = _now_iso()
        domain_persistence.write(FAMILY_EXPERIMENTS, experiment.key, experiment)
        return experiment.model_dump()

    def delete_experiment(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self._require_experiment(payload, context, manage=True)
        if experiment.status == "RUNNING":
            raise ValueError("运行中的实验不可删除，请先停止")
        domain_persistence.delete(FAMILY_EXPERIMENTS, experiment.key)
        self._experiments.pop(experiment.key, None)
        return {"deleted": experiment.key}

    def list_experiments(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ctx_project = self._ctx_project(context)
        rows = [
            e.model_dump() for e in self._experiments.values() if self._visible(e.project_id, ctx_project)
        ]
        status = str(payload.get("status") or "").strip().upper()
        if status:
            rows = [r for r in rows if r["status"] == status]
        rows.sort(key=lambda r: r["created_at"])
        return {"experiments": rows, "total": len(rows)}

    def get_experiment(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return self._require_experiment(payload, context, manage=False).model_dump()

    # ------------------------------------------------------------------
    # 数据面：分流 / 结果上报
    # ------------------------------------------------------------------
    def assign(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        user_id = self._resolve_subject(payload, context, "experiment:manage")
        key = str(payload.get("experiment_key") or "").strip()
        experiment = self._experiments.get(key)
        if experiment is None:
            # 宿主页面不应因误配实验键而报错：诚实返回控制组
            return {"experiment_key": key, "variant": "", "in_experiment": False, "reason": "NOT_FOUND"}
        if experiment.status != "RUNNING":
            return {"experiment_key": key, "variant": "", "in_experiment": False, "reason": experiment.status}
        ctx_env = str((context or {}).get("env_key") or "").strip()
        if experiment.env_key and ctx_env and experiment.env_key != ctx_env:
            return {"experiment_key": key, "variant": "", "in_experiment": False, "reason": "ENV_MISMATCH"}
        bucket = bucket_of(key, user_id)
        variant_key = pick_variant(bucket, experiment.variants, experiment.traffic_percent)
        if not variant_key:
            return {"experiment_key": key, "variant": "", "in_experiment": False, "reason": "TRAFFIC"}
        sticky_key = f"{key}:{user_id}"
        record = self._assignments.get(sticky_key)
        if record is None:
            domain_persistence.require(FAMILY_ASSIGNMENTS)
            record = AssignmentRecord(
                assignment_id=_new_id("asg"),
                experiment_key=key,
                user_id=user_id,
                variant_key=variant_key,
                in_experiment=True,
                project_id=experiment.project_id,
                assigned_at=_now_iso(),
            )
            self._assignments[sticky_key] = record
            domain_persistence.write(FAMILY_ASSIGNMENTS, sticky_key, record)
        return {"experiment_key": key, "variant": record.variant_key, "in_experiment": True}

    def report_outcome(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        user_id = self._resolve_subject(payload, context, "experiment:manage")
        key = str(payload.get("experiment_key") or "").strip()
        metric = str(payload.get("metric") or "").strip()
        if not metric:
            raise ValueError("结果指标名不能为空")
        record = self._assignments.get(f"{key}:{user_id}")
        if record is None:
            raise KeyError("该用户在此实验中没有分配记录（未入流或尚未分流）")
        try:
            value = float(payload.get("value") or 0)
        except (TypeError, ValueError):
            raise ValueError("结果值必须是数值")
        record.outcomes.append(Outcome(metric=metric, value=value, reported_at=_now_iso()))
        domain_persistence.write(FAMILY_ASSIGNMENTS, f"{key}:{user_id}", record)
        return {"experiment_key": key, "user_id": user_id, "metric": metric, "recorded": True}

    def readout(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self._require_experiment(payload, context, manage=False)
        by_variant: Dict[str, Dict[str, Any]] = {
            v.key: {"variant": v.key, "name": v.name, "weight": v.weight, "assignments": 0, "metrics": {}}
            for v in experiment.variants
        }
        for record in self._assignments.values():
            if record.experiment_key != experiment.key:
                continue
            slot = by_variant.get(record.variant_key)
            if slot is None:
                slot = by_variant.setdefault(
                    record.variant_key,
                    {"variant": record.variant_key, "name": "", "weight": 0, "assignments": 0, "metrics": {}},
                )
            slot["assignments"] += 1
            for outcome in record.outcomes:
                m = slot["metrics"].setdefault(outcome.metric, {"count": 0, "sum": 0.0})
                m["count"] += 1
                m["sum"] += outcome.value
        for slot in by_variant.values():
            for m in slot["metrics"].values():
                m["avg"] = round(m["sum"] / m["count"], 4) if m["count"] else 0.0
        total = sum(s["assignments"] for s in by_variant.values())
        return {
            "experiment": experiment.model_dump(),
            "total_assignments": total,
            "variants": list(by_variant.values()),
        }

    def _resolve_subject(self, payload: Dict[str, Any], context: Dict[str, Any], manage_permission: str) -> str:
        """数据面主体解析：身份一律取登录态；代查（payload.user_id）仅限管理者
        或平台超管 —— 防止匿名/越权冒充他人灰度分桶。"""
        uid = str((context or {}).get("user_id") or "").strip()
        requested = str(payload.get("user_id") or "").strip()
        if not uid:
            raise PermissionError("UNAUTHORIZED:该操作需要登录身份")
        if requested and requested != uid:
            if self._is_super(context):
                return requested
            experiment_project = self._ctx_project(context)
            try:
                from src.domains.platform.service import platform_service

                if platform_service.has_scoped_permission(uid, manage_permission, project_id=experiment_project):
                    return requested
            except Exception:
                pass
            raise PermissionError("权限不足：仅实验管理者可代其他用户试算")
        return uid

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _require_experiment(self, payload: Dict[str, Any], context: Dict[str, Any], manage: bool) -> Experiment:
        key = str(payload.get("experiment_key") or payload.get("key") or "").strip()
        experiment = self._experiments.get(key)
        if experiment is None:
            raise KeyError(f"实验 {key} 不存在")
        if manage:
            self._require_manage(context, experiment.project_id)
        else:
            self._require_readable(experiment, context)
        return experiment

    @staticmethod
    def _validate_variants(raw: Any) -> List[Variant]:
        if not isinstance(raw, list) or not raw:
            raise ValueError("实验至少需要一个变体")
        variants: List[Variant] = []
        keys: Set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("变体必须是 {key, name, weight} 对象")
            v = Variant(**item)
            if not VARIANT_KEY_PATTERN.match(v.key):
                raise ValueError(f"变体键非法：{v.key}")
            if v.key in keys:
                raise ValueError(f"变体键重复：{v.key}")
            keys.add(v.key)
            variants.append(v)
        return variants

    @staticmethod
    def _validate_traffic(raw: Any) -> int:
        try:
            traffic = int(raw)
        except (TypeError, ValueError):
            raise ValueError("流量百分比必须是 0-100 整数")
        if not 0 <= traffic <= 100:
            raise ValueError("流量百分比必须是 0-100 整数")
        return traffic

    # ------------------------------------------------------------------
    # Hydration（启动时由 domain_persistence 回放重建索引）
    # ------------------------------------------------------------------
    def hydrate_experiments(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows or []:
            try:
                experiment = Experiment(**row)
            except Exception:
                continue
            self._experiments[experiment.key] = experiment
        return len(rows or [])

    def hydrate_assignments(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows or []:
            try:
                record = AssignmentRecord(**row)
            except Exception:
                continue
            self._assignments[f"{record.experiment_key}:{record.user_id}"] = record
        return len(rows or [])


experiment_service = ExperimentService()

domain_persistence.register(FAMILY_EXPERIMENTS, experiment_service.hydrate_experiments)
domain_persistence.register(FAMILY_ASSIGNMENTS, experiment_service.hydrate_assignments)


# ----------------------------------------------------------------------
# MicroFlow 写路径：实验写操作动作表（经 OPC_EXPERIMENT_PIPELINE 元管线）
# ----------------------------------------------------------------------
EXPERIMENT_ACTIONS: Dict[str, str] = {
    "experiments.create": "create_experiment",
    "experiments.update": "update_experiment",
    "experiments.status": "set_experiment_status",
    "experiments.delete": "delete_experiment",
    "assign": "assign",
    "outcome.report": "report_outcome",
}


def dispatch_experiment_action(action: str, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    method_name = EXPERIMENT_ACTIONS.get(action)
    if not method_name:
        raise ValueError(f"未知的实验操作：{action}")
    method = getattr(experiment_service, method_name)
    return method(payload or {}, context or {})
