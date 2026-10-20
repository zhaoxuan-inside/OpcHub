"""Helper for generating home sitemap quick links."""
from typing import Any


def build_sitemap_quick_links(
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
            "name": "政策雷达",
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
            "count_desc": "最高 $5,000 算力补贴券",
            "tag": "福利",
            "description": "云厂商激活特权、Token 优惠券、Stripe 结汇通道及工具折扣。",
        },
        {
            "name": "合规指南",
            "route": "compliance",
            "count_desc": "6 大防线自检避坑雷达",
            "tag": "防线",
            "description": "六维合规防线、典型避坑案例库与上线前自检雷达。",
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
