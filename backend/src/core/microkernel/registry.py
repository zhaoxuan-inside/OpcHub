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
        async def policy_qualify_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            income = float(inputs.get("quarterly_income", 0.0))
            if income < 0:
                raise ValueError("quarterly_income cannot be negative")
            region = inputs.get("region") or inputs.get("city", "杭州")
            maker_type = inputs.get("maker_type") or ("INDIVIDUAL" if "个体" in inputs.get("entity_type", "") else "OPC")
            return {
                "guard_passed": True,
                "quarterly_income": income,
                "region": region,
                "city": region,
                "maker_type": maker_type,
            }
        self.register("policy.qualify_guard", policy_qualify_guard, domain="policy", description="政策测算资质准入与参数归一化门禁")

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
            city = inputs.get("region") or inputs.get("city", "杭州")
            maker_type = "INDIVIDUAL" if "INDIVIDUAL" in inputs.get("maker_type", "INDIVIDUAL") or "个体" in inputs.get("entity_type", "") else "OPC"
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
                "matched_policies": [p.model_dump() for p in matched_resp.matched_policies],
                "estimated_tax_savings": matched_resp.estimated_tax_savings,
                "explanation": matched_resp.explanation,
                "eligible": matched_resp.eligible,
                "applicable_tax_rate": matched_resp.applicable_tax_rate,
                "legal_basis": matched_resp.legal_basis,
            }
        self.register("policy.match_subsidies", policy_match_subsidies, domain="policy", description="根据地域主体匹配扶持补贴算子")

        async def policy_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in policy pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "policy.match.executed",
                "matched_count": inputs.get("matched_count", 0),
                "increment": 1,
            }
        self.register("policy.telemetry.incr", policy_telemetry_incr, domain="policy", description="政策雷达智能测算与撮合检索度量打点算子")

        # Policy Publishing Operators
        async def policy_publish_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            title = inputs.get("title", "").strip()
            summary = inputs.get("summary", "").strip()
            legal_basis = inputs.get("legal_basis", "").strip()
            if len(title) < 2:
                raise ValueError("Policy title must be at least 2 characters long")
            if len(summary) < 5:
                raise ValueError("Policy summary must be at least 5 characters long")
            if not legal_basis:
                raise ValueError("legal_basis is required for government policy")
            
            # Moderation check
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            full_text = f"{title} {summary} {legal_basis}"
            for f in forbidden:
                if f in full_text:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in policy publish")
            
            return {
                "guard_passed": True,
                "title": title,
                "summary": summary,
                "legal_basis": legal_basis,
                "policy_level": inputs.get("policy_level", "国家级"),
                "category": inputs.get("category", "TAX"),
                "subsidy_amount_max": float(inputs.get("subsidy_amount_max", 0.0)),
                "eligible_conditions": inputs.get("eligible_conditions", []),
            }
        self.register("policy.publish.guard", policy_publish_guard, domain="policy", description="政策雷达政府红利发布准入与法律依据校验门禁")

        async def policy_publish_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.policies.service import policy_service
            from src.domains.policies.models import PolicyCreate
            payload = PolicyCreate(
                title=inputs.get("title", ""),
                policy_level=inputs.get("policy_level", "国家级"),
                category=inputs.get("category", "TAX"),
                subsidy_amount_max=float(inputs.get("subsidy_amount_max", 0.0)),
                summary=inputs.get("summary", ""),
                eligible_conditions=inputs.get("eligible_conditions", []),
                legal_basis=inputs.get("legal_basis", ""),
            )
            created = policy_service.create_policy(payload)
            return {
                "policy_id": created.id,
                "created_policy": created.model_dump(),
                "status": "PUBLISHED",
            }

        async def policy_publish_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.policies.service import policy_service
            policy_id = inputs.get("policy_id") or (inputs.get("created_policy", {}).get("id"))
            if policy_id:
                deleted = policy_service.delete_policy(policy_id)
                return {"policy_id": policy_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No policy_id to rollback"}

        self.register(
            "policy.publish.persist",
            policy_publish_persist,
            domain="policy",
            description="政策雷达政府扶持红利持久化存储算子",
            compensator=policy_publish_persist_compensate,
        )


        # Domain 2: SOP Document Domain (商事登记与合规文书生成微内核算子与 Saga 补偿)
        async def sop_document_validate_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.sop.service import sop_service
            template_id = inputs.get("template_id", "tpl_individual_biz_reg")
            if not template_id:
                raise ValueError("template_id is required for document rendering")
            try:
                template = sop_service.get_template(template_id)
            except KeyError:
                raise KeyError(f"SOP template with ID {template_id} not found")

            form_data = inputs.get("form_data") or {}
            if not isinstance(form_data, dict):
                form_data = {}

            # Content moderation check on form data
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            full_text = " ".join(str(v) for v in form_data.values())
            for f in forbidden:
                if f in full_text:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in SOP document form data")

            return {
                "guard_passed": True,
                "template_id": template_id,
                "template_name": template.name,
                "user_id": inputs.get("user_id", "usr_maker_2026"),
                "form_data": form_data,
            }
        self.register("sop.document.validate_guard", sop_document_validate_guard, domain="sop", description="合规文书模版准入与表单合规风控门禁")

        async def sop_document_render_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.sop.service import sop_service
            from src.domains.sop.models import SOPDocumentCreate
            template_id = inputs.get("template_id", "tpl_individual_biz_reg")
            user_id = inputs.get("user_id", "usr_maker_2026")
            form_data = inputs.get("form_data", {})
            doc = sop_service.render_and_save_document(
                SOPDocumentCreate(
                    template_id=template_id,
                    user_id=user_id,
                    form_data=form_data,
                )
            )
            return {
                "sop_document_id": doc.id,
                "doc_id": doc.id,
                "document_title": doc.document_title,
                "generated_text": doc.rendered_content,
                "rendered_content": doc.rendered_content,
                "compliance_passed": doc.compliance_passed,
                "status": "READY",
                "created_at": doc.created_at,
                "created_doc": doc.model_dump(),
            }

        async def sop_document_render_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.sop.service import sop_service
            doc_id = inputs.get("sop_document_id") or inputs.get("doc_id") or (inputs.get("created_doc", {}).get("id"))
            if doc_id:
                deleted = sop_service.delete_document(doc_id)
                return {"doc_id": doc_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No doc_id to rollback"}

        self.register(
            "sop.document.render_persist",
            sop_document_render_persist,
            domain="sop",
            description="合规文书根据表单插值渲染并持久化存储算子",
            compensator=sop_document_render_compensate,
        )
        # Register legacy handler alias
        self.register(
            "sop.render_document",
            sop_document_render_persist,
            domain="sop",
            description="企业商事登记公文组装与流水号签发算子",
            compensator=sop_document_render_compensate,
        )

        async def sop_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in SOP document pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "sop.document.generated",
                "doc_id": inputs.get("doc_id") or inputs.get("sop_document_id", "unknown"),
                "increment": 1,
            }
        self.register("sop.telemetry.incr", sop_telemetry_incr, domain="sop", description="合规文书生成与流水号防伪签发度量打点算子")


        # Domain 3: Compliance Domain (六维合规防线与上线自检雷达算子与 Saga 补偿)
        async def compliance_audit_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            checked = inputs.get("passed_item_ids") or inputs.get("checked_ids") or []
            if not isinstance(checked, list):
                raise ValueError("passed_item_ids must be a list of checkpoint IDs")
            return {
                "guard_passed": True,
                "passed_item_ids": checked,
                "checked_ids": checked,
                "strict_mode": bool(inputs.get("strict_mode", False)),
            }
        self.register("compliance.audit.guard", compliance_audit_guard, domain="compliance", description="合规自检参数归一化与前置校验门禁")

        async def compliance_evaluate_audit(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.compliance.service import compliance_service
            from src.domains.compliance.models import AuditEvaluateRequest
            checked_ids = inputs.get("checked_ids") or inputs.get("passed_item_ids", [])
            report = compliance_service.evaluate_audit(AuditEvaluateRequest(passed_item_ids=checked_ids))
            if report.grade == "CRITICAL" and inputs.get("strict_mode", False):
                raise PermissionError(f"Compliance strict guard blocked: score is {report.score} (CRITICAL)")
            return {
                "score": report.score,
                "grade": report.grade,
                "compliance_score": report.score,
                "compliance_grade": report.grade,
                "total_items": report.total_items,
                "passed_items_count": report.passed_items_count,
                "failed_items_count": report.failed_items_count,
                "risk_items": [item.model_dump() for item in report.risk_items],
                "remedy_suggestions": report.remedy_suggestions,
                "legal_help_recommendation": report.legal_help_recommendation,
                "audit_report": report.model_dump(),
            }

        async def compliance_audit_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            return {
                "compensated": True,
                "action": "ROLLED_BACK",
                "details": "Transient compliance audit session and recommendations cleared",
            }

        self.register(
            "compliance.evaluate_audit",
            compliance_evaluate_audit,
            domain="compliance",
            description="六维合规防线自检打分与风险阻断算子",
            compensator=compliance_audit_compensate,
        )

        async def compliance_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in compliance pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "compliance.audit.evaluated",
                "score": inputs.get("score") or inputs.get("compliance_score", 0),
                "increment": 1,
            }
        self.register("compliance.telemetry.incr", compliance_telemetry_incr, domain="compliance", description="合规自检评估与雷达度量打点算子")


        # Domain 4: Moderation Domain (内容安全审查、全网下架与误判恢复微内核算子与 Saga 补偿)
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

        async def moderation_takedown_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.moderation.service import moderation_service
            item_id = inputs.get("item_id", "").strip()
            reason = inputs.get("reason") or inputs.get("takedown_reason", "").strip()
            moderator_id = inputs.get("moderator_id") or inputs.get("operator_id", "admin_001")
            ban_author = bool(inputs.get("ban_author", False))

            if not item_id:
                raise ValueError("item_id is required for takedown")
            if not reason:
                raise ValueError("takedown reason is required and cannot be empty")

            item = moderation_service.get_item(item_id)
            if not item:
                raise ValueError(f"Moderation item {item_id} not found")

            return {
                "guard_passed": True,
                "item_id": item_id,
                "reason": reason,
                "moderator_id": moderator_id,
                "ban_author": ban_author,
                "prev_status": item.status,
            }
        self.register("moderation.takedown.guard", moderation_takedown_guard, domain="moderation", description="内容治理违规下架前置守卫校验算子")

        async def moderation_takedown_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.moderation.service import moderation_service
            from src.domains.moderation.models import TakedownRequest

            item_id = inputs.get("item_id")
            reason = inputs.get("reason", "违规言论全网下架")
            moderator_id = inputs.get("moderator_id", "admin_001")
            ban_author = inputs.get("ban_author", False)
            prev_status = inputs.get("prev_status", "FLAGGED")

            req = TakedownRequest(
                item_id=item_id,
                reason=reason,
                moderator_id=moderator_id,
                ban_author=ban_author,
            )
            action_res = moderation_service.takedown(req)
            return {
                "item_id": action_res.item_id,
                "status": action_res.status,
                "moderated_at": action_res.moderated_at,
                "note": action_res.note,
                "prev_status": prev_status,
                "orchestrated_by": "OPC_MODERATION_TAKEDOWN_PIPELINE",
            }

        async def moderation_takedown_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.moderation.service import moderation_service
            item_id = inputs.get("item_id")
            prev_status = inputs.get("prev_status", "FLAGGED")
            if item_id:
                reverted = moderation_service.revert_takedown(item_id, prev_status)
                return {"item_id": item_id, "compensated": reverted, "action": "ROLLED_BACK", "restored_status": prev_status}
            return {"compensated": False, "reason": "No item_id to rollback takedown"}

        self.register(
            "moderation.takedown.persist",
            moderation_takedown_persist,
            domain="moderation",
            description="内容治理违规言论下架持久化算子",
            compensator=moderation_takedown_persist_compensate,
        )

        async def moderation_restore_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.moderation.service import moderation_service
            item_id = inputs.get("item_id", "").strip()
            moderator_id = inputs.get("moderator_id") or inputs.get("operator_id", "admin_001")

            if not item_id:
                raise ValueError("item_id is required for restore")

            item = moderation_service.get_item(item_id)
            if not item:
                raise ValueError(f"Moderation item {item_id} not found")
            if item.status != "TAKEN_DOWN":
                raise ValueError(f"Item {item_id} is currently in status '{item.status}', only TAKEN_DOWN items can be restored")

            return {
                "guard_passed": True,
                "item_id": item_id,
                "moderator_id": moderator_id,
            }
        self.register("moderation.restore.guard", moderation_restore_guard, domain="moderation", description="内容治理误判恢复前置守卫校验算子")

        async def moderation_restore_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.moderation.service import moderation_service
            from src.domains.moderation.models import RestoreRequest

            item_id = inputs.get("item_id")
            moderator_id = inputs.get("moderator_id", "admin_001")

            req = RestoreRequest(item_id=item_id, moderator_id=moderator_id)
            action_res = moderation_service.restore(req)
            return {
                "item_id": action_res.item_id,
                "status": action_res.status,
                "moderated_at": action_res.moderated_at,
                "note": action_res.note,
                "orchestrated_by": "OPC_MODERATION_RESTORE_PIPELINE",
            }

        async def moderation_restore_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.moderation.service import moderation_service
            item_id = inputs.get("item_id")
            if item_id:
                reverted = moderation_service.revert_restore(item_id)
                return {"item_id": item_id, "compensated": reverted, "action": "ROLLED_BACK", "restored_status": "TAKEN_DOWN"}
            return {"compensated": False, "reason": "No item_id to rollback restore"}

        self.register(
            "moderation.restore.persist",
            moderation_restore_persist,
            domain="moderation",
            description="内容治理误判下架言论恢复正常展示持久化算子",
            compensator=moderation_restore_persist_compensate,
        )

        async def moderation_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure to trigger Saga rollback")
            item_id = inputs.get("item_id", "unknown")
            action_status = inputs.get("status", "MODERATED")
            return {
                "telemetry_recorded": True,
                "metric": "governance.moderation.actions",
                "item_id": item_id,
                "status": action_status,
                "increment": 1,
            }
        self.register("moderation.telemetry.incr", moderation_telemetry_incr, domain="moderation", description="内容治理处置度量打点算子")

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

        # Domain 6: Forum Domain (头脑风暴社区微内核算子与 Saga 补偿)
        async def forum_thread_validate_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            title = inputs.get("title", "").strip()
            content = inputs.get("content", "").strip()
            category = inputs.get("category_code", "GENERAL")
            if len(title) < 5:
                raise ValueError("Forum thread title must be at least 5 characters long")
            if len(content) < 10:
                raise ValueError("Forum thread content must be at least 10 characters long")
            
            # Content moderation check
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            for f in forbidden:
                if f in title or f in content:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in forum thread")
            
            return {
                "guard_passed": True,
                "title": title,
                "content": content,
                "category_code": category,
                "author_id": inputs.get("author_id", "usr_maker_nomad"),
            }
        self.register("forum.thread.validate_guard", forum_thread_validate_guard, domain="forum", description="头脑风暴发帖准入校验与敏感词审查门禁")

        async def forum_thread_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            from src.domains.forum.models import ForumThreadCreate
            payload = ForumThreadCreate(
                category_code=inputs.get("category_code", "GENERAL"),
                author_id=inputs.get("author_id", "usr_maker_nomad"),
                title=inputs.get("title", ""),
                content=inputs.get("content", ""),
            )
            created = forum_service.create_thread(payload)
            return {
                "thread_id": created.id,
                "created_thread": created.model_dump(),
                "status": "PUBLISHED",
            }

        async def forum_thread_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            thread_id = inputs.get("thread_id") or (inputs.get("created_thread", {}).get("id"))
            if thread_id:
                deleted = forum_service.delete_thread(thread_id)
                return {"thread_id": thread_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No thread_id to rollback"}

        self.register(
            "forum.thread.persist",
            forum_thread_persist,
            domain="forum",
            description="头脑风暴社区讨论帖持久化存储算子",
            compensator=forum_thread_persist_compensate,
        )

        async def forum_comment_validate_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            thread_id = inputs.get("thread_id", "")
            content = inputs.get("content", "").strip()
            parent_id = inputs.get("parent_id")
            if not thread_id:
                raise ValueError("thread_id is required for forum comment")
            if not content:
                raise ValueError("Forum comment content cannot be empty")
            if thread_id not in forum_service._threads:
                raise KeyError(f"Forum thread with ID {thread_id} not found")
            if parent_id and parent_id not in forum_service._comments:
                raise KeyError(f"Parent comment with ID {parent_id} not found")
            
            # Content moderation check
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            for f in forbidden:
                if f in content:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in forum comment")
            
            return {
                "guard_passed": True,
                "thread_id": thread_id,
                "content": content,
                "parent_id": parent_id,
                "author_id": inputs.get("author_id", "usr_maker_solodev"),
                "reply_to_user_id": inputs.get("reply_to_user_id"),
            }
        self.register("forum.comment.validate_guard", forum_comment_validate_guard, domain="forum", description="头脑风暴评论准入校验与物化层级校验门禁")

        async def forum_comment_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            from src.domains.forum.models import ForumCommentCreate
            thread_id = inputs.get("thread_id", "")
            payload = ForumCommentCreate(
                author_id=inputs.get("author_id", "usr_maker_solodev"),
                content=inputs.get("content", ""),
                parent_id=inputs.get("parent_id"),
                reply_to_user_id=inputs.get("reply_to_user_id"),
            )
            created = forum_service.create_comment(thread_id, payload)
            return {
                "comment_id": created.id,
                "thread_id": thread_id,
                "materialized_path": created.materialized_path,
                "depth": created.depth,
                "created_comment": created.model_dump(),
                "status": "ACTIVE",
            }

        async def forum_comment_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            comment_id = inputs.get("comment_id") or (inputs.get("created_comment", {}).get("id"))
            if comment_id:
                deleted = forum_service.delete_comment(comment_id)
                return {"comment_id": comment_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No comment_id to rollback"}

        self.register(
            "forum.comment.persist",
            forum_comment_persist,
            domain="forum",
            description="头脑风暴物化路径评论持久化存储算子",
            compensator=forum_comment_persist_compensate,
        )

        async def forum_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            # Trigger downstream failure for Saga rollback verification if requested
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure to trigger Saga rollback")
            target_id = inputs.get("thread_id") or inputs.get("comment_id", "unknown")
            return {
                "telemetry_recorded": True,
                "metric": "community.interaction.count",
                "target_id": target_id,
                "increment": 1,
            }
        self.register("forum.telemetry.incr", forum_telemetry_incr, domain="forum", description="头脑风暴社区互动度量指标递增算子")

        # Domain 7: Product Showcase Domain (产品橱窗微内核算子与 Saga 补偿)
        async def product_validate_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            title = inputs.get("title", "").strip()
            tagline = inputs.get("tagline", "").strip()
            desc = inputs.get("description", "").strip()
            price = float(inputs.get("price_cny", 0.0))
            if len(title) < 2:
                raise ValueError("Product title must be at least 2 characters long")
            if len(tagline) < 5 and len(desc) < 5:
                raise ValueError("Product tagline or description must be at least 5 characters long")
            if price < 0:
                raise ValueError("Product price cannot be negative")
            
            # Content moderation check
            full_text = f"{title} {tagline} {desc}"
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            for f in forbidden:
                if f in full_text:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in product showcase")
            
            return {
                "guard_passed": True,
                "title": title,
                "tagline": tagline,
                "description": desc or tagline,
                "category": inputs.get("category", "DEV"),
                "pricing_model": inputs.get("pricing_model", "FREE" if price == 0 else "ONE_TIME"),
                "price_cny": price,
                "demo_url": inputs.get("demo_url", "https://opchub.dev"),
                "author_id": inputs.get("author_id", "usr_maker_2026"),
            }
        self.register("product.validate_guard", product_validate_guard, domain="product", description="产品橱窗作品发布准入校验与合规审查门禁")

        async def product_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.products.service import product_service
            from src.domains.products.models import ProductCreate
            payload = ProductCreate(
                author_id=inputs.get("author_id", "usr_maker_2026"),
                title=inputs.get("title", ""),
                tagline=inputs.get("tagline", ""),
                description=inputs.get("description", "") or inputs.get("tagline", ""),
                category=inputs.get("category", "DEV"),
                pricing_model=inputs.get("pricing_model", "FREE"),
                price_cny=float(inputs.get("price_cny", 0.0)),
                demo_url=inputs.get("demo_url", "https://opchub.dev"),
            )
            created = product_service.create_product(payload)
            return {
                "product_id": created.id,
                "created_product": created.model_dump(),
                "status": "PUBLISHED",
            }

        async def product_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.products.service import product_service
            product_id = inputs.get("product_id") or (inputs.get("created_product", {}).get("id"))
            if product_id:
                deleted = product_service.delete_product(product_id)
                return {"product_id": product_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No product_id to rollback"}

        self.register(
            "product.persist",
            product_persist,
            domain="product",
            description="产品橱窗独立商用作品持久化存储算子",
            compensator=product_persist_compensate,
        )

        async def product_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            # Trigger downstream failure for Saga rollback verification if requested
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure to trigger Saga rollback")
            product_id = inputs.get("product_id", "unknown")
            return {
                "telemetry_recorded": True,
                "metric": "showcase.product.published",
                "product_id": product_id,
                "increment": 1,
            }
        self.register("product.telemetry.incr", product_telemetry_incr, domain="product", description="产品橱窗作品收录与度量打点算子")

        # Domain 8: Demands & Bidding Market Domain (需求集市与创客竞标微内核算子与 Saga 补偿)
        async def demand_publish_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            title = inputs.get("title", "").strip()
            desc = inputs.get("description", "").strip()
            budget = float(inputs.get("budget_cny", 0.0))
            category = inputs.get("category", "DEV").upper()
            deadline_days = int(inputs.get("deadline_days", 14))
            creator_id = inputs.get("creator_id", "usr_client_corp_default")

            if len(title) < 2:
                raise ValueError("Demand title must be at least 2 characters long")
            if len(desc) < 5:
                raise ValueError("Demand description must be at least 5 characters long")
            if budget < 0:
                raise ValueError("Demand budget cannot be negative")
            valid_cats = {"DEV", "AI", "TAX", "LEGAL", "BIZ"}
            if category not in valid_cats:
                category = "DEV"
            if deadline_days < 1:
                deadline_days = 14

            # Moderation check
            full_text = f"{title} {desc}"
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            for f in forbidden:
                if f in full_text:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in demand publish")

            return {
                "guard_passed": True,
                "title": title,
                "description": desc,
                "budget_cny": budget,
                "category": category,
                "deadline_days": deadline_days,
                "creator_id": creator_id,
            }
        self.register("demand.publish.guard", demand_publish_guard, domain="demands", description="需求集市外包寻源委托发布准入校验与合规审查门禁")

        async def demand_publish_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            from src.domains.demands.models import DemandCreate
            payload = DemandCreate(
                title=inputs.get("title", ""),
                description=inputs.get("description", ""),
                budget_cny=float(inputs.get("budget_cny", 0.0)),
                category=inputs.get("category", "DEV"),
                deadline_days=int(inputs.get("deadline_days", 14)),
                creator_id=inputs.get("creator_id", "usr_client_corp_default"),
            )
            created = demand_service.create_demand(payload)
            return {
                "demand_id": created.id,
                "created_demand": created.model_dump(),
                "status": "OPEN",
            }

        async def demand_publish_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            demand_id = inputs.get("demand_id") or (inputs.get("created_demand", {}).get("id"))
            if demand_id:
                deleted = demand_service.delete_demand(demand_id)
                return {"demand_id": demand_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No demand_id to rollback"}

        self.register(
            "demand.publish.persist",
            demand_publish_persist,
            domain="demands",
            description="需求集市企业委托寻源需求持久化存储算子",
            compensator=demand_publish_persist_compensate,
        )

        async def demand_bid_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            demand_id = inputs.get("demand_id", "").strip()
            bidder_id = inputs.get("bidder_id", "usr_maker_2026").strip()
            amount = float(inputs.get("bid_amount_cny", 0.0))
            delivery_days = int(inputs.get("delivery_days", 7))
            proposal = inputs.get("proposal_text", "").strip()

            if not demand_id:
                raise ValueError("demand_id is required for bidding")
            demand = demand_service.get_demand(demand_id)
            if not demand:
                raise KeyError(f"Demand with ID {demand_id} not found")
            if demand.status != "OPEN":
                raise ValueError(f"Demand {demand_id} is not open for bidding (status: {demand.status})")
            if amount < 0:
                raise ValueError("bid_amount_cny cannot be negative")
            if delivery_days < 1:
                raise ValueError("delivery_days must be at least 1")
            if len(proposal) < 5:
                raise ValueError("proposal_text must be at least 5 characters long")

            # Moderation check
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            for f in forbidden:
                if f in proposal:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in demand bid proposal")

            return {
                "guard_passed": True,
                "demand_id": demand_id,
                "bidder_id": bidder_id,
                "bid_amount_cny": amount,
                "delivery_days": delivery_days,
                "proposal_text": proposal,
            }
        self.register("demand.bid.guard", demand_bid_guard, domain="demands", description="需求集市创客竞标方案准入审查门禁")

        async def demand_bid_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            from src.domains.demands.models import BidCreate
            demand_id = inputs.get("demand_id")
            payload = BidCreate(
                bidder_id=inputs.get("bidder_id", "usr_maker_2026"),
                bid_amount_cny=float(inputs.get("bid_amount_cny", 0.0)),
                delivery_days=int(inputs.get("delivery_days", 7)),
                proposal_text=inputs.get("proposal_text", ""),
            )
            created = demand_service.submit_bid(demand_id, payload)
            return {
                "bid_id": created.id,
                "demand_id": demand_id,
                "created_bid": created.model_dump(),
                "status": "SUBMITTED",
            }

        async def demand_bid_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            demand_id = inputs.get("demand_id")
            bid_id = inputs.get("bid_id") or (inputs.get("created_bid", {}).get("id"))
            if demand_id and bid_id:
                deleted = demand_service.delete_bid(demand_id, bid_id)
                return {"demand_id": demand_id, "bid_id": bid_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "Missing demand_id or bid_id to rollback"}

        self.register(
            "demand.bid.persist",
            demand_bid_persist,
            domain="demands",
            description="需求集市创客竞标方案持久化与指标自增算子",
            compensator=demand_bid_persist_compensate,
        )

        async def demand_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in demands pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "demands.pipeline.executed",
                "demand_id": inputs.get("demand_id", "unknown"),
                "increment": 1,
            }
        self.register("demand.telemetry.incr", demand_telemetry_incr, domain="demands", description="需求集市寻源与竞标度量打点算子")

        # Domain 9: Perks & Infrastructure Domain (生态特权与福利领用微内核算子与 Saga 补偿)
        async def perk_claim_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.perks.service import perk_service
            perk_id = inputs.get("perk_id", "").strip()
            user_id = inputs.get("user_id", "usr_maker_2026").strip()

            if not perk_id:
                raise ValueError("perk_id is required for claiming perk")
            perk = perk_service.get_perk(perk_id)
            if not perk:
                raise KeyError(f"Perk with ID {perk_id} not found")
            if perk.quota_remaining <= 0:
                raise ValueError(f"Perk {perk.name} is fully redeemed")

            return {
                "guard_passed": True,
                "perk_id": perk_id,
                "perk_name": perk.name,
                "provider": perk.provider,
                "user_id": user_id,
            }
        self.register("perk.claim.guard", perk_claim_guard, domain="perks", description="生态特权领用准入与剩余配额校验门禁")

        async def perk_claim_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.perks.service import perk_service
            from src.domains.perks.models import PerkClaimRequest
            perk_id = inputs.get("perk_id")
            user_id = inputs.get("user_id", "usr_maker_2026")
            claim = perk_service.claim_perk(PerkClaimRequest(user_id=user_id, perk_id=perk_id))
            return {
                "claim_id": claim.claim_id,
                "perk_id": perk_id,
                "user_id": user_id,
                "voucher_code": claim.voucher_code,
                "created_claim": claim.model_dump(),
                "status": "ACTIVATED",
            }

        async def perk_claim_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.perks.service import perk_service
            perk_id = inputs.get("perk_id") or (inputs.get("created_claim", {}).get("perk_id"))
            user_id = inputs.get("user_id") or (inputs.get("created_claim", {}).get("user_id"))
            if perk_id and user_id:
                revoked = perk_service.revoke_claim(user_id, perk_id)
                return {"perk_id": perk_id, "user_id": user_id, "compensated": revoked, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "Missing perk_id or user_id to rollback"}

        self.register(
            "perk.claim.persist",
            perk_claim_persist,
            domain="perks",
            description="生态特权抵扣凭据签发与配额原子扣减算子",
            compensator=perk_claim_persist_compensate,
        )

        async def perk_publish_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            name = inputs.get("name", "").strip()
            provider = inputs.get("provider", "").strip()
            val = float(inputs.get("value_cny", 0.0))
            summary = inputs.get("summary", "").strip()

            if len(name) < 2:
                raise ValueError("Perk name must be at least 2 characters long")
            if len(provider) < 2:
                raise ValueError("Perk provider must be at least 2 characters long")
            if val < 0:
                raise ValueError("Perk value_cny cannot be negative")
            if len(summary) < 5:
                raise ValueError("Perk summary must be at least 5 characters long")

            # Moderation check
            forbidden = ["代开假发票", "内嵌自设资金池", "洗钱", "非法集资"]
            full_text = f"{name} {provider} {summary}"
            for f in forbidden:
                if f in full_text:
                    raise ValueError(f"Content moderation violation: found prohibited keyword '{f}' in perk publish")

            return {
                "guard_passed": True,
                "name": name,
                "provider": provider,
                "value_cny": val,
                "category": inputs.get("category", "CLOUD"),
                "summary": summary,
                "quota_remaining": int(inputs.get("quota_remaining", 100)),
            }
        self.register("perk.publish.guard", perk_publish_guard, domain="perks", description="生态特权提报上线准入与风控审查门禁")

        async def perk_publish_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.perks.service import perk_service
            from src.domains.perks.models import PerkCreate
            payload = PerkCreate(
                name=inputs.get("name", ""),
                provider=inputs.get("provider", ""),
                value_cny=float(inputs.get("value_cny", 0.0)),
                category=inputs.get("category", "CLOUD"),
                summary=inputs.get("summary", ""),
                quota_remaining=int(inputs.get("quota_remaining", 100)),
            )
            created = perk_service.create_perk(payload)
            return {
                "perk_id": created.id,
                "created_perk": created.model_dump(),
                "status": "ONLINE",
            }

        async def perk_publish_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.perks.service import perk_service
            perk_id = inputs.get("perk_id") or (inputs.get("created_perk", {}).get("id"))
            if perk_id:
                deleted = perk_service.delete_perk(perk_id)
                return {"perk_id": perk_id, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No perk_id to rollback"}

        self.register(
            "perk.publish.persist",
            perk_publish_persist,
            domain="perks",
            description="生态特权新权益持久化收录算子",
            compensator=perk_publish_persist_compensate,
        )

        async def perk_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in perks pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "perks.pipeline.executed",
                "perk_id": inputs.get("perk_id", "unknown"),
                "increment": 1,
            }
        self.register("perk.telemetry.incr", perk_telemetry_incr, domain="perks", description="生态特权领用与发布度量打点算子")






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

        # Domain 10: Ops & Telemetry Domain (全域运营大盘实时核心指标聚合与审计流水线算子)
        async def telemetry_dashboard_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            time_range = inputs.get("time_range", "7D")
            terminal_filter = inputs.get("terminal_filter", "ALL")
            operator_id = inputs.get("operator_id") or inputs.get("user_id", "admin_001")

            valid_ranges = ["1D", "7D", "30D", "1Y", "ALL"]
            if time_range not in valid_ranges:
                raise ValueError(f"Invalid time_range '{time_range}', must be one of {valid_ranges}")

            return {
                "guard_passed": True,
                "time_range": time_range,
                "terminal_filter": terminal_filter,
                "operator_id": operator_id,
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("telemetry.dashboard.guard", telemetry_dashboard_guard, domain="telemetry", description="运营监控大盘调阅鉴权与参数守卫算子")

        async def telemetry_dashboard_collect(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.telemetry.service import telemetry_service
            dashboard_obj = telemetry_service.get_dashboard_metrics()
            dashboard_dict = dashboard_obj.model_dump()
            dashboard_dict["orchestrated_by"] = "OPC_OPS_DASHBOARD_PIPELINE"
            dashboard_dict["time_range"] = inputs.get("time_range", "7D")
            dashboard_dict["terminal_filter"] = inputs.get("terminal_filter", "ALL")
            return {
                "dashboard": dashboard_dict,
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("telemetry.dashboard.collect", telemetry_dashboard_collect, domain="telemetry", description="全域三端运营指标与核心KPI原子聚合算子")

        # In-memory audit tracking for Saga compensation
        _ops_audit_log = {}

        async def telemetry_dashboard_audit(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            import uuid
            from datetime import datetime, timezone
            audit_id = f"aud_ops_{uuid.uuid4().hex[:8]}"
            dashboard = inputs.get("dashboard", {})
            operator_id = inputs.get("operator_id", "admin_001")
            record = {
                "audit_id": audit_id,
                "operator_id": operator_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "RECORDED",
                "watermark": "SECURE_ADMIN_HASH_2026",
            }
            _ops_audit_log[audit_id] = record
            # Flatten dashboard data to top-level output for transparent gateway consumption
            result = dict(dashboard)
            result["audit_id"] = audit_id
            result["audit_status"] = "RECORDED"
            result["simulate_downstream_failure"] = inputs.get("simulate_downstream_failure", False)
            return result

        async def telemetry_dashboard_audit_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            audit_id = inputs.get("audit_id")
            if audit_id and audit_id in _ops_audit_log:
                _ops_audit_log[audit_id]["status"] = "ROLLED_BACK"
                return {"audit_id": audit_id, "compensated": True, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No audit record to rollback"}

        self.register(
            "telemetry.dashboard.audit",
            telemetry_dashboard_audit,
            domain="telemetry",
            description="运营大盘调阅脱敏水印签发与安全审计持久化算子",
            compensator=telemetry_dashboard_audit_compensate,
        )

        async def telemetry_dashboard_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in Ops Dashboard pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "ops.dashboard.viewed",
                "increment": 1,
            }
        self.register("telemetry.dashboard.telemetry.incr", telemetry_dashboard_telemetry_incr, domain="telemetry", description="运营大盘调阅度量指标自增算子")


registry = AtomicRegistry()
