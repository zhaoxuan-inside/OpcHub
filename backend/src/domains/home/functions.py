"""Single-responsibility pure assemblers for the home overview.

Only aggregation lives here: the counts are collected by ``entity.count`` /
``entity.list`` scenario nodes and handed in as arguments. This module performs
no I/O, imports no other domain and never orchestrates.
"""
from __future__ import annotations

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


def _quick_links(
    threads_count: int,
    products_count: int,
    policies_count: int,
    demands_count: int,
) -> list[dict[str, Any]]:
    return [
        {
            "name": "头脑风暴",
            "route": "forum",
            "count_desc": f"{threads_count} 篇讨论",
            "tag": "社区",
            "description": "灵感碰撞交流、出海实战答疑、经验置顶与干货讨论区。",
        },
        {
            "name": "产品橱窗",
            "route": "product",
            "count_desc": f"{products_count} 款独立商用作品",
            "tag": "商机",
            "description": "独立创客产品画廊，支持点赞打榜、产品收录与出海获客。",
        },
        {
            "name": "政策中心",
            "route": "policy",
            "count_desc": f"{policies_count} 条扶持减免红利",
            "tag": "政策",
            "description": "全网政策白话提炼，税收减免、算力返还与地方补贴精准匹配。",
        },
        {
            "name": "需求集市",
            "route": "demand",
            "count_desc": f"{demands_count} 笔外包寻源委托",
            "tag": "委托",
            "description": "真实企业寻源商机、AI Agent 外包撮合与资金托管担保。",
        },
        {
            "name": "流程文书",
            "route": "sop",
            "count_desc": "4 阶段合规材料即时生成",
            "tag": "文书",
            "description": "工商设立到离岸资金流全阶段表单收集，一键导出标准申报材料。",
        },
        {
            "name": "生态特权",
            "route": "perks",
            "count_desc": "Token 优惠 · 服务器 · SaaS 优惠公告",
            "tag": "福利",
            "description": "生态伙伴优惠公告板：Token 优惠券、云服务器折扣、SaaS 服务特惠与结汇通道。",
        },
        {
            "name": "合规指南",
            "route": "compliance",
            "count_desc": "法条库与避坑案例集",
            "tag": "法条",
            "description": "合规法条白话提炼、典型避坑案例库与免责声明。",
        },
        {
            "name": "创客档案",
            "route": "user",
            "count_desc": "权益凭据与会员中心",
            "tag": "主体",
            "description": "多级会员凭证强绑定、按量功能开关与支付鉴权控制中心。",
        },
        {
            "name": "后端编排",
            "route": "backend-orch",
            "count_desc": "微内核 DAG 可视化引擎",
            "tag": "架构",
            "description": "Python 脚本热上传、AST 安全沙箱验证与微内核 Scenario 路由编排。",
        },
    ]


@operator(
    "assemble.home.overview",
    category="ASSEMBLE",
    description="Assemble the public home overview document from domain counts",
)
def overview(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    products_count = _as_int(args.get("products_count"))
    threads_count = _as_int(args.get("forum_threads_count"))
    policies_count = _as_int(args.get("matched_policies_count"))
    demands_count = _as_int(args.get("demands_orders_count"))

    perks = args.get("perks")
    perks_saved = 0.0
    if isinstance(perks, list):
        perks_saved = round(
            sum(
                float(row.get("value_cny") or 0)
                for row in perks
                if isinstance(row, dict) and str(row.get("status") or "PUBLISHED") == "PUBLISHED"
            ),
            2,
        )

    active_makers = _distinct_makers(args.get("interaction_records"))
    if not active_makers:
        active_makers = _as_int(args.get("active_makers_count"))

    return {
        "region": str(args.get("region") or "全国"),
        "active_makers_count": active_makers,
        "active_dags_count": _as_int(args.get("active_dags_count")),
        "matched_policies_count": policies_count,
        "demands_orders_count": demands_count,
        "perks_saved_cny": perks_saved,
        "products_count": products_count,
        "forum_threads_count": threads_count,
        "quick_links": _quick_links(threads_count, products_count, policies_count, demands_count),
        "orchestrated": True,
        "orchestrated_by": str(params.get("orchestrated_by") or "OPC_HOME_OVERVIEW_PIPELINE"),
    }
