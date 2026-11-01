"""运营平台数据面：全量真实数据聚合（Umami/GrowthBook 读出模式承载）。

数据源（不造埋点、不放假数）：
* 实体计数 —— entity_store（内容/用户/互动在册量）；
* 审计流 —— 每个授权场景的执行留痕（actor×动作×时间），是漏斗/留存/趋势的
  事实来源；样本量与覆盖窗口在响应中如实披露；
* 运行记录 —— ops 域落库的场景执行（按日趋势）。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

# 运营概览实体口径（与 OPC_OPS_DASHBOARD 同一实体名清单）
OVERVIEW_ENTITIES = (
    "user.account",
    "forum.thread",
    "product.item",
    "demands.item",
    "policy.item",
    "perk.item",
    "sop.template",
    "interaction.record",
)

SAMPLE_CAP = 5000  # 分析样本上限（审计流最近 N 条），响应中披露


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit_sample() -> List[Dict[str, Any]]:
    from src.core.audit import audit_service

    return await audit_service.list_logs(limit=SAMPLE_CAP)


def bizops_overview_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Dict[str, Any]:
    """KPI 总览：实体在册量 + 近期活动量（真实计数）。"""
    from src.core.entity.store import entity_store
    from src.domains.ops.service import ops_run_service

    entities: Dict[str, int] = {}
    for name in OVERVIEW_ENTITIES:
        try:
            entities[name] = entity_store.count(name)
        except Exception:
            entities[name] = 0

    day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    runs_24h = sum(
        1 for r in ops_run_service._records.values() if r.started_at >= day_ago
    )
    return {"entities": entities, "runs_24h": runs_24h, "generated_at": _now_iso()}


async def bizops_actions_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Dict[str, Any]:
    """高频动作清单（漏斗步骤的真实可选值，按出现次数排序）。"""
    sample = await _audit_sample()
    counts: Dict[str, int] = defaultdict(int)
    for row in sample:
        counts[str(row.get("action") or "")] += 1
    counts.pop("", None)
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:50]
    return {
        "actions": [{"action": a, "count": n} for a, n in top],
        "sample_size": len(sample),
        "note": "样本为审计流最近记录（上限 5000），覆盖窗口随流量浮动",
    }


async def bizops_trend_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Dict[str, Any]:
    """按日趋势：审计事件数（按动作大类）+ 场景运行数（运行记录，窗口≤14 天）。"""
    from src.domains.ops.service import ops_run_service

    days = max(1, min(int((p or {}).get("days") or 14), 14))
    today = datetime.now(timezone.utc).date()
    day_keys = [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]

    sample = await _audit_sample()
    audit_by_day: Dict[str, Dict[str, int]] = {d: {"events": 0, "denied": 0, "actors": 0} for d in day_keys}
    actors_per_day: Dict[str, set] = {d: set() for d in day_keys}
    for row in sample:
        created = str(row.get("created_at") or "")[:10]
        if created not in audit_by_day:
            continue
        audit_by_day[created]["events"] += 1
        if row.get("result") == "DENIED":
            audit_by_day[created]["denied"] += 1
        if row.get("actor_id"):
            actors_per_day[created].add(row["actor_id"])
    for d in day_keys:
        audit_by_day[d]["actors"] = len(actors_per_day[d])

    runs_by_day: Dict[str, int] = {d: 0 for d in day_keys}
    for r in ops_run_service._records.values():
        day = r.started_at[:10]
        if day in runs_by_day:
            runs_by_day[day] += 1

    return {
        "days": day_keys,
        "series": [
            {
                "day": d,
                "events": audit_by_day[d]["events"],
                "denied": audit_by_day[d]["denied"],
                "active_actors": audit_by_day[d]["actors"],
                "scenario_runs": runs_by_day[d],
            }
            for d in day_keys
        ],
        "sample_size": len(sample),
        "note": "审计样本上限 5000 条；场景运行数覆盖运行记录保留期（默认 14 天）",
    }


async def bizops_funnel_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Dict[str, Any]:
    """业务漏斗：按步骤动作统计去重操作者数（精确口径：步骤内去重人数，
    非严格时序先后 —— 时序归因需事件序号，留待 T14 控制面）。"""
    steps = [str(s).strip() for s in (p or {}).get("steps") or [] if str(s).strip()]
    if not steps:
        raise ValueError("漏斗步骤不能为空（steps 为动作名列表，可从 bizops.actions 选取）")
    sample = await _audit_sample()
    actors_per_step: List[set] = [set() for _ in steps]
    for row in sample:
        action = str(row.get("action") or "")
        actor = row.get("actor_id")
        if not actor:
            continue
        for i, step in enumerate(steps):
            if action == step or action.startswith(step):
                actors_per_step[i].add(actor)
    first = len(actors_per_step[0]) if actors_per_step else 0
    step_rows = [
        {
            "step": step,
            "actors": len(actors),
            "conversion_from_first": round(len(actors) / first, 4) if first else 0.0,
        }
        for step, actors in zip(steps, actors_per_step)
    ]
    return {
        "steps": step_rows,
        "sample_size": len(sample),
        "note": "口径：各步骤去重操作者数与首步转化率（非严格时序漏斗）",
    }


async def bizops_retention_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Dict[str, Any]:
    """留存：操作者 × 日活跃矩阵（真实审计足迹），输出 D1/D7 次日/周留存率。"""
    days = max(2, min(int((p or {}).get("days") or 14), 14))
    today = datetime.now(timezone.utc).date()
    day_keys = [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]
    day_index = {d: i for i, d in enumerate(day_keys)}

    sample = await _audit_sample()
    actor_days: Dict[str, set] = defaultdict(set)
    for row in sample:
        created = str(row.get("created_at") or "")[:10]
        actor = row.get("actor_id")
        if actor and created in day_index:
            actor_days[actor].add(day_index[created])

    # 以首次活跃日为 cohort 起点，计算 D1/D7 复访
    d1_pairs = d7_pairs = cohort = 0
    matrix_rows: List[Dict[str, Any]] = []
    for actor, day_set in actor_days.items():
        start = min(day_set)
        cohort += 1
        d1 = (start + 1) in day_set
        d7 = (start + 7) in day_set
        d1_pairs += 1 if d1 else 0
        d7_pairs += 1 if d7 else 0
        matrix_rows.append({"actor_id": actor, "first_day": day_keys[start], "active_days": sorted(day_set), "d1": d1, "d7": d7})

    return {
        "days": day_keys,
        "cohort_size": cohort,
        "d1_rate": round(d1_pairs / cohort, 4) if cohort else 0.0,
        "d7_rate": round(d7_pairs / cohort, 4) if cohort else 0.0,
        "actors": matrix_rows[:200],  # 明细截断（前端活跃网格）
        "sample_size": len(sample),
        "note": "口径：窗口内以审计足迹判定活跃；D1/D7 为首活跃日后的复访率",
    }
