"""Generic adapters for domain services referenced by gateway routes configuration."""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict
from src.domains.user.service import user_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import (
    ScenarioExecuteRequest,
    FrontendLayoutSaveRequest,
)
from src.infrastructure.external_gateway import (
    siliconflow_gateway,
    payment_gateway,
    gov_crawler_gateway,
)
from src.core.rag import policy_rag_service, forum_rag_service

# Imported eagerly so its domain-persistence hydrators are registered before
# startup hydration (restart durability for interactions / comments / loyalty).
from src.domains.interactions.service import content_interaction_service  # noqa: E402,F401
from src.domains.loyalty.service import loyalty_service  # noqa: E402,F401

logger = logging.getLogger("opchub.gateway.adapters")


def _publish_identity_fields(
    inputs: Dict[str, Any],
    c: Dict[str, Any] = None,
    author_key: str = "author_id",
    name_key: str = "author_name",
) -> None:
    """Declare the payload identity fields for the identity-guard operator.

    Identity binding and the official tag are now decided inside
    ``content.publish.identity_guard``, which reads the gateway context that is
    propagated with the scenario request. Adapters only declare which payload
    fields carry the author identity.
    """
    inputs["_author_key"] = author_key
    inputs["_author_name_key"] = name_key


# ---------------------------------------------------------------------------
# Loyalty bridge helpers
#
# Publishing / interacting / reading are business domains; points are a separate
# loyalty domain. These helpers execute the loyalty DAG pipelines and never let
# a points failure break the business action (best-effort, logged).
# ---------------------------------------------------------------------------


async def _run_loyalty_pipeline(scenario_code: str, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    from src.domains.loyalty.pipelines import ensure_loyalty_pipelines

    ensure_loyalty_pipelines()
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario_code,
            version="v1.0.0",
            inputs=dict(inputs or {}),
            context=dict(context or {}),
        )
    )
    return res.final_output if res.status == "SUCCESS" else {"loyalty_error": res.error_message}


async def _award_loyalty(
    event_code: str,
    user_id: str,
    actor_id: str,
    target_type: str,
    target_id: str,
    context: Dict[str, Any] = None,
    idempotency_key: str = "",
    note: str = "",
) -> Dict[str, Any]:
    from src.domains.loyalty.pipelines import AWARD_PIPELINE

    try:
        return await _run_loyalty_pipeline(
            AWARD_PIPELINE,
            {
                "event_code": event_code,
                "user_id": user_id,
                "actor_id": actor_id,
                "target_type": target_type,
                "target_id": target_id,
                "idempotency_key": idempotency_key or None,
                "note": note,
            },
            context,
        )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Loyalty award failed for %s/%s: %s", event_code, target_id, exc)
        return {"loyalty_error": str(exc)}


async def _revoke_loyalty(
    event_code: str,
    target_type: str,
    target_id: str,
    context: Dict[str, Any] = None,
    idempotency_key: str = "",
    actor_id: str = "",
) -> Dict[str, Any]:
    from src.domains.loyalty.pipelines import REVOKE_PIPELINE

    try:
        return await _run_loyalty_pipeline(
            REVOKE_PIPELINE,
            {
                "event_code": event_code,
                "actor_id": actor_id,
                "target_type": target_type,
                "target_id": target_id,
                "idempotency_key": idempotency_key or None,
            },
            context,
        )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Loyalty revoke failed for %s/%s: %s", event_code, target_id, exc)
        return {"loyalty_error": str(exc)}


async def _award_publish_points(
    event_code: str,
    target_type: str,
    entity: Any,
    context: Dict[str, Any] = None,
) -> None:
    """Award publish points after a publish pipeline has actually persisted content."""
    if not isinstance(entity, dict):
        return
    target_id = (
        entity.get("id")
        or entity.get("thread_id")
        or entity.get("product_id")
        or entity.get("demand_id")
        or entity.get("doc_id")
        or entity.get("flow_id")
        or entity.get("perk_id")
        or entity.get("compliance_id")
        or ""
    )
    author_id = (
        entity.get("author_id")
        or entity.get("creator_id")
        or entity.get("owner_id")
        or entity.get("user_id")
        or (context or {}).get("user_id", "")
    )
    if not target_id or not author_id:
        return
    first_publish = not loyalty_service.has_award(str(author_id), "PUBLISH_")
    await _award_loyalty(
        event_code=event_code,
        user_id=str(author_id),
        actor_id=str((context or {}).get("user_id") or author_id),
        target_type=target_type,
        target_id=str(target_id),
        context=context,
        idempotency_key=f"publish:{target_type}:{target_id}",
    )
    if first_publish:
        await _award_loyalty(
            event_code="FIRST_PUBLISH",
            user_id=str(author_id),
            actor_id=str(author_id),
            target_type=target_type,
            target_id=str(target_id),
            context=context,
            idempotency_key=f"once:FIRST_PUBLISH:{author_id}",
        )


async def demand_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for enterprise outsourcing demand publishing."""
    inputs = dict(p)
    if "demand_payload" in inputs and isinstance(inputs["demand_payload"], dict):
        inputs.update(inputs["demand_payload"])
    _publish_identity_fields(inputs, c, author_key="creator_id", name_key="creator_name")

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Demand publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_demand") or res.final_output
    await _award_publish_points("PUBLISH_DEMAND", "DEMAND", created, c)
    return created


async def demand_bid_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for maker demand bidding."""
    inputs = dict(p)
    if "bid_payload" in inputs and isinstance(inputs["bid_payload"], dict):
        inputs.update(inputs["bid_payload"])
    _publish_identity_fields(inputs, c, author_key="bidder_id", name_key="bidder_name")

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_BID_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Demand bidding pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_bid") or res.final_output


async def sop_flow_create_adapter(p: Any, c: Dict[str, Any] = None) -> Any:
    """Create a maker-owned flow.

    The route uses the default payload+context contract, so ``p`` is the raw payload
    mapping and ``c`` carries the identity injected by the router.
    """
    from src.domains.sop.service import sop_service
    req = p if hasattr(p, "node_refs") else _build_flow_create(p)
    # The router injects the verified identity into the context; use it as the owner
    # so a flow always belongs to the maker who created it.
    if not getattr(req, "owner_id", ""):
        req.owner_id = (c or {}).get("user_id", "")
    flow = sop_service.create_flow(req)
    return flow.model_dump()


async def sop_flow_update_adapter(p: Any, c: Dict[str, Any] = None) -> Any:
    """Update an existing maker-owned flow."""
    from src.domains.sop.service import sop_service
    req = p if hasattr(p, "node_refs") else _build_flow_create(p)
    flow_id = getattr(req, "flow_id", None) or (c or {}).get("flow_id")
    if not flow_id:
        raise ValueError("flow_id is required for SOP flow update")
    flow = sop_service.update_flow(flow_id, req)
    return flow.model_dump()


async def sop_flow_delete_adapter(p: Any, c: Dict[str, Any] = None) -> Any:
    """Delete a maker-owned flow. The route is key-typed, so ``p`` is the flow id."""
    from src.domains.sop.service import sop_service
    flow_id = p if isinstance(p, str) else (c or {}).get("flow_id")
    if not flow_id:
        raise ValueError("flow_id is required for SOP flow deletion")
    return {"deleted": sop_service.delete_flow(flow_id)}


def _build_flow_create(data: Dict[str, Any]):
    """Build an SOPFlowCreate from a raw payload mapping."""
    from src.domains.sop.models import SOPFlowCreate
    return SOPFlowCreate(**(data or {}))


async def sop_document_catalog_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """List the standard document catalog for the workbench.

    The route uses the default payload+context contract, so ``c`` carries the
    identity injected by the router.
    """
    from src.domains.sop.service import sop_service
    payload = p or {}
    user_id = (c or {}).get("user_id") or payload.get("user_id") or ""
    catalog = sop_service.list_document_cards(
        user_id=user_id,
        category=payload.get("category"),
    )
    return catalog.model_dump()


async def sop_flow_template_catalog_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """List the platform flow catalog for the flow-guide workspace."""
    from src.domains.sop.service import sop_service
    payload = p or {}
    user_id = (c or {}).get("user_id") or payload.get("user_id") or ""
    catalog = sop_service.list_flow_template_cards(
        user_id=user_id,
        category=payload.get("category"),
    )
    return catalog.model_dump()


async def sop_flow_template_detail_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Resolve one platform flow template into its ordered document steps.

    The route is key-typed, so the handler receives the bare ``flow_id`` string.
    """
    from src.domains.sop.service import sop_service
    flow_id = p if isinstance(p, str) else ((p or {}).get("flow_id") or (c or {}).get("flow_id"))
    if not flow_id:
        raise ValueError("flow_id is required for SOP flow template detail")
    detail = sop_service.get_flow_template_detail(flow_id)
    return detail.model_dump()






async def sop_node_context_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Resolve one workflow node (document or subgraph) into its full maker-facing context.

    The route is declared with ``args_type: "key"``, so the handler receives the bare
    ``node_id`` string rather than the full payload mapping.
    """
    from src.domains.sop.service import sop_service
    node_id = p if isinstance(p, str) else ((p or {}).get("node_id") or (p or {}).get("id") or "")
    if not node_id:
        raise ValueError("node_id is required for SOP node context")
    ctx = sop_service.get_node_context(node_id)
    node = ctx["node"]
    children = ctx["children"]
    return {
        "node": node.model_dump(),
        "children": [ch.model_dump() for ch in children],
        "prerequisites": ctx["prerequisites"],
    }


async def sop_document_render_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for SOP document generation and persistence."""
    inputs = dict(p)
    if "doc_payload" in inputs and isinstance(inputs["doc_payload"], dict):
        inputs.update(inputs["doc_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_SOP_DOCUMENT_RENDER_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "SOP document render pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_doc") or res.final_output


async def sop_document_draft_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Save a freely-edited document draft via the unified draft DAG (起草新文书).

    算子链路：identity_guard → sop.document.draft.guard（正文校验 + 修改前
    快照）→ draft.persist（新建删除 / 更新回滚）→ telemetry。
    """
    inputs = dict(p or {})
    _publish_identity_fields(inputs, c, author_key="user_id", name_key="author_name")
    inputs["_publish_metric"] = "sop.document.drafted"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_SOP_DOCUMENT_DRAFT_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "SOP document draft pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_doc") or res.final_output


async def sop_document_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Submit a maker document for publish review via the unified DAG."""
    inputs = dict(p or {})
    _publish_identity_fields(inputs, c, author_key="user_id", name_key="author_name")
    inputs["_publish_metric"] = "sop.document.submitted"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_SOP_DOCUMENT_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "SOP document publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("review_submission") or res.final_output


async def sop_flow_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Submit a maker flow for publish review via the unified DAG."""
    inputs = dict(p or {})
    _publish_identity_fields(inputs, c, author_key="user_id", name_key="author_name")
    inputs["_publish_metric"] = "sop.flow.submitted"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_SOP_FLOW_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "SOP flow publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("review_submission") or res.final_output


async def sop_review_queue_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """List the publish review queue (documents & flows awaiting audit)."""
    from src.domains.sop.service import sop_service
    payload = p or {}
    res = sop_service.list_review_queue(status=payload.get("status"))
    return res.model_dump()


async def sop_review_process_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Consume the review queue: audit legality/compliance/sensitive words, then
    promote approved submissions into the standard catalogs."""
    from src.domains.sop.service import sop_service
    payload = p or {}
    limit = payload.get("limit")
    pending = sop_service.list_review_queue(status="PENDING").items
    res = await sop_service.process_review_queue(limit=limit)
    approved = set(res.published_documents) | set(res.published_flows)
    for item in pending:
        if item.target_id not in approved:
            continue
        target_type = "SOP_DOCUMENT" if item.target_type == "DOCUMENT" else "SOP_FLOW"
        await _award_loyalty(
            "PUBLISH_SOP",
            item.author_id,
            item.author_id,
            target_type,
            item.target_id,
            c,
            f"publish:{target_type}:{item.target_id}",
            note=item.title,
        )
    return res.model_dump()


async def perk_claim_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for developer perk redemption."""
    inputs = dict(p)
    if "claim_payload" in inputs and isinstance(inputs["claim_payload"], dict):
        inputs.update(inputs["claim_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_CLAIM_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Perk claim pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_claim") or res.final_output


async def perk_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for ecosystem perk publishing."""
    inputs = dict(p)
    if "perk_payload" in inputs and isinstance(inputs["perk_payload"], dict):
        inputs.update(inputs["perk_payload"])
    _publish_identity_fields(inputs, c)

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Perk publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_perk") or res.final_output
    await _award_publish_points("PUBLISH_PERK", "PERK", created, c)
    return created


async def compliance_audit_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for product compliance self-audit."""
    inputs = dict(p)
    if "audit_payload" in inputs and isinstance(inputs["audit_payload"], dict):
        inputs.update(inputs["audit_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_COMPLIANCE_AUDIT_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Compliance audit pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("audit_report") or res.final_output


async def content_report_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """User report on questionable content via the report DAG (用户举报).

    算子链路：moderation.report.guard（目标/举报人校验）→ report.persist
    （同目标合并去重，含补偿）→ telemetry。
    """
    inputs = dict(p or {})
    inputs["_publish_metric"] = "moderation.reported"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_MODERATION_REPORT_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Content report pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_report") or res.final_output


def _notification_uid(c: Dict[str, Any] = None) -> str:
    uid = str((c or {}).get("user_id") or "").strip()
    if not uid:
        raise PermissionError("请先登录创客账号后查看消息箱")
    return uid


async def notifications_list_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """List the caller's own message-box receipts (消息箱)."""
    from src.domains.notifications.service import notification_service

    payload = p or {}
    res = notification_service.list_for_user(
        _notification_uid(c),
        status=payload.get("status"),
        limit=int(payload.get("limit") or 50),
        offset=int(payload.get("offset") or 0),
    )
    return res.model_dump()


async def notifications_unread_count_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Return the caller's unread message count (navbar badge)."""
    from src.domains.notifications.service import notification_service

    return {"unread": notification_service.unread_count(_notification_uid(c))}


async def notifications_mark_read_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Mark one/several of the caller's messages as read."""
    from src.domains.notifications.service import notification_service

    payload = p or {}
    ids = payload.get("ids")
    if not isinstance(ids, list):
        ids = [payload.get("id")] if payload.get("id") else []
    res = notification_service.mark_read(_notification_uid(c), [str(i) for i in ids if i])
    return res.model_dump()


async def notifications_mark_all_read_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Mark every unread message of the caller as read."""
    from src.domains.notifications.service import notification_service

    return notification_service.mark_all_read(_notification_uid(c)).model_dump()


async def notifications_delete_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Delete one message owned by the caller."""
    from src.domains.notifications.service import notification_service

    payload = p or {}
    res = notification_service.delete(
        _notification_uid(c),
        str(payload.get("id") or payload.get("notification_id") or ""),
    )
    return res.model_dump()


async def moderation_takedown_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for content moderation takedown."""
    inputs = dict(p)
    if "takedown_payload" in inputs and isinstance(inputs["takedown_payload"], dict):
        inputs.update(inputs["takedown_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_MODERATION_TAKEDOWN_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Moderation takedown pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def moderation_restore_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for content moderation restore."""
    inputs = dict(p)
    if "restore_payload" in inputs and isinstance(inputs["restore_payload"], dict):
        inputs.update(inputs["restore_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_MODERATION_RESTORE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Moderation restore pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def ops_dashboard_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for Ops Dashboard telemetry aggregation."""
    inputs = dict(p or {})
    if "dashboard_payload" in inputs and isinstance(inputs["dashboard_payload"], dict):
        inputs.update(inputs["dashboard_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_OPS_DASHBOARD_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Ops dashboard pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def forum_thread_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for forum thread publishing."""
    inputs = dict(p)
    if "thread_payload" in inputs and isinstance(inputs["thread_payload"], dict):
        inputs.update(inputs["thread_payload"])

    # Bind authenticated user identity if author_id is not explicitly provided
    _publish_identity_fields(inputs, c)

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_THREAD_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum thread publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_thread") or res.final_output
    await _award_publish_points("PUBLISH_FORUM", "FORUM_THREAD", created, c)
    return created


async def forum_feed_stream_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for forum infinite scroll feed and caching."""
    inputs = dict(p)
    if not inputs.get("user_id") and (c or {}).get("user_id"):
        inputs["user_id"] = c["user_id"]
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum feed stream pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("feed_result") or res.final_output


async def forum_comment_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for forum comment publishing."""
    inputs = dict(p)
    _publish_identity_fields(inputs, c)

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_COMMENT_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum comment publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_comment") or res.final_output


async def forum_answer_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for posting a Zhihu-style perspective answer."""
    inputs = dict(p)
    if "answer_payload" in inputs and isinstance(inputs["answer_payload"], dict):
        inputs.update(inputs["answer_payload"])
    _publish_identity_fields(inputs, c)

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_ANSWER_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum answer publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_answer") or res.final_output
    await _award_publish_points("PUBLISH_ANSWER", "FORUM_ANSWER", created, c)
    return created


async def forum_answer_accept_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for accepting a best answer."""
    inputs = dict(p)
    if not inputs.get("operator_user_id") and (c or {}).get("user_id"):
        inputs["operator_user_id"] = c["user_id"]

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_ANSWER_ACCEPT_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum answer accept pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def forum_vote_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for mutual upvoting/downvoting."""
    inputs = dict(p)
    if not inputs.get("user_id") and (c or {}).get("user_id"):
        inputs["user_id"] = c["user_id"]
    if not inputs.get("user_id"):
        inputs["user_id"] = "usr_guest"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_VOTE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum vote pipeline failed"
        # The engine flattens node exceptions into a message; restore 404 semantics.
        if "not found" in error_msg.lower():
            raise KeyError(error_msg)
        raise ValueError(error_msg)
    vote = res.final_output.get("vote_result") or res.final_output
    if isinstance(vote, dict) and str(vote.get("target_type") or "").upper() == "THREAD":
        actor = str(inputs.get("user_id") or "")
        thread_id = str(vote.get("target_id") or inputs.get("target_id") or "")
        like_key = f"forum-vote-like:{actor}:THREAD:{thread_id}"
        dislike_key = f"forum-vote-dislike:{actor}:THREAD:{thread_id}"
        # Switching votes must first reverse the previous ledger entry.
        await _revoke_loyalty("RECEIVE_LIKE", "FORUM_THREAD", thread_id, c, like_key, actor_id=actor)
        await _revoke_loyalty("RECEIVE_DISLIKE", "FORUM_THREAD", thread_id, c, dislike_key, actor_id=actor)
        if vote.get("user_vote") == "UPVOTE":
            await _award_loyalty("RECEIVE_LIKE", "", actor, "FORUM_THREAD", thread_id, c, like_key)
        elif vote.get("user_vote") == "DOWNVOTE":
            await _award_loyalty("RECEIVE_DISLIKE", "", actor, "FORUM_THREAD", thread_id, c, dislike_key)
    return vote


async def forum_thread_get_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Fetch Zhihu-style thread/question details with answers, comments, and caller interactions."""
    from src.domains.forum.service import forum_service
    thread_id = str(p.get("thread_id") or p.get("id") or "")
    if not thread_id:
        raise ValueError("thread_id is required")
    user_id = p.get("user_id") or (c or {}).get("user_id")
    detail = forum_service.get_thread_detail(thread_id, user_id=user_id)
    if not detail:
        raise KeyError(f"Forum thread with ID {thread_id} not found")
    return detail.model_dump()


async def forum_follow_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Toggle following a thread/question."""
    from src.domains.forum.service import forum_service
    user_id = p.get("user_id") or (c or {}).get("user_id") or "usr_guest"
    thread_id = str(p.get("thread_id") or "")
    if not thread_id:
        raise ValueError("thread_id is required")
    return forum_service.toggle_follow(user_id, thread_id)


async def forum_thread_update_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for editing a forum thread (author or ADMIN)."""
    inputs = dict(p)
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_THREAD_UPDATE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum thread update pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("updated_thread") or res.final_output


async def forum_answer_delete_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for deleting a Zhihu-style answer."""
    inputs = dict(p)
    if not inputs.get("operator_user_id") and (c or {}).get("user_id"):
        inputs["operator_user_id"] = c["user_id"]
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_ANSWER_DELETE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum answer delete pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def forum_comment_delete_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for deleting a forum comment subtree."""
    inputs = dict(p)
    if not inputs.get("operator_user_id") and (c or {}).get("user_id"):
        inputs["operator_user_id"] = c["user_id"]
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_COMMENT_DELETE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum comment delete pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def product_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for product showcase publishing."""
    inputs = dict(p)
    if "product_payload" in inputs and isinstance(inputs["product_payload"], dict):
        inputs.update(inputs["product_payload"])
    _publish_identity_fields(inputs, c)

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PRODUCT_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Product showcase publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_product") or res.final_output
    await _award_publish_points("PUBLISH_PRODUCT", "PRODUCT", created, c)
    return created


async def policy_match_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for policy qualification matching."""
    inputs = dict(p)
    if "match_payload" in inputs and isinstance(inputs["match_payload"], dict):
        inputs.update(inputs["match_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_POLICY_MATCH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Policy match pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def policy_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for government policy publishing."""
    inputs = dict(p)
    if "policy_payload" in inputs and isinstance(inputs["policy_payload"], dict):
        inputs.update(inputs["policy_payload"])
    _publish_identity_fields(inputs, c)

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_POLICY_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Policy publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_policy") or res.final_output
    await _award_publish_points("PUBLISH_POLICY", "POLICY", created, c)
    return created


async def compliance_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Publish a legal provision / pitfall case via the unified publish DAG.

    算子链路：content.publish.identity_guard → compliance.publish.guard（两级
    敏感词门禁）→ compliance.publish.persist（含 Saga 补偿）→ telemetry。
    """
    inputs = dict(p or {})
    _publish_identity_fields(inputs, c)
    inputs["_publish_metric"] = "compliance.published"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_COMPLIANCE_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Compliance publish pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_entry") or res.final_output
    await _award_publish_points("PUBLISH_COMPLIANCE", "COMPLIANCE", created, c)
    return created


async def home_overview_adapter(p: Dict[str, Any], c: Dict[str, Any]) -> Any:
    """Executes the microkernel DAG pipeline for the Home page overview."""
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_HOME_OVERVIEW_PIPELINE",
            version="v1.0.0",
            inputs=p or {},
        )
    )
    if res.status != "SUCCESS":
        return {
            "active_makers_count": 0,
            "active_dags_count": 0,
            "matched_policies_count": 0,
            "demands_orders_count": 0,
            "perks_saved_cny": 0.0,
            "products_count": 0,
            "forum_threads_count": 0,
            "quick_links": [],
            "orchestrated": False,
        }
    return res.final_output


async def user_profile_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for maker profile retrieval."""
    inputs = dict(p or {})
    if "user_payload" in inputs and isinstance(inputs["user_payload"], dict):
        inputs.update(inputs["user_payload"])
    if c:
        if "token" in c and "token" not in inputs:
            inputs["token"] = c["token"]
        if "user_id" in c and "user_id" not in inputs:
            inputs["user_id"] = c["user_id"]

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_USER_PROFILE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "User profile pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("profile") or res.final_output


async def user_profile_update_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Update maker profile in memory and DB."""
    from src.domains.user.service import user_service
    from src.domains.user.models import UserProfileUpdateRequest
    token = p.get("token") or (c or {}).get("token") or ""
    req = UserProfileUpdateRequest(
        user_id=p.get("user_id") or (c or {}).get("user_id"),
        nickname=p.get("nickname"),
        phone=p.get("phone"),
        company_name=p.get("company_name"),
        credit_code=p.get("credit_code"),
        industry_track=p.get("industry_track"),
        avatar_id=p.get("avatar_id"),
    )
    profile = await user_service.update_profile(req=req, token=token)
    profile_ctx = {**(c or {}), "user_id": profile.uid, "user_role": profile.role or "MAKER"}
    if profile.avatar_id and profile.industry_track and (profile.company_name or profile.credit_code):
        await _award_loyalty(
            "PROFILE_COMPLETE",
            profile.uid,
            profile.uid,
            "",
            "",
            profile_ctx,
            f"once:PROFILE_COMPLETE:{profile.uid}",
        )
    return profile.model_dump()


async def user_entitlement_activate_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for maker entitlement activation."""
    inputs = dict(p or {})
    if "activate_payload" in inputs and isinstance(inputs["activate_payload"], dict):
        inputs.update(inputs["activate_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "User entitlement activate pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("activation") or res.final_output


async def save_dag_config_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for orchestration config saving and deployment."""
    inputs = dict(p or {})
    topo = inputs.get("topology_graph") or inputs.get("config") or {}
    if "topology" not in topo and "topology" in inputs:
        topo["topology"] = inputs["topology"]
    inputs["topology_graph"] = topo

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_ORCHESTRATION_CONTROL_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Orchestration control pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def list_operators_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for operator descriptor enumeration."""
    inputs = dict(p or {})
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_ORCHESTRATION_OPERATORS_LIST_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Operators list pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("operators") or res.final_output


def save_layout_adapter(p: Dict[str, Any]) -> Any:
    return orchestration_service.save_frontend_layout(
        FrontendLayoutSaveRequest(
            layout_name=p.get("layout_name") or p.get("page_key", "main_console_layout"),
            version=p.get("version", "v1.0.4"),
            grid_schema=p.get("grid_schema", {"columns": 24, "type": "fluid_grid"}),
            widgets=p.get("widgets", []),
        )
    )


def get_frontend_layout_adapter(p: Dict[str, Any]) -> Any:
    layout_name = p.get("layout_name") or p.get("layout_id") or "main_console_layout"
    return orchestration_service.get_frontend_layout(layout_name=layout_name)


async def async_scenario_executor(payload: Dict[str, Any], context: Dict[str, Any]) -> Any:
    req = ScenarioExecuteRequest(**payload)
    if context:
        req.context = {**context, **req.context}
    return await orchestration_service.execute_scenario(req)


# ==========================================
# External Ecosystem Outbound Gateway Adapters
# ==========================================
async def external_siliconflow_chat_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes SiliconFlow AI chat completion with OpenAI-compatible payload."""
    messages = p.get("messages", [])
    if not messages and "prompt" in p:
        messages = [{"role": "user", "content": p["prompt"]}]
    model = p.get("model")
    temp = float(p.get("temperature", 0.3))
    max_tok = int(p.get("max_tokens", 1024))
    return await siliconflow_gateway.chat_completion(
        messages=messages,
        model=model,
        temperature=temp,
        max_tokens=max_tok
    )


async def external_siliconflow_summarize_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes SiliconFlow AI policy white-talk summarization."""
    title = p.get("title") or p.get("policy_title", "")
    full_text = p.get("full_text") or p.get("policy_full_text", "")
    model = p.get("model")
    return await siliconflow_gateway.summarize_policy(
        policy_title=title,
        policy_full_text=full_text,
        model=model
    )


async def external_siliconflow_charter_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes SiliconFlow AI legal charter drafting for One-Person Companies."""
    company_name = p.get("company_name", "杭州超级个体科技有限公司")
    biz_scope = p.get("biz_scope", "软件研发与人工智能算法服务")
    capital = float(p.get("registered_capital_cny", 100000.0))
    model = p.get("model")
    return await siliconflow_gateway.generate_charter_text(
        company_name=company_name,
        biz_scope=biz_scope,
        registered_capital_cny=capital,
        model=model
    )


async def external_payment_split_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes anti-fund-pooling split payment order via WeChat Pay or Stripe."""
    order_id = p.get("order_id", f"ord_{int(time.time()*1000)}")
    amount_cny = float(p.get("amount_cny", p.get("amount", 100.0)))
    merchant_account = p.get("merchant_account", "mch_opchub_platform")
    maker_account = p.get("maker_account", "maker_licensed_escrow")
    channel = p.get("channel", "WECHAT")
    return await payment_gateway.create_split_order(
        order_id=order_id,
        amount_cny=amount_cny,
        merchant_account=merchant_account,
        maker_account=maker_account,
        channel=channel
    )


async def external_gov_sat_policy_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Fetches official State Taxation Administration announcement."""
    year = int(p.get("year", 2023))
    num = int(p.get("num", 12))
    return await gov_crawler_gateway.fetch_sat_announcement(year=year, num=num)


async def external_rag_policy_search_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes RAG semantic hybrid vector search over government policies."""
    query = p.get("query", p.get("search_query", "增值税减免"))
    top_k = int(p.get("top_k", 5))
    region = p.get("region")
    category = p.get("category")
    return await policy_rag_service.search_policies(
        query=query,
        top_k=top_k,
        region=region,
        category=category,
    )


async def external_rag_forum_qa_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes RAG community Q&A search and AI expert answer generation."""
    question = p.get("question", p.get("query", "一人公司如何报税与开设银行对公户？"))
    top_k = int(p.get("top_k", 3))
    return await forum_rag_service.ask_forum_rag(
        question=question,
        top_k=top_k,
    )


async def auth_register_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Register maker account via email with commercial validations."""
    from src.domains.user.models import UserRegisterRequest
    params = dict(p)
    if c and not params.get("client_ip") and c.get("client_ip"):
        params["client_ip"] = c.get("client_ip")
    req = UserRegisterRequest(**params)
    res = await user_service.register_by_email(req)
    if params.get("verification_code"):
        await _award_loyalty(
            "VERIFY_EMAIL",
            res.uid,
            res.uid,
            "",
            "",
            {**(c or {}), "user_id": res.uid, "user_role": "MAKER"},
            f"once:VERIFY_EMAIL:{res.uid}",
        )
    return res.model_dump()


async def auth_captcha_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Generate lightweight anti-bot SVG challenge."""
    from src.domains.user.service import user_service
    return user_service.generate_captcha()


async def auth_send_code_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Dispatch email verification code with rate-limiting and anti-bot validation."""
    from src.domains.user.service import user_service
    email = p.get("email", "")
    captcha_id = p.get("captcha_id")
    captcha_code = p.get("captcha_code")
    client_ip = (c or {}).get("client_ip") or p.get("client_ip")
    return user_service.send_verification_code(
        email=email,
        captcha_id=captcha_id,
        captcha_code=captcha_code,
        client_ip=client_ip,
    )


async def auth_verify_code_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Pre-verify an email verification code."""
    from src.domains.user.service import user_service
    email = p.get("email", "")
    code = p.get("code", "")
    valid = user_service.verify_email_code(email, code)
    if not valid:
        raise ValueError("验证码错误或已失效")
    return {"valid": True, "message": "验证码有效"}


async def auth_password_strength_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Evaluate password strength against commercial standards."""
    from src.domains.user.service import user_service
    password = p.get("password", "")
    email = p.get("email")
    return user_service.evaluate_password_strength(password, email=email)


async def auth_legal_agreements_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Retrieve full text and versions of legal service agreements and privacy policy."""
    from src.domains.user.service import user_service
    return user_service.get_legal_agreements()


async def auth_mail_providers_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Retrieve list of supported email providers and active routing configurations."""
    from src.domains.user.service import user_service
    target_email = p.get("email")
    if target_email:
        return user_service.resolve_mail_provider(target_email)
    return user_service.get_supported_mail_providers()


async def auth_login_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Authenticate maker via email and password."""
    from src.domains.user.models import UserLoginRequest
    req = UserLoginRequest(**p)
    res = await user_service.login_by_email(req)
    return res.model_dump()


async def auth_session_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Verify session token and retrieve current maker info."""
    from src.core.security import verify_session_token
    token = p.get("token") or (c or {}).get("token") or ""
    payload = verify_session_token(token)
    if not payload:
        raise ValueError("会话已失效或未提供有效登录凭据")
    uid = payload.get("uid", "")
    email = payload.get("email", "")
    nickname = payload.get("nickname", "创客")
    profile = user_service.get_profile(uid=uid)
    return {
        "valid": True,
        "authenticated": True,
        "token": token,
        "uid": uid,
        "email": email,
        "nickname": nickname,
        "role": payload.get("role", "MAKER"),
        "tier_name": profile.tier_name if profile else "标准创客",
        "session": payload,
        "profile": profile.model_dump() if profile else {},
    }


async def auth_change_password_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Rotate the caller's password; clears the built-in admin must_change_password flag."""
    from src.domains.user.models import ChangePasswordRequest
    token = p.get("token") or (c or {}).get("token") or ""
    payload = {k: v for k, v in (p or {}).items() if k in {"old_password", "new_password", "user_id", "token"}}
    if token and not payload.get("token"):
        payload["token"] = token
    res = await user_service.change_password(ChangePasswordRequest(**payload))
    return res.model_dump()


async def forum_thread_delete_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Delete a forum thread and cascade delete its comments (ADMIN or author)."""
    from src.domains.forum.service import forum_service
    thread_id = str(p.get("thread_id") or (c or {}).get("thread_id") or "")
    if not thread_id:
        raise ValueError("thread_id is required")
    deleted = forum_service.delete_thread(thread_id)
    if not deleted:
        raise KeyError(f"Forum thread with ID {thread_id} not found")
    return {"thread_id": thread_id, "deleted": True}


async def operator_mode_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Update an operator's dispatch mode (IN_PROCESS vs HTTP_REMOTE) — ADMIN orchestration."""
    from src.domains.orchestration.models import OperatorModeUpdateRequest
    req = OperatorModeUpdateRequest(**p)
    res = orchestration_service.update_operator_mode(req)
    return res.model_dump()


# ==========================================
# Orchestration Catalog (三层编排资产目录：算子/子图/场景 + 排他锁)
# ==========================================
def _actor_display_name(uid: str) -> str:
    """Resolve the operator's display name for lock-holder visibility (展示锁定人)."""
    if not uid:
        return ""
    try:
        profile = user_service.get_profile(uid=uid)
        if profile and getattr(profile, "nickname", ""):
            return str(profile.nickname)
    except Exception:
        pass
    return uid


def catalog_operators_list_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """List the managed operator catalog (builtin + custom) with lock status (公开只读)."""
    from src.domains.orchestration.catalog import catalog_service
    rows = [o.model_dump() for o in catalog_service.list_operators()]
    return {"operators": rows, "total": len(rows)}


def catalog_operator_detail_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Fetch one operator asset with its full version history (公开只读)."""
    from src.domains.orchestration.catalog import catalog_service
    name = str((p or {}).get("name") or "")
    if not name:
        raise ValueError("name is required")
    return catalog_service.get_operator(name).model_dump()


def catalog_subgraphs_list_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """List all subgraph assets with lock status (公开只读)."""
    from src.domains.orchestration.catalog import catalog_service
    rows = [s.model_dump() for s in catalog_service.list_subgraphs()]
    return {"subgraphs": rows, "total": len(rows)}


def catalog_subgraph_detail_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Fetch one subgraph asset with its version history and compiled graphs (公开只读)."""
    from src.domains.orchestration.catalog import catalog_service
    code = str((p or {}).get("code") or "")
    if not code:
        raise ValueError("code is required")
    return catalog_service.get_subgraph(code).model_dump()


def catalog_scenarios_list_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """List managed scenarios plus read-only runtime pipelines with lock status (公开只读)."""
    from src.domains.orchestration.catalog import catalog_service
    rows = catalog_service.list_scenarios()
    return {"scenarios": rows, "total": len(rows)}


def catalog_scenario_detail_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Fetch one scenario (managed or runtime) with versions / runtime topology (公开只读)."""
    from src.domains.orchestration.catalog import catalog_service
    code = str((p or {}).get("code") or "")
    if not code:
        raise ValueError("code is required")
    return catalog_service.get_scenario(code)


def catalog_locks_list_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """List every active exclusive edit lock with holder info (公开只读，展示锁定人)."""
    from src.domains.orchestration.locks import lock_manager
    locks = [lk.model_dump() for lk in lock_manager.list_active()]
    return {"locks": locks, "total": len(locks)}


async def catalog_lock_acquire_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Acquire (or heartbeat-renew) the exclusive edit lock for one catalog asset."""
    from src.domains.orchestration.locks import (
        DEFAULT_TTL_SECONDS,
        LockConflictError,
        conflict_message,
        lock_manager,
    )

    ctx = c or {}
    uid = str(ctx.get("user_id") or "")
    if not uid:
        raise PermissionError("请先登录后再获取编辑锁")
    raw_ttl = (p or {}).get("ttl_seconds")
    try:
        lock = lock_manager.acquire(
            entity_type=str((p or {}).get("entity_type") or ""),
            entity_key=str((p or {}).get("entity_key") or ""),
            holder_id=uid,
            holder_name=_actor_display_name(uid),
            ttl_seconds=int(raw_ttl) if raw_ttl else DEFAULT_TTL_SECONDS,
        )
    except LockConflictError as exc:
        raise PermissionError(conflict_message(exc)) from exc
    return lock.model_dump()


async def catalog_lock_release_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Release an edit lock (holder always; others need ADMIN force)."""
    from src.domains.orchestration.locks import LockConflictError, conflict_message, lock_manager

    ctx = c or {}
    uid = str(ctx.get("user_id") or "")
    if not uid:
        raise PermissionError("请先登录后再释放编辑锁")
    is_admin = str(ctx.get("user_role") or "").upper() == "ADMIN"
    force = bool((p or {}).get("force")) and is_admin
    try:
        released = lock_manager.release(
            entity_type=str((p or {}).get("entity_type") or ""),
            entity_key=str((p or {}).get("entity_key") or ""),
            holder_id=uid,
            force=force,
        )
    except LockConflictError as exc:
        raise PermissionError(conflict_message(exc)) from exc
    return {"released": released, "forced": force}


async def catalog_write_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Execute one catalog mutation via the OPC_ORCHESTRATION_CATALOG_PIPELINE DAG.

    写走 DAG：guard（动作/身份）→ persist（排他锁校验 + 变更）→ telemetry。
    引擎会把节点异常压平成字符串，这里把 LOCKED / UNLOCKED / UNAUTHORIZED
    前缀还原成语义化错误。
    """
    from src.domains.orchestration.locks import humanize_lock_error

    # 写走 DAG：guard（动作/身份）→ persist（排他锁校验 + 变更）→ telemetry。
    # ensure_catalog_pipeline 幂等确保元管线已注册（catalog 模块可能懒加载）。
    from src.domains.orchestration.catalog import ensure_catalog_pipeline

    ensure_catalog_pipeline()

    action = str((p or {}).get("action") or "")
    ctx = dict(c or {})
    uid = str(ctx.get("user_id") or "")
    if uid:
        ctx.setdefault("user_name", _actor_display_name(uid))

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_ORCHESTRATION_CATALOG_PIPELINE",
            version="v1.0.0",
            inputs={"action": action, "payload": (p or {}).get("payload") or {}},
            context=ctx,
        )
    )
    if res.status != "SUCCESS":
        message = res.error_message or "Orchestration catalog pipeline failed"
        hint = humanize_lock_error(message)
        if hint:
            raise PermissionError(hint)
        # 剥掉执行引擎附加的英文节点前缀，把校验原文（中文）交给前端展示
        for prefix in ("Node step_persist execution error: ", "Node step_guard execution error: ", "Guard check failed: "):
            if message.startswith(prefix):
                message = message[len(prefix):]
                break
        raise ValueError(message)
    return res.final_output.get("catalog_result") or res.final_output


async def framework_hot_reload_status_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """Introspection for file sensing watcher and staged/activated code versions."""
    from src.core.microkernel.watcher import hot_reload_engine
    return hot_reload_engine.get_status()


async def framework_hot_reload_scan_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """Actively trigger a scan for file additions, modifications, and deletions."""
    from src.core.microkernel.watcher import hot_reload_engine
    changes = hot_reload_engine.scan_changes()
    return {
        "status": "ok",
        "newly_detected_count": len(changes),
        "staged_count": len(hot_reload_engine._staged_changes),
        "detected_changes": [ch.model_dump() for ch in changes],
    }


async def framework_hot_reload_activate_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """Atomically load staged python changes into memory for the target version."""
    from src.core.microkernel.watcher import hot_reload_engine
    target_version = (p or {}).get("version", "v1.0.0")
    file_paths = (p or {}).get("file_paths")
    return hot_reload_engine.activate_version(
        target_version=target_version,
        file_paths=file_paths,
        reload_gateway_routes=True,
    )


async def framework_gateway_reload_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """Reload routes, version policies, and activate pending modules."""
    from src.core.microkernel.watcher import hot_reload_engine
    from src.core.gateway import register_default_scenario_routes
    from src.core.config import settings
    target_ver = (p or {}).get("version") or getattr(settings, "app_version", "v1.0.0")
    activation_res = hot_reload_engine.activate_version(
        target_version=target_ver,
        reload_gateway_routes=False,
    )
    count = register_default_scenario_routes()
    return {
        "status": "ok",
        "reloaded_routes_count": count,
        "hot_reload": activation_res,
    }


async def gateway_rules_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    """List all registered scenario routing rules across business domains."""
    from src.core.gateway.router import scenario_router
    return [r.model_dump() for r in scenario_router.list_rules()]


async def forum_semantic_search_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes NLP and vector semantic similarity search for forum threads."""
    from src.core.rag.service import forum_rag_service
    query = (p or {}).get("query") or (p or {}).get("search") or ""
    category_code = (p or {}).get("category_code") or (p or {}).get("category")
    top_k = int((p or {}).get("top_k", 20))
    if not query.strip():
        return {"status": "SUCCESS", "query": "", "total": 0, "items": []}
    items = await forum_rag_service.search_threads(query=query, top_k=top_k, category_code=category_code)
    return {
        "status": "SUCCESS",
        "query": query,
        "category_code": category_code or "ALL",
        "total": len(items),
        "items": items,
    }


async def content_interaction_toggle_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Toggle one unified interaction (LIKE / FAVORITE / LOVE / DISLIKE) for the caller."""
    from src.domains.interactions.service import content_interaction_service

    ctx = c or {}
    user_id = ctx.get("user_id", "")
    if not user_id:
        raise PermissionError("请先登录创客账号后再进行互动")
    payload = p or {}
    result = content_interaction_service.toggle(
        user_id=str(user_id),
        target_type=payload.get("target_type", ""),
        target_id=str(payload.get("target_id", "")),
        kind=payload.get("kind", ""),
        target_title=payload.get("target_title"),
    )
    # 积分联动：点赞/收藏/喜欢/踩都走同一条幂等键；取消互动反向冲销。
    event_code = f"RECEIVE_{result.kind}"
    idem = f"interaction:{event_code}:{user_id}:{result.target_type}:{result.target_id}"
    if result.active:
        await _award_loyalty(
            event_code=event_code,
            user_id="",
            actor_id=str(user_id),
            target_type=result.target_type,
            target_id=result.target_id,
            context=c,
            idempotency_key=idem,
        )
    else:
        await _revoke_loyalty(
            event_code=event_code,
            target_type=result.target_type,
            target_id=result.target_id,
            context=c,
            idempotency_key=idem,
            actor_id=str(user_id),
        )
    return result.model_dump()


async def content_interaction_rate_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Submit / update the caller's 1-5 star rating for a public content target."""
    from src.domains.interactions.service import content_interaction_service

    ctx = c or {}
    user_id = ctx.get("user_id", "")
    if not user_id:
        raise PermissionError("请先登录创客账号后再进行打分")
    payload = p or {}
    result = content_interaction_service.rate(
        user_id=str(user_id),
        target_type=payload.get("target_type", ""),
        target_id=str(payload.get("target_id", "")),
        score=int(payload.get("score", 0) or 0),
    )
    return result.model_dump()


async def content_interactions_state_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Batch-read interaction counters and the caller's own toggle state."""
    from src.domains.interactions.service import content_interaction_service

    ctx = c or {}
    payload = p or {}
    targets = payload.get("targets") or []
    if not isinstance(targets, list):
        raise ValueError("targets must be a list")
    return content_interaction_service.batch_state(ctx.get("user_id", ""), targets[:200])


async def content_interactions_mine_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Return the caller's own likes, favorites, loves and comments."""
    from src.domains.interactions.service import content_interaction_service

    ctx = c or {}
    return content_interaction_service.mine(str(ctx.get("user_id", "") or "")).model_dump()


async def content_comments_list_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """List comments for one public content target (public read)."""
    from src.domains.interactions.service import content_interaction_service

    payload = p or {}
    result = content_interaction_service.list_comments(
        payload.get("target_type", ""),
        str(payload.get("target_id", "")),
    )
    return result.model_dump()


async def content_comments_create_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Create a comment via the unified comment publish DAG."""
    inputs = dict(p or {})
    inputs["_publish_metric"] = "content.comment.created"

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Content comment pipeline failed"
        raise ValueError(error_msg)
    created = res.final_output.get("created_comment") or res.final_output
    if isinstance(created, dict):
        comment_id = created.get("id") or res.final_output.get("comment_id")
        commenter = created.get("author_id") or (c or {}).get("user_id", "")
        target_type = created.get("target_type") or inputs.get("target_type", "")
        target_id = created.get("target_id") or inputs.get("target_id", "")
        if comment_id and len(str(created.get("content") or "")) >= 15:
            await _award_loyalty(
                "RECEIVE_COMMENT", "", str(commenter), str(target_type), str(target_id), c,
                f"comment:receive:{comment_id}",
            )
            await _award_loyalty(
                "COMMENT_CREATED", str(commenter), str(commenter), str(target_type), str(target_id), c,
                f"comment:create:{comment_id}",
            )
    return created


async def content_comments_delete_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Delete a comment (author only; admins bypass ownership)."""
    from src.domains.interactions.service import content_interaction_service

    ctx = c or {}
    user_id = ctx.get("user_id", "")
    if not user_id:
        raise PermissionError("请先登录创客账号后再操作")
    payload = p or {}
    comment_id = payload.get("comment_id") or payload.get("id")
    if not comment_id:
        raise ValueError("comment_id is required")
    ok = content_interaction_service.delete_comment(
        user_id=str(user_id),
        comment_id=str(comment_id),
        is_admin=str(ctx.get("user_role", "")).upper() == "ADMIN",
    )
    if ok:
        await _revoke_loyalty("RECEIVE_COMMENT", "", "", c, f"comment:receive:{comment_id}", actor_id=str(user_id))
        await _revoke_loyalty("COMMENT_CREATED", "", "", c, f"comment:create:{comment_id}", actor_id=str(user_id))
    return {"deleted": bool(ok), "comment_id": str(comment_id)}


async def product_semantic_search_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes NLP and vector semantic similarity search for showcase products."""
    from src.core.rag.service import product_rag_service
    query = (p or {}).get("query") or (p or {}).get("search") or ""
    category = (p or {}).get("category")
    top_k = int((p or {}).get("top_k", 20))
    if not query.strip():
        return {"status": "SUCCESS", "query": "", "total": 0, "items": []}
    items = await product_rag_service.search_products(query=query, top_k=top_k, category=category)
    return {
        "status": "SUCCESS",
        "query": query,
        "category": category or "ALL",
        "total": len(items),
        "items": items,
    }






# ---------------------------------------------------------------------------
# Loyalty / membership / redemption adapters
# ---------------------------------------------------------------------------

_LOYALTY_REASON_TEXT = {
    "missing_user": "请先登录创客账号",
    "rule_disabled": "该积分规则暂未开放",
    "rule_zero_points": "该行为不计积分",
    "official_account": "官方账号不参与积分激励",
    "self_interaction": "自己不能给自己的内容刷互动积分",
    "duplicate": "该笔积分已入账，请勿重复提交",
    "pair_daily_cap": "今日与该创客的互动计分已达上限",
    "daily_cap_reached": "今日积分获取已达上限，明天再来",
    "reputation_blocked": "当前信誉分不足以获得互动积分",
    "plan_not_found": "会员套餐不存在",
    "insufficient_points": "晨光积分不足",
    "item_unavailable": "该兑换商品已下架",
    "out_of_stock": "该商品库存不足",
    "address_required": "实物兑换需要填写收货地址",
    "per_user_limit": "已达到该商品的兑换上限",
    "debt_pending": "存在待补扣积分，暂时无法兑换",
    "higher_tier_active": "当前已有更高档会员权益，无需降级兑换",
}


def _loyalty_uid(c: Dict[str, Any] = None, payload: Dict[str, Any] = None) -> str:
    ctx = c or {}
    return str(ctx.get("user_id") or (payload or {}).get("user_id") or "")


async def loyalty_account_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    return loyalty_service.get_account(uid).model_dump()


async def loyalty_ledger_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    payload = p or {}
    return loyalty_service.list_ledger(
        uid=uid,
        limit=int(payload.get("limit", 50) or 50),
        offset=int(payload.get("offset", 0) or 0),
        event_code=str(payload.get("event_code") or ""),
    ).model_dump()


async def loyalty_rules_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    return loyalty_service.list_rules().model_dump()


async def loyalty_membership_plans_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    membership = loyalty_service.get_membership(uid) if uid else None
    plans = loyalty_service.list_plans(membership.tier if membership else "STANDARD")
    return {
        "items": [plan.model_dump() for plan in plans],
        "current_tier": membership.tier if membership else "STANDARD",
        "current_tier_name": membership.tier_name if membership else "标准创客",
    }


async def loyalty_membership_me_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    return loyalty_service.get_membership(uid).model_dump()


async def loyalty_membership_subscribe_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    from src.domains.loyalty.pipelines import SUBSCRIBE_PIPELINE

    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    payload = p or {}
    out = await _run_loyalty_pipeline(
        SUBSCRIBE_PIPELINE,
        {
            "plan_code": payload.get("plan_code", ""),
            "pay_method": payload.get("pay_method", "POINTS"),
            "idempotency_key": payload.get("idempotency_key"),
        },
        c,
    )
    if not out.get("loyalty_subscribed"):
        reason = str(out.get("loyalty_reason") or "")
        raise ValueError(_LOYALTY_REASON_TEXT.get(reason) or reason or "会员开通失败")
    return out


async def loyalty_membership_auto_renew_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    return loyalty_service.set_auto_renew(uid, bool((p or {}).get("enabled", False))).model_dump()


async def loyalty_rewards_items_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    account = loyalty_service.get_account(uid) if uid else None
    return {
        "items": [item.model_dump() for item in loyalty_service.list_items(uid)],
        "balance": account.balance if account else 0,
    }


async def loyalty_rewards_redeem_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    from src.domains.loyalty.pipelines import REDEEM_PIPELINE

    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    payload = p or {}
    out = await _run_loyalty_pipeline(
        REDEEM_PIPELINE,
        {
            "item_code": payload.get("item_code", ""),
            "qty": int(payload.get("qty", 1) or 1),
            "address": payload.get("address"),
            "idempotency_key": payload.get("idempotency_key"),
        },
        c,
    )
    if not out.get("loyalty_redeemed"):
        reason = str(out.get("loyalty_reason") or "")
        raise ValueError(_LOYALTY_REASON_TEXT.get(reason) or reason or "兑换失败")
    return out


async def loyalty_rewards_orders_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    uid = _loyalty_uid(c, p)
    if not uid:
        raise PermissionError("请先登录创客账号")
    return loyalty_service.list_orders(uid).model_dump()


async def loyalty_content_read_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Track a content detail view and credit the author a tiny read reward.

    Guests are silently ignored (reading must never require login). Dedup is
    per viewer + content + day, so refreshing a detail page cannot farm points.
    """
    from src.domains.loyalty.pipelines import AWARD_PIPELINE

    uid = _loyalty_uid(c, p)
    payload = p or {}
    target_type = str(payload.get("target_type") or "").upper()
    target_id = str(payload.get("target_id") or "")
    if not uid or not target_type or not target_id:
        return {"read_tracked": False, "reason": "guest_or_missing_target"}
    day = datetime.now(timezone.utc).date().isoformat()
    out = await _run_loyalty_pipeline(
        AWARD_PIPELINE,
        {
            "event_code": "RECEIVE_READ",
            "actor_id": uid,
            "target_type": target_type,
            "target_id": target_id,
            "idempotency_key": f"read:{uid}:{target_type}:{target_id}:{day}",
        },
        c,
    )
    return {
        "read_tracked": True,
        "awarded": bool(out.get("loyalty_awarded")),
        "delta": int(out.get("delta", 0) or 0),
        "reason": out.get("loyalty_reason", ""),
    }


async def loyalty_admin_grant_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Admin-only audited points adjustment (补发 / 扣回)."""
    payload = p or {}
    return loyalty_service.admin_adjust(
        uid=str(payload.get("uid") or ""),
        delta=int(payload.get("delta", 0) or 0),
        reason=str(payload.get("reason") or ""),
        operator_id=str((c or {}).get("user_id") or ""),
    )
