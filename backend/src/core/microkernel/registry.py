"""Atomic Operator Registry supporting Dynamic Hot-Reloading and Domain Auto-Registration."""
from typing import Any, Callable, Awaitable, Optional
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

    def unregister(self, name: str) -> bool:
        """Remove a dynamically registered handler, its compensator and descriptor."""
        existed = name in self._handlers
        self._handlers.pop(name, None)
        self._compensators.pop(name, None)
        dispatcher.unregister_descriptor(name)
        if existed:
            logger.info(f"Unregistered atomic action handler: {name}")
        return existed

    def get(self, name: str) -> ActionHandler | None:
        return self._handlers.get(name)

    def get_compensator(self, name: str) -> ActionHandler | None:
        return self._compensators.get(name)

    def list_handlers(self) -> list[str]:
        return list(self._handlers.keys())

    def _register_default_handlers(self):
        # 1. Gateway Ingress
        async def gateway_ingress(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            quarterly_income = float(inputs.get("quarterly_income", 0.0))
            return {
                "parsed": True,
                "quarterly_income": quarterly_income,
                "company_type": inputs.get("company_type", "SOLE_PROPRIETORSHIP"),
                "auth_token": inputs.get("auth_token", ""),
            }
        self.register("gateway_ingress", gateway_ingress, domain="core", description="统一网关参数清洗与反序列化")

        # 2. Auth Guard
        async def auth_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            token = inputs.get("auth_token", "")
            if token == "invalid_token":
                raise PermissionError("HTTP 402: Entitlement required or invalid token")
            user_id = inputs.get("user_id", "")
            if not user_id and token:
                from src.core.security import verify_session_token
                p = verify_session_token(token)
                if p and p.get("uid"):
                    user_id = p.get("uid")
            return {
                "auth_passed": True,
                "user_id": user_id,
                "role": "MAKER" if user_id else "GUEST",
                "entitlement": "",
            }
        self.register("auth_guard", auth_guard, domain="auth", description="创客权益身份与令牌准入门禁拦截")

        # 3. Invoice Tax Calculator
        async def invoice_tax_calc(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.core.config import settings
            income = float(inputs.get("quarterly_income", 0.0))
            exempt = income <= settings.vat_exemption_quarterly_threshold
            tax_rate = 0.0 if exempt else settings.vat_concessional_rate
            tax_payable = 0.0 if exempt else income * tax_rate
            return {
                "quarterly_income": income,
                "vat_exemption_eligible": exempt,
                "applicable_tax_rate": tax_rate,
                "estimated_tax_payable": tax_payable,
                "legal_basis": settings.vat_legal_basis,
            }
        self.register("invoice_tax_calc", invoice_tax_calc, domain="policy", description="增值税小规模免征智能测算")

        # 4. Policy Matcher
        async def policy_matcher(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.policies.service import policy_service
            from src.domains.policies.models import PolicyMatchRequest
            region = inputs.get("region") or inputs.get("city", "杭州")
            maker_type = inputs.get("maker_type", "INDIVIDUAL")
            income = float(inputs.get("quarterly_income", 0.0))
            req = PolicyMatchRequest(
                quarterly_income=income,
                maker_type=maker_type,
                region=region,
            )
            resp = policy_service.match_policies(req)
            return {
                "matched_count": len(resp.matched_policies),
                "matched_policies": [p.model_dump() for p in resp.matched_policies],
                "recommended_subsidies": [p.title for p in resp.matched_policies],
                "eligible": resp.eligible,
                "estimated_tax_savings": resp.estimated_tax_savings,
            }
        self.register("policy_matcher", policy_matcher, domain="policy", description="政策智能匹配引擎")

        # 5. ES Audit Sync
        async def es_audit_sync(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from datetime import datetime, timezone
            return {
                "audit_recorded": True,
                "es_index": f"opc_audit_log_{datetime.now(timezone.utc).strftime('%Y_%m')}",
                "synced_timestamp": datetime.now(timezone.utc).isoformat(),
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
            from src.core.config import settings
            income = float(inputs.get("quarterly_income", 0.0))
            is_exempt = income <= settings.vat_exemption_quarterly_threshold
            rate = 0.0 if is_exempt else settings.vat_concessional_rate
            tax = 0.0 if is_exempt else income * rate
            return {
                "tax_calculated": True,
                "is_vat_exempt": is_exempt,
                "applicable_tax_rate": rate,
                "estimated_tax_amount": tax,
                "policy_citation": settings.vat_legal_basis,
            }
        self.register("policy.calculate_tax", policy_calculate_tax, domain="policy", description="高精度增值税及综合税负试算算子")

        async def match_subsidies_by_region(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：按创客主体与城市匹配政策扶持补贴"""
            from src.domains.policies.service import policy_service
            from src.domains.policies.models import PolicyMatchRequest
            m_type = "INDIVIDUAL" if "INDIVIDUAL" in inputs.get("maker_type", "INDIVIDUAL") or "个体" in inputs.get("entity_type", "") else "OPC"
            req = PolicyMatchRequest(
                quarterly_income=float(inputs.get("quarterly_income", 100000.0)),
                maker_type=m_type,
                region=inputs.get("region") or inputs.get("city", "杭州"),
            )
            resp = policy_service.match_policies(req)
            policies = [p.model_dump() for p in resp.matched_policies]
            return {
                "subsidies_matched": True, "matched_count": len(policies),
                "matched_subsidies": policies, "matched_policies": policies,
                "estimated_tax_savings": resp.estimated_tax_savings, "explanation": resp.explanation,
                "eligible": resp.eligible, "applicable_tax_rate": resp.applicable_tax_rate, "legal_basis": resp.legal_basis,
            }
        self.register("policy.match_subsidies", match_subsidies_by_region, domain="policy", description="根据地域主体匹配扶持补贴算子")
        self.register("match_subsidies_by_region", match_subsidies_by_region, domain="policy", description="根据地域主体匹配扶持补贴算子")

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
        async def validate_publish_policy(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验发布政策合法性并做公文文本合规审查"""
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            t, s, l = inputs.get("title", "").strip(), inputs.get("summary", "").strip(), inputs.get("legal_basis", "").strip()
            if len(t) < 2:
                raise ValueError("Policy title must be at least 2 characters long")
            if len(s) < 5:
                raise ValueError("Policy summary must be at least 5 characters long")
            if not l:
                raise ValueError("legal_basis is required for government policy")
            await check_content_safety(f"{t} {s} {l}", field_name="policy publish")
            return {
                "guard_passed": True, "title": t, "summary": s, "legal_basis": l,
                "policy_level": inputs.get("policy_level", "国家级"), "category": inputs.get("category", "TAX"),
                "subsidy_amount_max": float(inputs.get("subsidy_amount_max", 0.0)),
                "eligible_conditions": inputs.get("eligible_conditions", []),
            }
        self.register("policy.publish.guard", validate_publish_policy, domain="policy", description="政策雷达政府红利发布准入与法律依据校验门禁")
        self.register("validate_publish_policy", validate_publish_policy, domain="policy", description="政策雷达政府红利发布准入与法律依据校验门禁")

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
        async def validate_sop_document_params(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验生成文书所需的模版有效性及表单数据敏感词合规"""
            from src.domains.sop.service import sop_service
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            res = sop_service.validate_render_payload(inputs)
            full_text = " ".join(str(v) for v in res["form_data"].values())
            await check_content_safety(full_text, field_name="SOP document form data")
            return res
        self.register("sop.document.validate_guard", validate_sop_document_params, domain="sop", description="合规文书模版准入与表单合规风控门禁")
        self.register("validate_sop_document_params", validate_sop_document_params, domain="sop", description="合规文书模版准入与表单合规风控门禁")

        async def render_and_save_sop_document(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：仅负责按模版渲染并持久化合规文书"""
            from src.domains.sop.service import sop_service
            from src.domains.sop.models import SOPDocumentCreate
            payload = SOPDocumentCreate(
                template_id=inputs.get("template_id", "").strip(),
                user_id=inputs.get("user_id", ""),
                form_data=inputs.get("form_data", {}),
            )
            doc = sop_service.render_and_save_document(payload)
            return {
                "sop_document_id": doc.id, "doc_id": doc.id, "document_title": doc.document_title,
                "generated_text": doc.rendered_content, "rendered_content": doc.rendered_content,
                "compliance_passed": doc.compliance_passed, "status": "READY",
                "created_at": doc.created_at, "created_doc": doc.model_dump(),
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
            render_and_save_sop_document,
            domain="sop",
            description="合规文书根据表单插值渲染并持久化存储算子",
            compensator=sop_document_render_compensate,
        )
        self.register(
            "sop.render_document",
            render_and_save_sop_document,
            domain="sop",
            description="企业商事登记公文组装与流水号签发算子",
            compensator=sop_document_render_compensate,
        )
        self.register(
            "render_and_save_sop_document",
            render_and_save_sop_document,
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

        async def evaluate_compliance_audit(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：调用合规服务计算六维防线评分报告"""
            from src.domains.compliance.service import compliance_service
            from src.domains.compliance.models import AuditEvaluateRequest
            req = AuditEvaluateRequest(passed_item_ids=inputs.get("checked_ids") or inputs.get("passed_item_ids", []))
            r = compliance_service.evaluate_audit(req)
            if r.grade == "CRITICAL" and inputs.get("strict_mode", False):
                raise PermissionError(f"Compliance strict guard blocked: score is {r.score} (CRITICAL)")
            return {
                "score": r.score, "grade": r.grade, "compliance_score": r.score, "compliance_grade": r.grade,
                "total_items": r.total_items, "passed_items_count": r.passed_items_count, "failed_items_count": r.failed_items_count,
                "risk_items": [item.model_dump() for item in r.risk_items],
                "remedy_suggestions": r.remedy_suggestions, "legal_help_recommendation": r.legal_help_recommendation,
                "audit_report": r.model_dump(),
            }

        async def compliance_audit_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            return {
                "compensated": True,
                "action": "ROLLED_BACK",
                "details": "Transient compliance audit session and recommendations cleared",
            }

        self.register(
            "compliance.evaluate_audit",
            evaluate_compliance_audit,
            domain="compliance",
            description="六维合规防线自检打分与风险阻断算子",
            compensator=compliance_audit_compensate,
        )
        self.register(
            "evaluate_compliance_audit",
            evaluate_compliance_audit,
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
            from src.infrastructure.external_gateway.content_moderation_gateway import content_moderation_gateway
            content = inputs.get("content", "")
            scan_res = await content_moderation_gateway.scan_text(content)
            if not scan_res["passed"]:
                hit_words = scan_res["hit_words"]
                raise ValueError(f"Content moderation violation: found prohibited keywords {hit_words}")
            return {
                "moderation_inspected": True,
                "passed": True,
                "flagged_keywords": [],
                "filtered_content": scan_res.get("filtered_content", content),
            }
        self.register("moderation.inspect_content", moderation_inspect_content, domain="moderation", description="UGC文本敏感词审查与违规处置算子")

        async def validate_takedown_request(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验下架操作的 item_id 与 reason 有效性"""
            from src.domains.moderation.service import moderation_service
            item_id = inputs.get("item_id", "").strip()
            reason = inputs.get("reason") or inputs.get("takedown_reason", "").strip()
            if not item_id or not reason:
                raise ValueError("item_id and non-empty takedown reason are required")
            item = moderation_service.get_item(item_id)
            if not item:
                raise ValueError(f"Moderation item {item_id} not found")
            return {
                "guard_passed": True, "item_id": item_id, "reason": reason,
                "moderator_id": inputs.get("moderator_id") or inputs.get("operator_id", "admin_001"),
                "ban_author": bool(inputs.get("ban_author", False)), "prev_status": item.status,
            }
        self.register("moderation.takedown.guard", validate_takedown_request, domain="moderation", description="内容治理违规下架前置守卫校验算子")
        self.register("validate_takedown_request", validate_takedown_request, domain="moderation", description="内容治理违规下架前置守卫校验算子")

        async def takedown_moderation_item(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：调用审核服务执行违规内容下架"""
            from src.domains.moderation.service import moderation_service
            from src.domains.moderation.models import TakedownRequest
            req = TakedownRequest(
                item_id=inputs.get("item_id"),
                reason=inputs.get("reason", "违规言论全网下架"),
                moderator_id=inputs.get("moderator_id", "admin_001"),
                ban_author=inputs.get("ban_author", False),
            )
            res = moderation_service.takedown(req)
            return {
                "item_id": res.item_id,
                "status": res.status,
                "moderated_at": res.moderated_at,
                "note": res.note,
                "prev_status": inputs.get("prev_status", "FLAGGED"),
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
            takedown_moderation_item,
            domain="moderation",
            description="内容治理违规言论下架持久化算子",
            compensator=moderation_takedown_persist_compensate,
        )
        self.register(
            "takedown_moderation_item",
            takedown_moderation_item,
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
            from src.domains.products.service import product_service
            from src.domains.demands.service import demand_service
            from src.domains.policies.service import policy_service
            from src.domains.user.service import user_service
            
            prods = product_service.list_products()
            demands = demand_service.list_demands()
            policies = policy_service.list_policies()
            real_users_count = len([u for u in user_service._users_by_uid.values() if u.get("role") != "GUEST"])
            
            return {
                "active_makers_count": real_users_count,
                "active_dags_count": 0,
                "matched_policies_count": len(policies),
                "demands_orders_count": len(demands),
                "perks_saved_cny": 0.0,
                "products_count": len(prods),
            }
        self.register("home.metrics.collector", home_metrics_collector, domain="home", description="首页全域宏观核心指标聚合算子")

        async def build_home_sitemap(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """极简算子：仅负责拉取论坛条数并委托 sitemap 构造器"""
            from src.domains.forum.service import forum_service
            from src.domains.sitemap_builder import build_sitemap_quick_links
            threads_count = len(forum_service.list_threads())
            quick_links = build_sitemap_quick_links(
                threads_count=threads_count,
                products_count=inputs.get("products_count", 0),
                policies_count=inputs.get("matched_policies_count", 0),
                demands_count=inputs.get("demands_orders_count", 0),
            )
            return {"quick_links": quick_links}
        self.register("home.sitemap.builder", build_home_sitemap, domain="home", description="首页全景功能空间地图装配算子")
        self.register("build_home_sitemap", build_home_sitemap, domain="home", description="首页全景功能空间地图装配算子")

        async def home_overview_aggregator(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from datetime import datetime, timezone
            return {
                "active_makers_count": inputs.get("active_makers_count", 0),
                "active_dags_count": inputs.get("active_dags_count", 0),
                "matched_policies_count": inputs.get("matched_policies_count", 0),
                "demands_orders_count": inputs.get("demands_orders_count", 0),
                "perks_saved_cny": inputs.get("perks_saved_cny", 0.0),
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
            
            # Content moderation check via external HTTP moderation gateway
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            await check_content_safety(f"{title} {content}", field_name="forum thread")
            
            return {
                "guard_passed": True,
                "title": title,
                "content": content,
                "category_code": category,
                "author_id": inputs.get("author_id", ""),
            }
        self.register("forum.thread.validate_guard", forum_thread_validate_guard, domain="forum", description="头脑风暴发帖准入校验与敏感词审查门禁")

        async def forum_thread_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            from src.domains.forum.models import ForumThreadCreate
            author_id = inputs.get("author_id") or (context or {}).get("user_id") or ""
            author_name = inputs.get("author_name") or (context or {}).get("nickname") or (context or {}).get("username")
            payload = ForumThreadCreate(
                category_code=inputs.get("category_code", "GENERAL"),
                author_id=author_id,
                author_name=author_name,
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

        async def validate_create_comment(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验发评论参数合法性并进行文本合规审查"""
            from src.domains.forum.service import forum_service
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            res = forum_service.validate_create_comment_payload(inputs)
            await check_content_safety(res["content"], field_name="forum comment")
            return res
        self.register("forum.comment.validate_guard", validate_create_comment, domain="forum", description="头脑风暴评论准入校验与物化层级校验门禁")
        self.register("validate_create_comment", validate_create_comment, domain="forum", description="头脑风暴评论准入校验与物化层级校验门禁")

        async def forum_comment_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            from src.domains.forum.models import ForumCommentCreate
            thread_id = inputs.get("thread_id", "")
            payload = ForumCommentCreate(
                author_id=inputs.get("author_id", ""),
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

        # Forum Stream Feed Operators (流式无限滚动、缓存与预加载)
        async def forum_feed_cursor_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            cat = str(inputs.get("category_code") or inputs.get("id") or "ALL").upper()
            cursor_raw = inputs.get("cursor", 0)
            try:
                cursor_val = max(0, int(cursor_raw))
            except (ValueError, TypeError):
                cursor_val = 0
            limit_raw = inputs.get("limit") or inputs.get("page_size") or inputs.get("page_length") or 10
            try:
                limit_val = max(1, min(int(limit_raw), 50))
            except (ValueError, TypeError):
                limit_val = 10
            sort_by = str(inputs.get("sort_by") or "latest").lower()
            if sort_by not in ("latest", "hot", "replies"):
                sort_by = "latest"
            user_id = inputs.get("user_id") or (context or {}).get("user_id") or ""
            return {
                "guard_passed": True,
                "category_code": cat,
                "cursor": cursor_val,
                "limit": limit_val,
                "sort_by": sort_by,
                "user_id": user_id,
            }
        self.register("forum.feed.cursor_guard", forum_feed_cursor_guard, domain="forum", description="头脑风暴流式游标校验与防刷门禁算子")

        async def forum_feed_cache_read(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            cat = inputs.get("category_code", "ALL")
            cursor = inputs.get("cursor", 0)
            limit = inputs.get("limit", 10)
            sort_by = inputs.get("sort_by", "latest")
            cache_key = f"{cat}:{sort_by}:{cursor}:{limit}"
            cached_data = forum_service.get_feed_cache(cache_key)
            if cached_data is not None:
                return {
                    "cache_hit": True,
                    "cache_key": cache_key,
                    "cached_data": cached_data,
                }
            return {
                "cache_hit": False,
                "cache_key": cache_key,
                "cached_data": None,
            }
        self.register("forum.feed.cache_read", forum_feed_cache_read, domain="forum", description="头脑风暴流式分片多级缓存命中算子")

        async def forum_feed_stream_fetch(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("cache_hit") and inputs.get("cached_data"):
                return {"stream_payload": inputs["cached_data"]}
            from src.domains.forum.service import forum_service
            cat = inputs.get("category_code", "ALL")
            cursor = inputs.get("cursor", 0)
            limit = inputs.get("limit", 10)
            sort_by = inputs.get("sort_by", "latest")
            stream_result = forum_service.fetch_feed_stream(
                category_code=cat,
                cursor=cursor,
                limit=limit,
                sort_by=sort_by,
            )
            return {"stream_payload": stream_result}
        self.register("forum.feed.stream_fetch", forum_feed_stream_fetch, domain="forum", description="头脑风暴帖子索引流检索与游标切片算子")

        async def forum_feed_enrich_prefetch_meta(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            stream_payload = dict(inputs.get("stream_payload") or {})
            next_cursor = stream_payload.get("next_cursor")
            limit = stream_payload.get("limit", 10)
            prefetch_hint = {
                "recommended_prefetch_cursor": next_cursor,
                "prefetch_threshold_ratio": 0.8,
                "batch_size": limit,
            }
            stream_payload["prefetch_hint"] = prefetch_hint
            return {
                "feed_enriched": True,
                "stream_payload": stream_payload,
                "feed_result": stream_payload,
            }
        self.register("forum.feed.enrich_prefetch_meta", forum_feed_enrich_prefetch_meta, domain="forum", description="头脑风暴流式交互润色与预加载元信息增强算子")

        async def forum_feed_cache_write(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            cache_hit = inputs.get("cache_hit", False)
            cache_key = inputs.get("cache_key")
            feed_result = inputs.get("feed_result") or inputs.get("stream_payload") or {}
            from src.domains.forum.service import forum_service
            if not cache_hit and cache_key and feed_result:
                forum_service.set_feed_cache(cache_key, feed_result)
            
            # Speculative background pre-warming for next batch
            prewarmed = False
            if feed_result.get("has_more") and feed_result.get("next_cursor") is not None:
                next_cur = feed_result["next_cursor"]
                cat = feed_result.get("category_code", "ALL")
                sort_by = feed_result.get("sort_by", "latest")
                limit = feed_result.get("limit", 10)
                next_cache_key = f"{cat}:{sort_by}:{next_cur}:{limit}"
                if forum_service.get_feed_cache(next_cache_key) is None:
                    next_batch = forum_service.fetch_feed_stream(
                        category_code=cat,
                        cursor=next_cur,
                        limit=limit,
                        sort_by=sort_by,
                    )
                    next_batch["prefetch_hint"] = {
                        "recommended_prefetch_cursor": next_batch.get("next_cursor"),
                        "prefetch_threshold_ratio": 0.8,
                        "batch_size": limit,
                    }
                    forum_service.set_feed_cache(next_cache_key, next_batch)
                    prewarmed = True

            return {
                "cache_written": True,
                "prewarmed_next": prewarmed,
                "feed_result": feed_result,
            }
        self.register("forum.feed.cache_write", forum_feed_cache_write, domain="forum", description="头脑风暴缓存回写与推测式下一批预热算子")

        async def forum_cache_invalidate_operator(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.forum.service import forum_service
            cat = inputs.get("category_code")
            evicted_count = forum_service.invalidate_feed_cache(cat)
            return {
                "cache_invalidated": True,
                "evicted_keys_count": evicted_count,
            }
        self.register("forum.cache.invalidate_operator", forum_cache_invalidate_operator, domain="forum", description="头脑风暴帖子变更缓存精准驱逐算子")

        # Domain 7: Product Showcase Domain (产品橱窗微内核算子与 Saga 补偿)
        async def validate_publish_product(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验独立商用作品发布入参合法性并做文本合规审查"""
            from src.domains.products.service import product_service
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            res = product_service.validate_publish_payload(inputs)
            await check_content_safety(f"{res['title']} {res['tagline']} {res['description']}", field_name="product showcase")
            return res
        self.register("product.validate_guard", validate_publish_product, domain="product", description="产品橱窗作品发布准入校验与合规审查门禁")
        self.register("validate_publish_product", validate_publish_product, domain="product", description="产品橱窗作品发布准入校验与合规审查门禁")

        async def product_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.products.service import product_service
            from src.domains.products.models import ProductCreate
            payload = ProductCreate(
                author_id=inputs.get("author_id", ""),
                title=inputs.get("title", ""),
                tagline=inputs.get("tagline", ""),
                description=inputs.get("description", "") or inputs.get("tagline", ""),
                category=inputs.get("category", "DEV"),
                pricing_model=inputs.get("pricing_model", "FREE"),
                price_cny=float(inputs.get("price_cny", 0.0)),
                demo_url=inputs.get("demo_url", ""),
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
        async def validate_publish_demand(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验发布需求入参合法性并进行敏感词风控审查"""
            from src.domains.demands.service import demand_service
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            res = demand_service.validate_publish_payload(inputs)
            await check_content_safety(f"{res['title']} {res['description']}", field_name="demand publish")
            return res
        self.register("demand.publish.guard", validate_publish_demand, domain="demands", description="需求集市外包寻源委托发布准入校验与合规审查门禁")
        self.register("validate_publish_demand", validate_publish_demand, domain="demands", description="需求集市外包寻源委托发布准入校验与合规审查门禁")

        async def demand_publish_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            from src.domains.demands.models import DemandCreate
            payload = DemandCreate(
                title=inputs.get("title", ""),
                description=inputs.get("description", ""),
                budget_cny=float(inputs.get("budget_cny", 0.0)),
                category=inputs.get("category", "DEV"),
                deadline_days=int(inputs.get("deadline_days", 14)),
                creator_id=inputs.get("creator_id", ""),
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

        async def validate_bid_demand(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验创客竞标方案合法性并审查提案内容安全"""
            from src.domains.demands.service import demand_service
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            res = demand_service.validate_bid_payload(inputs)
            await check_content_safety(res["proposal_text"], field_name="demand bid proposal")
            return res
        self.register("demand.bid.guard", validate_bid_demand, domain="demands", description="需求集市创客竞标方案准入审查门禁")
        self.register("validate_bid_demand", validate_bid_demand, domain="demands", description="需求集市创客竞标方案准入审查门禁")

        async def demand_bid_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.demands.service import demand_service
            from src.domains.demands.models import BidCreate
            demand_id = inputs.get("demand_id")
            payload = BidCreate(
                bidder_id=inputs.get("bidder_id", ""),
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
            user_id = inputs.get("user_id", "").strip()

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
            user_id = inputs.get("user_id", "")
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

        async def validate_publish_perk(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：校验生态特权福利上线合法性并进行文本合规审查"""
            from src.domains.perks.service import perk_service
            from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety
            res = perk_service.validate_publish_payload(inputs)
            await check_content_safety(f"{res['name']} {res['provider']} {res['summary']}", field_name="perk publish")
            return res
        self.register("perk.publish.guard", validate_publish_perk, domain="perks", description="生态特权提报上线准入与风控审查门禁")
        self.register("validate_publish_perk", validate_publish_perk, domain="perks", description="生态特权提报上线准入与风控审查门禁")

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
                "authority": res.get("department"),
                "publish_date": res.get("published_date"),
                "source_url": res.get("source_url"),
                "content_preview": res.get("content", "")[:200],
            }
        self.register("external.crawler.fetch_policy", external_crawler_fetch_policy, domain="external", description="统一外部网关低速合规采集政务公文")

        # 3. Payment Gateway
        async def split_payment_order(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：仅透传参数调用持牌支付网关执行分账"""
            from src.infrastructure.external_gateway import payment_gateway
            res = await payment_gateway.create_split_order(
                order_id=inputs.get("order_id", ""),
                amount_cny=float(inputs.get("amount", 0.0)),
                merchant_account=inputs.get("merchant_account", ""),
                maker_account=inputs.get("maker_account", ""),
                channel=inputs.get("channel", "WECHAT"),
            )
            return {
                "split_order_executed": res.get("status") == "SUCCESS",
                "platform_fee": res.get("platform_fee"), "maker_amount": res.get("maker_share"),
                "clearing_status": res.get("status"), "transaction_no": res.get("transaction_no"),
                "escrow_verified": res.get("escrow_verified", False),
            }
        self.register("external.payment.split_order", split_payment_order, domain="external", description="统一外部网关持牌分账结算指令")
        self.register("split_payment_order", split_payment_order, domain="external", description="统一外部网关持牌分账结算指令")

        # 4. SMS Gateway
        async def external_sms_send_auth_code(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.infrastructure.external_gateway import sms_auth_gateway
            phone = inputs.get("phone", "")
            code = inputs.get("code", "")
            res = await sms_auth_gateway.send_verification_code(phone, code)
            return {
                "sms_sent": res.get("status") == "SUCCESS",
                "phone_masked": res.get("phone_masked"),
                "sms_channel": res.get("sms_channel"),
                "sent_code_stub": res.get("sent_code_stub"),
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

        async def audit_ops_dashboard_access(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：仅为大盘调阅写入一条审计存证记录"""
            import uuid
            from datetime import datetime, timezone
            aid = f"aud_ops_{uuid.uuid4().hex[:8]}"
            _ops_audit_log[aid] = {
                "audit_id": aid,
                "operator_id": inputs.get("operator_id", "admin_001"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "RECORDED",
                "watermark": "SECURE_ADMIN_HASH_2026",
            }
            res = dict(inputs.get("dashboard", {}))
            res.update({"audit_id": aid, "audit_status": "RECORDED", "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False)})
            return res

        async def telemetry_dashboard_audit_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            audit_id = inputs.get("audit_id")
            if audit_id and audit_id in _ops_audit_log:
                _ops_audit_log[audit_id]["status"] = "ROLLED_BACK"
                return {"audit_id": audit_id, "compensated": True, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No audit record to rollback"}

        self.register(
            "telemetry.dashboard.audit",
            audit_ops_dashboard_access,
            domain="telemetry",
            description="运营大盘调阅脱敏水印签发与安全审计持久化算子",
            compensator=telemetry_dashboard_audit_compensate,
        )
        self.register(
            "audit_ops_dashboard_access",
            audit_ops_dashboard_access,
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

        # Domain 11: User & Maker Domain (创客档案画像、收费权益激活与防伪凭据签发算子及 Saga 补偿)
        async def user_profile_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            user_id = (inputs.get("user_id") or (context or {}).get("user_id") or "").strip()
            if not user_id:
                token = inputs.get("token") or (context or {}).get("token") or ""
                if token:
                    from src.core.security import verify_session_token
                    p = verify_session_token(token)
                    if p and p.get("uid"):
                        user_id = p.get("uid")
            if not user_id:
                user_id = "usr_guest"
            return {
                "guard_passed": True,
                "user_id": user_id,
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("user.profile.guard", user_profile_guard, domain="user", description="创客中心档案调阅参数守卫算子")

        async def user_profile_load(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.user.service import user_service
            user_id = inputs.get("user_id") or (context or {}).get("user_id") or "usr_guest"
            profile = user_service.get_profile(user_id)
            profile_dict = profile.model_dump()
            profile_dict["orchestrated_by"] = "OPC_USER_PROFILE_PIPELINE"
            return {
                "profile": profile_dict,
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("user.profile.load", user_profile_load, domain="user", description="创客主体认证档案与权益矩阵加载算子")

        async def user_entitlement_activate_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            user_id = inputs.get("user_id", "").strip()
            ent_id = inputs.get("entitlement_id") or inputs.get("entitlement_code", "").strip()

            if not user_id:
                raise ValueError("user_id is required for entitlement activation")
            if not ent_id:
                raise ValueError("entitlement_id or entitlement_code is required for activation")

            return {
                "guard_passed": True,
                "user_id": user_id,
                "entitlement_id": ent_id,
                "duration_months": inputs.get("duration_months", 12),
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("user.entitlement.activate.guard", user_entitlement_activate_guard, domain="user", description="创客收费商业权益激活前置参数守卫算子")

        async def user_entitlement_activate_persist(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.user.service import user_service
            from src.domains.user.models import EntitlementActivateRequest

            user_id = inputs.get("user_id")
            ent_id = inputs.get("entitlement_id")
            req = EntitlementActivateRequest(user_id=user_id, entitlement_id=ent_id)
            res = await user_service.activate_entitlement(req)

            res_dict = res.model_dump()
            res_dict["orchestrated_by"] = "OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE"
            return {
                "activation": res_dict,
                "user_id": user_id,
                "entitlement_id": res.entitlement_id,
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }

        async def user_entitlement_activate_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.user.service import user_service
            ent_id = inputs.get("entitlement_id")
            user_id = inputs.get("user_id")
            if ent_id:
                deactivated = await user_service.deactivate_entitlement(ent_id, user_id=user_id)
                return {
                    "entitlement_id": ent_id,
                    "user_id": user_id,
                    "compensated": deactivated,
                    "action": "ROLLED_BACK",
                }
            return {"compensated": False, "reason": "No entitlement_id to rollback"}

        self.register(
            "user.entitlement.activate.persist",
            user_entitlement_activate_persist,
            domain="user",
            description="创客专属商业权益原子激活持久化算子",
            compensator=user_entitlement_activate_persist_compensate,
        )

        async def user_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in user maker pipeline")
            metric = "user.entitlement.activated" if "activation" in inputs else "user.profile.view"
            return {
                "telemetry_recorded": True,
                "metric": metric,
                "increment": 1,
            }
        self.register("user.telemetry.incr", user_telemetry_incr, domain="user", description="创客中心业务与转化度量打点算子")

        # Domain 12: Orchestration Domain (微内核流程图可视化编排控制台、拓扑部署与热载算子及 Saga 补偿)
        async def orchestration_control_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            scenario_code = inputs.get("scenario_code", "").strip()
            version = inputs.get("version", "v1.0.0").strip()
            topology_graph = inputs.get("topology_graph") or inputs.get("config") or {}

            if not scenario_code:
                raise ValueError("scenario_code is required for DAG orchestration deployment")
            if not version:
                raise ValueError("version is required for DAG orchestration deployment")

            return {
                "guard_passed": True,
                "scenario_code": scenario_code,
                "version": version,
                "topology_graph": topology_graph,
                "status": inputs.get("status", "ACTIVE"),
                "created_by": inputs.get("created_by", "usr_admin_001"),
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("orchestration.control.guard", orchestration_control_guard, domain="orchestration", description="微内核DAG编排部署守卫校验算子")

        async def save_dag_config_record(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            """原子算子：调用编排服务持久化 DAG 拓扑配置"""
            from src.domains.orchestration.service import orchestration_service
            from src.domains.orchestration.models import DAGConfigSaveRequest
            topo = dict(inputs.get("topology_graph") or {})
            if "topology" not in topo and "topology" in inputs:
                topo["topology"] = inputs["topology"]
            req = DAGConfigSaveRequest(
                scenario_code=inputs.get("scenario_code"), version=inputs.get("version"),
                topology_graph=topo, status=inputs.get("status", "ACTIVE"),
                created_by=inputs.get("created_by", "usr_admin_001"),
            )
            saved = orchestration_service.save_dag_config(req).model_dump()
            saved["orchestrated_by"] = "OPC_ORCHESTRATION_CONTROL_PIPELINE"
            return {"dag_record": saved, "scenario_code": inputs.get("scenario_code"), "version": inputs.get("version"), "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False)}

        async def orchestration_control_persist_compensate(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.orchestration.service import orchestration_service
            scenario_code = inputs.get("scenario_code")
            version = inputs.get("version")
            if scenario_code and version:
                deleted = orchestration_service.delete_dag_config(scenario_code, version)
                return {"scenario_code": scenario_code, "version": version, "compensated": deleted, "action": "ROLLED_BACK"}
            return {"compensated": False, "reason": "No scenario_code/version to rollback"}

        self.register(
            "orchestration.control.persist",
            save_dag_config_record,
            domain="orchestration",
            description="微内核DAG编排拓扑配置原子持久化与热载算子",
            compensator=orchestration_control_persist_compensate,
        )
        self.register(
            "save_dag_config_record",
            save_dag_config_record,
            domain="orchestration",
            description="微内核DAG编排拓扑配置原子持久化与热载算子",
            compensator=orchestration_control_persist_compensate,
        )

        async def orchestration_control_telemetry_incr(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            if inputs.get("simulate_downstream_failure", False):
                raise RuntimeError("Simulated downstream telemetry failure in orchestration pipeline")
            return {
                "telemetry_recorded": True,
                "metric": "orchestration.dag.deployed",
                "scenario_code": inputs.get("scenario_code", "unknown"),
                "increment": 1,
            }
        self.register("orchestration.control.telemetry.incr", orchestration_control_telemetry_incr, domain="orchestration", description="编排控制台部署度量打点算子")

        async def orchestration_operators_guard(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            return {
                "guard_passed": True,
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("orchestration.operators.guard", orchestration_operators_guard, domain="orchestration", description="算子清单检索参数守卫算子")

        async def orchestration_operators_collect(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            from src.domains.orchestration.service import orchestration_service
            descriptors = orchestration_service.list_operators()
            desc_list = [d.model_dump() for d in descriptors]
            return {
                "operators": desc_list,
                "total_count": len(desc_list),
                "orchestrated_by": "OPC_ORCHESTRATION_OPERATORS_LIST_PIPELINE",
                "simulate_downstream_failure": inputs.get("simulate_downstream_failure", False),
            }
        self.register("orchestration.operators.collect", orchestration_operators_collect, domain="orchestration", description="全域微内核原子算子清单聚合算子")


registry = AtomicRegistry()
