"""Default scenario route rules registration.

Registers all domain scenarios into ScenarioRouter, establishing the single
unified entrypoint dispatch table for the entire OpcHub platform.
"""
from src.core.gateway.router import scenario_router
from src.domains.products.service import product_service
from src.domains.products.models import ProductCreate
from src.domains.policies.service import policy_service
from src.domains.policies.models import PolicyCreate, PolicyMatchRequest
from src.domains.demands.service import demand_service
from src.domains.demands.models import DemandCreate, BidCreate
from src.domains.sop.service import sop_service
from src.domains.sop.models import SOPTemplateCreate, SOPDocumentCreate
from src.domains.perks.service import perk_service
from src.domains.perks.models import PerkCreate, PerkClaimRequest
from src.domains.forum.service import forum_service
from src.domains.forum.models import ForumThreadCreate, ForumCommentCreate
from src.domains.telemetry.service import telemetry_service
from src.domains.user.service import user_service
from src.domains.user.models import EntitlementActivateRequest
from src.domains.moderation.service import moderation_service
from src.domains.moderation.models import TakedownRequest, RestoreRequest
from src.domains.compliance.service import compliance_service
from src.domains.compliance.models import AuditEvaluateRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import (
    ScenarioExecuteRequest,
    FrontendLayoutSaveRequest,
    DAGConfigSaveRequest,
)
from src.core.microkernel.dispatcher import DualModeDispatcher


def register_default_scenario_routes():
    """Register all standard domain scenario rules into the router."""

    # 1. Product Showcase
    scenario_router.register(
        "products.list",
        lambda p, c: product_service.list_products(category=p.get("category")),
        domain="products",
        description="检索独立创客商业作品列表",
    )
    scenario_router.register(
        "products.publish",
        lambda p, c: product_service.create_product(ProductCreate(**p)),
        domain="products",
        description="发布新独立创客作品至橱窗",
    )
    scenario_router.register(
        "products.upvote",
        lambda p, c: product_service.upvote_product(p.get("product_id")),
        domain="products",
        description="为独立作品点赞打榜",
    )

    # 2. Policy Radar
    scenario_router.register(
        "policies.list",
        lambda p, c: policy_service.list_policies(category=p.get("category")),
        domain="policies",
        description="获取政府扶持与税收减免政策列表",
    )
    scenario_router.register(
        "policies.publish",
        lambda p, c: policy_service.create_policy(PolicyCreate(**p)),
        domain="policies",
        description="发布最新政府扶持与补贴政策",
    )
    scenario_router.register(
        "policies.match",
        lambda p, c: policy_service.match_policies(PolicyMatchRequest(**p)),
        domain="policies",
        description="测算创客免税资格与预计减免额",
    )

    # 3. Demands & Bidding
    scenario_router.register(
        "demands.list",
        lambda p, c: demand_service.list_demands(category=p.get("category")),
        domain="demands",
        description="检索企业委托寻源商机列表",
    )
    scenario_router.register(
        "demands.publish",
        lambda p, c: demand_service.create_demand(DemandCreate(**p)),
        domain="demands",
        description="发布企业外包委托与法律求助",
    )
    scenario_router.register(
        "demands.bid",
        lambda p, c: demand_service.submit_bid(
            demand_id=p.get("demand_id"),
            payload=BidCreate(**p.get("bid_payload", p)),
        ),
        domain="demands",
        description="提交创客竞标方案",
    )

    # 4. SOP & Compliance Documents
    scenario_router.register(
        "sop.templates",
        lambda p, c: sop_service.get_stages_and_templates(),
        domain="sop",
        description="获取合规流程阶段与文档模板列表",
    )
    scenario_router.register(
        "sop.template.publish",
        lambda p, c: sop_service.create_template(SOPTemplateCreate(**p)),
        domain="sop",
        description="发布并登记新合规文书模板",
    )
    scenario_router.register(
        "sop.document.render",
        lambda p, c: sop_service.render_and_save_document(SOPDocumentCreate(**p)),
        domain="sop",
        description="根据用户输入渲染并持久化合规文书",
    )
    scenario_router.register(
        "sop.document.get",
        lambda p, c: sop_service.get_document(p.get("doc_id")),
        domain="sop",
        description="按 ID 获取已生成的文书实例",
    )
    scenario_router.register(
        "sop.document.list",
        lambda p, c: sop_service.list_documents(user_id=p.get("user_id")),
        domain="sop",
        description="获取创客已保存的文书历史列表",
    )

    # 5. Perks & Infrastructure
    scenario_router.register(
        "perks.list",
        lambda p, c: perk_service.list_perks(),
        domain="perks",
        description="获取开发者基础设施折扣与算力福利列表",
    )
    scenario_router.register(
        "perks.publish",
        lambda p, c: perk_service.create_perk(PerkCreate(**p)),
        domain="perks",
        description="提报并上线生态特权福利",
    )
    scenario_router.register(
        "perks.claim",
        lambda p, c: perk_service.claim_perk(PerkClaimRequest(**p)),
        domain="perks",
        description="领取特权并生成专属兑换凭据",
    )

    # 6. Forum / Brainstorm
    scenario_router.register(
        "forum.threads.list",
        lambda p, c: forum_service.list_threads(category_code=p.get("category_code")),
        domain="forum",
        description="检索头脑风暴社区讨论帖列表",
    )
    scenario_router.register(
        "forum.threads.publish",
        lambda p, c: forum_service.create_thread(ForumThreadCreate(**p)),
        domain="forum",
        description="发布新创客讨论帖与踩坑复盘",
    )
    scenario_router.register(
        "forum.threads.get",
        lambda p, c: forum_service.get_thread(p.get("thread_id")),
        domain="forum",
        description="获取讨论帖详情与正文",
    )
    scenario_router.register(
        "forum.comments.create",
        lambda p, c: forum_service.create_comment(
            thread_id=p.get("thread_id"),
            payload=ForumCommentCreate(**p.get("comment_payload", p)),
        ),
        domain="forum",
        description="发表一级回答或物化路径嵌套子回复",
    )

    # 7. Telemetry & Home Overview
    scenario_router.register(
        "home.overview",
        lambda p, c: {
            "active_makers_count": 14820,
            "active_dags_count": 482,
            "matched_policies_count": 128,
            "demands_orders_count": 89,
            "perks_saved_cny": 1820000.0,
            "quick_links": [
                {"name": "头脑风暴", "route": "forum", "count_desc": "1,240 篇实战经验"},
                {"name": "流程文书", "route": "sop", "count_desc": "4 阶段合规材料"},
                {"name": "政策雷达", "route": "policy", "count_desc": "30万增值税免征"},
                {"name": "需求集市", "route": "demand", "count_desc": "89 笔进行中委托"},
                {"name": "生态特权", "route": "perks", "count_desc": "最高 $5,000 算力券"},
                {"name": "合规指南", "route": "compliance", "count_desc": "6大防线自检雷达"},
                {"name": "后端编排", "route": "backend-orch", "count_desc": "微内核 DAG 引擎"},
            ],
        },
        domain="telemetry",
        description="获取首页功能全景与平台宏观指标",
    )
    scenario_router.register(
        "telemetry.dashboard",
        lambda p, c: telemetry_service.get_dashboard_metrics(),
        domain="telemetry",
        description="全域运营大盘实时核心指标聚合",
    )
    scenario_router.register(
        "ops.dashboard",
        lambda p, c: telemetry_service.get_dashboard_metrics(),
        domain="telemetry",
        description="运营大盘三端指标检索别名",
    )

    # 8. User Profile & Entitlements
    scenario_router.register(
        "user.profile",
        lambda p, c: user_service.get_maker_profile(user_id=p.get("user_id", "usr_2026_opc_9981")),
        domain="user",
        description="获取创客个人主体档案与已激活权益",
    )
    scenario_router.register(
        "user.entitlements.activate",
        lambda p, c: user_service.activate_entitlement(EntitlementActivateRequest(**p)),
        domain="user",
        description="激活创客专属商业权益与特权门禁",
    )

    # 9. Moderation
    scenario_router.register(
        "moderation.items.list",
        lambda p, c: moderation_service.list_items(status=p.get("status")),
        domain="moderation",
        description="获取内容安全与敏感词审核队列",
    )
    scenario_router.register(
        "moderation.takedown",
        lambda p, c: moderation_service.takedown(TakedownRequest(**p)),
        domain="moderation",
        description="执行违规内容一键全网下架",
    )
    scenario_router.register(
        "moderation.restore",
        lambda p, c: moderation_service.restore(RestoreRequest(**p)),
        domain="moderation",
        description="恢复误判下架内容至正常展示",
    )

    # 10. Compliance
    scenario_router.register(
        "compliance.dimensions",
        lambda p, c: compliance_service.list_dimensions(),
        domain="compliance",
        description="获取六维合规防线核心法则与处罚依据",
    )
    scenario_router.register(
        "compliance.cases",
        lambda p, c: compliance_service.list_cases(dimension_id=p.get("dimension_id")),
        domain="compliance",
        description="获取典型踩坑与行政处罚案例库",
    )
    scenario_router.register(
        "compliance.checkpoints",
        lambda p, c: compliance_service.list_checkpoints(dimension_id=p.get("dimension_id")),
        domain="compliance",
        description="获取上线前自检清单与合规门禁条目",
    )
    scenario_router.register(
        "compliance.audit",
        lambda p, c: compliance_service.evaluate_audit(AuditEvaluateRequest(**p)),
        domain="compliance",
        description="评估创客产品自检并出具评分报告",
    )

    # 11. Orchestration & Scenarios
    scenario_router.register(
        "orchestration.operators.list",
        lambda p, c: orchestration_service.list_operators(),
        domain="orchestration",
        description="获取全域微内核原子算子清单与元数据",
    )
    scenario_router.register(
        "orchestration.dag.save",
        lambda p, c: _save_dag_config_adapter(p),
        domain="orchestration",
        description="保存并部署微内核 DAG 编排配置",
    )
    scenario_router.register(
        "orchestration.dag.list",
        lambda p, c: orchestration_service.list_dag_configs(scenario_code=p.get("scenario_code")),
        domain="orchestration",
        description="获取微内核 DAG 编排配置列表",
    )
    scenario_router.register(
        "orchestration.scenarios.execute",
        async_scenario_executor,
        domain="orchestration",
        description="执行低代码平台编排的有向无环图场景流水线",
    )
    scenario_router.register(
        "frontend.layouts.get",
        lambda p, c: orchestration_service.get_frontend_layout(layout_name=p.get("layout_name") or p.get("layout_id") or "main_console_layout"),
        domain="orchestration",
        description="获取 24 栅格低代码页面布局",
    )
    scenario_router.register(
        "frontend.layouts.save",
        lambda p, c: _save_layout_adapter(p),
        domain="orchestration",
        description="保存 24 栅格低代码前端可视化布局",
    )


def _save_dag_config_adapter(p: dict):
    topo = p.get("topology_graph") or p.get("config") or {}
    if "topology" not in topo and "topology" in p:
        topo["topology"] = p["topology"]
    return orchestration_service.save_dag_config(
        DAGConfigSaveRequest(
            scenario_code=p.get("scenario_code", "CUSTOM_SCENARIO"),
            version=p.get("version", "v1.0.0"),
            topology_graph=topo,
            status=p.get("status", "ACTIVE"),
            created_by=p.get("created_by", "usr_admin_001"),
        )
    )


def _save_layout_adapter(p: dict):
    return orchestration_service.save_frontend_layout(
        FrontendLayoutSaveRequest(
            layout_name=p.get("layout_name") or p.get("page_key", "main_console_layout"),
            version=p.get("version", "v1.0.4"),
            grid_schema=p.get("grid_schema", {"columns": 24, "type": "fluid_grid"}),
            widgets=p.get("widgets", []),
        )
    )


async def async_scenario_executor(payload: dict, context: dict):
    req = ScenarioExecuteRequest(**payload)
    return await orchestration_service.execute_scenario(req)

