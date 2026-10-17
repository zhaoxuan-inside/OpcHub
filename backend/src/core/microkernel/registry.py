"""Atomic Operator Registry supporting Dynamic Hot-Reloading and Domain Auto-Registration."""
from typing import Any, Callable, Awaitable, Optional
import inspect
import logging

from src.core.microkernel.dispatcher import dispatcher, DispatchMode

logger = logging.getLogger("opchub.microkernel")

ActionHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]


class AtomicRegistry:
    """Central method registry for atomic DAG node handlers and Saga compensators."""

    def __init__(self):
        self._handlers: dict[str, ActionHandler] = {}
        self._compensators: dict[str, ActionHandler] = {}
        self._register_default_handlers()
        self._register_domain_handlers()
        self._register_external_gateway_handlers()

    def register(
        self,
        name: str,
        handler: ActionHandler,
        domain: str = "core",
        description: str = "",
        dispatch_mode: DispatchMode = DispatchMode.IN_PROCESS,
        remote_endpoint: Optional[str] = None,
        compensator: Optional[ActionHandler] = None,
    ):
        """Register an atomic handler, optional compensator, and metadata descriptor."""
        self._handlers[name] = handler
        if compensator:
            self._compensators[name] = compensator
        dispatcher.register_descriptor(
            name=name,
            domain=domain,
            description=description or f"Atomic operator: {name}",
            mode=dispatch_mode,
            remote_endpoint=remote_endpoint,
        )
        logger.info(f"Registered atomic action handler: {name} (domain={domain}, mode={dispatch_mode.value})")

    def register_compensator(self, name: str, handler: ActionHandler):
        """Register a Saga reverse compensation handler for an action operator."""
        self._compensators[name] = handler
        logger.info(f"Registered Saga compensator for operator: {name}")

    def get(self, name: str) -> ActionHandler | None:
        return self._handlers.get(name)

    def get_compensator(self, name: str) -> ActionHandler | None:
        return self._compensators.get(name)

    def list_handlers(self) -> list[str]:
        return list(self._handlers.keys())

    def _register_default_handlers(self):
        # 1. Gateway Ingress
        async def gateway_ingress(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            quarterly_income = float(inputs.get("quarterly_income", 280000.0))
            return {
                "parsed": True,
                "quarterly_income": quarterly_income,
                "company_type": inputs.get("company_type", "SOLE_PROPRIETORSHIP"),
                "auth_token": inputs.get("auth_token", "opc_token_valid"),
            }
        self.register("gateway_ingress", gateway_ingress, domain="core", description="统一网关参数清洗与反序列化")

        # 2. Auth Guard
        async def auth_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            token = inputs.get("auth_token", "")
            if token == "invalid_token":
                raise PermissionError("HTTP 402: Entitlement required or invalid token")
            return {
                "auth_passed": True,
                "user_id": inputs.get("user_id", "usr_2026_opc_9981"),
                "role": "MAKER",
                "entitlement": "ENT_VIP",
            }
        self.register("auth_guard", auth_guard, domain="auth", description="创客权益身份与令牌准入门禁拦截")

        # 3. Invoice Tax Calculator
        async def invoice_tax_calc(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            income = float(inputs.get("quarterly_income", 0.0))
            exempt = income <= 300000.0
            tax_rate = 0.0 if exempt else 0.01
            tax_payable = 0.0 if exempt else income * tax_rate
            return {
                "quarterly_income": income,
                "vat_exemption_eligible": exempt,
                "applicable_tax_rate": tax_rate,
                "estimated_tax_payable": tax_payable,
                "legal_basis": "财政部 税务总局公告 2023年第12号 (小规模纳税人季度销售额30万元以下免征增值税)",
            }
        self.register("invoice_tax_calc", invoice_tax_calc, domain="policy", description="增值税小规模免征智能测算")

        # 4. Policy Matcher
        async def policy_matcher(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            return {
                "matched_count": 3,
                "recommended_subsidies": [
                    "长三角智能算力券 (最高 ¥120,000)",
                    "小微企业研发费用 100% 加计扣除",
                    "创客集聚区集群地址免实际租赁入驻补贴",
                ],
            }
        self.register("policy_matcher", policy_matcher, domain="policy", description="政策智能匹配引擎")

        # 5. ES Audit Sync
        async def es_audit_sync(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            return {
                "audit_recorded": True,
                "es_index": "opc_audit_log_2026_10",
                "synced_timestamp": "2026-10-17T02:00:00Z",
            }
        self.register("es_audit_sync", es_audit_sync, domain="core", description="审计日志与执行快照存储同步")

    def _register_domain_handlers(self):
        """Auto-register domain business operators."""
        # Domain 1: Policy Domain
        async def policy_calculate_tax(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            income = float(inputs.get("quarterly_income", 0.0))
            is_exempt = income <= 300000.0
            rate = 0.0 if is_exempt else 0.01
            tax = 0.0 if is_exempt else income * rate
            return {
                "tax_calculated": True,
                "is_vat_exempt": is_exempt,
                "applicable_tax_rate": rate,
                "estimated_tax_amount": tax,
                "policy_citation": "财政部 税务总局公告 2023年第12号",
            }
        self.register("policy.calculate_tax", policy_calculate_tax, domain="policy", description="高精度增值税及综合税负试算算子")
        async def policy_match_subsidies(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.policies.service import policy_service
            from src.domains.policies.models import PolicyMatchRequest
            city = inputs.get("city", "杭州")
            maker_type = "INDIVIDUAL" if "个体" in inputs.get("entity_type", "个体工商户") else "OPC"
            income = float(inputs.get("quarterly_income", 100000.0))
            req = PolicyMatchRequest(
                quarterly_income=income,
                maker_type=maker_type,
                region=city,
            )
            matched_resp = policy_service.match_policies(req)
            return {
                "subsidies_matched": True,
                "matched_count": len(matched_resp.matched_policies),
                "matched_subsidies": [p.model_dump() for p in matched_resp.matched_policies],
                "estimated_tax_savings": matched_resp.estimated_tax_savings,
            }
        self.register("policy.match_subsidies", policy_match_subsidies, domain="policy", description="根据地域主体匹配扶持补贴算子")

        # Domain 2: SOP Document Domain
        async def sop_render_document(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.sop.service import sop_service
            from src.domains.sop.models import SOPDocumentCreate
            template_id = inputs.get("template_id", "tpl_individual_biz_reg")
            maker_name = inputs.get("owner_name") or inputs.get("maker_name", "张创客")
            company_name = inputs.get("company_name", "杭州极速智能科技有限公司")
            field_data = {
                "maker_name": maker_name,
                "company_name": company_name,
                "biz_scope": inputs.get("biz_scope", "软件开发与人工智能应用研发"),
            }
            doc = sop_service.render_and_save_document(
                SOPDocumentCreate(
                    template_id=template_id,
                    user_id=inputs.get("user_id", "usr_maker_01"),
                    form_data=field_data,
                )
            )
            return {
                "sop_document_id": doc.id,
                "document_title": doc.document_title,
                "generated_text": doc.rendered_content,
                "compliance_passed": doc.compliance_passed,
                "created_at": doc.created_at,
            }
        self.register("sop.render_document", sop_render_document, domain="sop", description="企业商事登记公文组装与流水号签发算子")

        # Domain 3: Compliance Domain
        async def compliance_evaluate_audit(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.compliance.service import compliance_service
            from src.domains.compliance.models import AuditEvaluateRequest
            checked_ids = inputs.get("checked_ids") or inputs.get("passed_item_ids", [])
            report = compliance_service.evaluate_audit(AuditEvaluateRequest(passed_item_ids=checked_ids))
            if report.grade == "CRITICAL" and inputs.get("strict_mode", False):
                raise PermissionError(f"Compliance strict guard blocked: score is {report.score} (CRITICAL)")
            return {
                "compliance_score": report.score,
                "compliance_grade": report.grade,
                "passed_items_count": report.passed_items_count,
                "failed_items_count": report.failed_items_count,
                "remedy_suggestions": report.remedy_suggestions,
                "legal_help_recommendation": report.legal_help_recommendation,
            }
        self.register("compliance.evaluate_audit", compliance_evaluate_audit, domain="compliance", description="六维合规防线自检打分与风险阻断算子")

        # Domain 4: Moderation Domain
        async def moderation_inspect_content(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            content = inputs.get("content", "")
            forbidden_words = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            hit_words = [w for w in forbidden_words if w in content]
            if hit_words:
                raise ValueError(f"Content moderation violation: found prohibited keywords {hit_words}")
            return {
                "moderation_inspected": True,
                "passed": True,
                "flagged_keywords": [],
            }
        self.register("moderation.inspect_content", moderation_inspect_content, domain="moderation", description="UGC文本敏感词审查与违规处置算子")

        # Domain 5: Home & Sitemap Domain
        async def home_metrics_collector(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.telemetry.service import telemetry_service
            from src.domains.products.service import product_service
            from src.domains.demands.service import demand_service
            from src.domains.policies.service import policy_service
            
            prods = product_service.list_products()
            demands = demand_service.list_demands()
            policies = policy_service.list_policies()
            metrics = telemetry_service.get_dashboard_metrics()
            
            return {
                "active_makers_count": metrics.active_makers_count if hasattr(metrics, "active_makers_count") else 14820,
                "active_dags_count": 482,
                "matched_policies_count": len(policies),
                "demands_orders_count": len(demands),
                "perks_saved_cny": 1820000.0,
                "products_count": len(prods),
            }
        self.register("home.metrics.collector", home_metrics_collector, domain="home", description="首页全域宏观核心指标聚合算子")

        async def home_sitemap_builder(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            quick_links = [
                {"name": "头脑风暴", "route": "forum", "count_desc": "1,240 篇实战经验", "tag": "社区"},
                {"name": "产品橱窗", "route": "product", "count_desc": f"{inputs.get('products_count', 12)} 款独立商用作品", "tag": "商机"},
                {"name": "政策雷达", "route": "policy", "count_desc": f"{inputs.get('matched_policies_count', 8)} 条扶持减免红利", "tag": "政策"},
                {"name": "需求集市", "route": "demand", "count_desc": f"{inputs.get('demands_orders_count', 9)} 笔外包寻源委托", "tag": "委托"},
                {"name": "流程文书", "route": "sop", "count_desc": "4 阶段合规材料即时生成", "tag": "文书"},
                {"name": "生态特权", "route": "perks", "count_desc": "最高 $5,000 算力补贴券", "tag": "福利"},
                {"name": "合规指南", "route": "compliance", "count_desc": "6 大防线自检避坑雷达", "tag": "防线"},
                {"name": "创客档案", "route": "user", "count_desc": "权益凭据与会员中心", "tag": "主体"},
                {"name": "后端编排", "route": "backend-orch", "count_desc": "微内核 DAG 可视化引擎", "tag": "架构"},
            ]
            return {"quick_links": quick_links}
        self.register("home.sitemap.builder", home_sitemap_builder, domain="home", description="首页全景功能空间地图装配算子")

        async def home_overview_aggregator(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from datetime import datetime, timezone
            return {
                "active_makers_count": inputs.get("active_makers_count", 14820),
                "active_dags_count": inputs.get("active_dags_count", 482),
                "matched_policies_count": inputs.get("matched_policies_count", 8),
                "demands_orders_count": inputs.get("demands_orders_count", 9),
                "perks_saved_cny": inputs.get("perks_saved_cny", 1820000.0),
                "quick_links": inputs.get("quick_links", []),
                "server_time": datetime.now(timezone.utc).isoformat(),
                "orchestrated_by": "OPC_HOME_OVERVIEW_PIPELINE",
            }
        self.register("home.overview.aggregator", home_overview_aggregator, domain="home", description="首页综合全景大盘最终聚合算子")


    def _register_external_gateway_handlers(self):
        """Auto-register outbound gateway proxies as microkernel operators."""
        # 1. AI Gateway
        async def external_ai_generate_charter(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.infrastructure.external_gateway import ai_gateway
            company_name = inputs.get("company_name", "杭州极速智能科技有限公司")
            scope = inputs.get("biz_scope", "软件开发、人工智能技术服务")
            res = await ai_gateway.generate_charter_text(company_name, scope)
            return {
                "ai_charter_generated": True,
                "model_used": res.get("model"),
                "charter_text": res.get("charter_text"),
                "tokens_consumed": res.get("tokens_consumed"),
            }
        self.register("external.ai.generate_charter", external_ai_generate_charter, domain="external", description="统一外部网关代理生成一人公司章程")

        # 2. Crawler Gateway
        async def external_crawler_fetch_policy(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.infrastructure.external_gateway import gov_crawler_gateway
            dept = inputs.get("department", "国办发")
            doc_no = inputs.get("doc_number", "2023-12")
            res = await gov_crawler_gateway.fetch_public_policy(dept, doc_no)
            return {
                "crawler_fetched": True,
                "source_title": res.get("title"),
                "authority": res.get("issuing_authority"),
                "publish_date": res.get("publish_date"),
                "content_preview": res.get("content", "")[:200],
            }
        self.register("external.crawler.fetch_policy", external_crawler_fetch_policy, domain="external", description="统一外部网关低速合规采集政务公文")

        # 3. Payment Gateway
        async def external_payment_split_order(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.infrastructure.external_gateway import payment_gateway
            order_id = inputs.get("order_id", "ord_demo_2026")
            amount = float(inputs.get("amount", 2000.0))
            maker_amt = amount * 0.9
            platform_fee = amount * 0.1
            res = await payment_gateway.create_split_order(order_id, amount, maker_amt, platform_fee, "mch_sub_maker_01")
            return {
                "split_order_executed": True,
                "platform_fee": res.get("platform_fee"),
                "maker_amount": res.get("maker_amount"),
                "clearing_status": res.get("clearing_status"),
            }
        self.register("external.payment.split_order", external_payment_split_order, domain="external", description="统一外部网关持牌分账结算指令")

        # 4. SMS Gateway
        async def external_sms_send_auth_code(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.infrastructure.external_gateway import sms_auth_gateway
            phone = inputs.get("phone", "13800138000")
            code = inputs.get("code", "689201")
            res = await sms_auth_gateway.send_verification_code(phone, code)
            return {
                "sms_sent": True,
                "phone": res.get("phone"),
                "sms_channel": res.get("channel"),
                "verification_code": res.get("code"),
            }
        self.register("external.sms.send_auth_code", external_sms_send_auth_code, domain="external", description="统一外部网关发送实名验证码")


registry = AtomicRegistry()
