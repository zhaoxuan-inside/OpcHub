"""Single-responsibility pure assemblers for operational telemetry.

The module only turns already-collected domain counts into the ops dashboard
document. It performs no I/O, imports no other domain and never orchestrates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.operators.sdk import operator


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _distinct_makers(records: Any) -> int:
    if not isinstance(records, list):
        return 0
    user_ids = {
        str(row.get("user_id") or "").strip()
        for row in records
        if isinstance(row, dict) and row.get("user_id")
    }
    user_ids.discard("")
    return len(user_ids)


def _kpi(label: str, value: str, sub_text: str) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "delta_percent": 0.0,
        "trend": "UP",
        "sub_text": sub_text,
    }


_NO_SOURCE = "暂无埋点数据源，等待接入真实统计"


@operator(
    "assemble.telemetry.dashboard",
    category="ASSEMBLE",
    description="Assemble the ops dashboard document from live domain record counts",
)
def dashboard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    active_makers = _distinct_makers(args.get("interaction_records"))
    if not active_makers:
        active_makers = _as_int(args.get("active_makers_count"))

    module_counts = [
        ("政策中心", "POLICY", _as_int(args.get("policy_count"))),
        ("流程文书SOP", "SOP", _as_int(args.get("sop_count"))),
        ("头脑风暴", "FORUM", _as_int(args.get("forum_count"))),
        ("需求外包集市", "MARKET", _as_int(args.get("demand_count"))),
        ("产品橱窗", "GALLERY", _as_int(args.get("product_count"))),
        ("算力与特权", "PERKS", _as_int(args.get("perk_count"))),
        ("合规指南", "COMPLIANCE", _as_int(args.get("compliance_count"))),
    ]
    total_count = sum(count for _, _, count in module_counts) or 1
    module_heatmaps = [
        {
            "module_name": name,
            "code": code,
            "pv_count": count,
            "percentage": round(count / total_count * 100.0, 1) if count else 0.0,
            "color": "#0071E3",
        }
        for name, code, count in module_counts
        if count > 0
    ]

    now = datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(),
        "is_live": True,
        "time_range": str(args.get("time_range") or "7D"),
        "terminal_filter": str(args.get("terminal_filter") or "ALL"),
        "dau": _kpi("DAU 日活跃创客", str(active_makers), _NO_SOURCE),
        "uv": _kpi("UV 今日独立访客", "0", _NO_SOURCE),
        "pv": _kpi("PV 页面总浏览量", "0", _NO_SOURCE),
        "mau": _kpi("MAU 月活创客数", "0", _NO_SOURCE),
        "retention": _kpi("次日 / 7日留存率", "0% / 0%", _NO_SOURCE),
        "api_throughput": _kpi("微内核 API 吞吐", "0 次/日", _NO_SOURCE),
        "daily_trends": [
            {
                "date": now.strftime("%m-%d"),
                "pv": 0,
                "uv": 0,
                "dau": active_makers,
            }
        ],
        "module_heatmaps": module_heatmaps,
        "terminal_distribution": {
            "ios_percentage": 0.0,
            "android_percentage": 0.0,
            "desktop_web_percentage": 0.0,
        },
        "recent_gateway_logs": [],
        "orchestrated_by": str(params.get("orchestrated_by") or "OPC_OPS_DASHBOARD_PIPELINE"),
    }
