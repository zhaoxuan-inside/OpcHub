"""Atomic operators for the loyalty domain.

Every points mutation is expressed as an orchestrated DAG of these operators:

* award:    identity_guard -> event_resolve -> award_guard -> points_settle -> telemetry
* revoke:   identity_guard -> event_resolve -> points_revoke -> telemetry
* redeem:   identity_guard -> redeem_guard -> redeem_settle -> telemetry
* subscribe:identity_guard -> subscribe_guard -> subscribe_settle -> telemetry

Business domains (publish / interaction / read adapters) only emit intents; the
loyalty service remains the single writer of balances.
"""
from __future__ import annotations

from typing import Any, Dict

from src.domains.loyalty.models import AwardDecision
from src.domains.loyalty.service import loyalty_service

KIND_TO_EVENT = {
    "LIKE": "RECEIVE_LIKE",
    "FAVORITE": "RECEIVE_FAVORITE",
    "LOVE": "RECEIVE_LOVE",
    "DISLIKE": "RECEIVE_DISLIKE",
}


def _uid(inputs: Dict[str, Any], context: Dict[str, Any]) -> str:
    return str(
        (context or {}).get("user_id")
        or inputs.get("loyalty_actor_id")
        or inputs.get("actor_id")
        or inputs.get("user_id")
        or ""
    )


def register_loyalty_operators(registry: Any) -> None:
    """Register every loyalty atomic handler into the platform registry."""

    async def loyalty_identity_guard(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        uid = _uid(inputs, context)
        if not uid:
            raise PermissionError("请先登录创客账号后再进行积分操作")
        return {"loyalty_actor_id": uid, "actor_id": uid, "loyalty_identity": True}

    async def loyalty_event_resolve(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        event_code = str(inputs.get("event_code") or "").upper()
        target_type = str(inputs.get("target_type") or "").upper()
        target_id = str(inputs.get("target_id") or "")
        actor_id = str(inputs.get("actor_id") or inputs.get("loyalty_actor_id") or _uid(inputs, context))
        if not event_code:
            kind = str(inputs.get("kind") or "").upper()
            event_code = KIND_TO_EVENT.get(kind, "")
        if not event_code:
            return {"loyalty_allowed": False, "loyalty_reason": "missing_event_code"}

        user_id = str(inputs.get("user_id") or "")
        if event_code.startswith("RECEIVE_") and not user_id:
            user_id = loyalty_service.resolve_target_author(target_type, target_id)
        if not user_id:
            return {
                "loyalty_allowed": False,
                "loyalty_reason": "missing_target_author",
                "event_code": event_code,
                "target_type": target_type,
                "target_id": target_id,
            }
        return {
            "event_code": event_code,
            "user_id": user_id,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "loyalty_event_resolved": True,
        }

    async def loyalty_award_guard(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if inputs.get("loyalty_allowed") is False:
            return {}
        decision = loyalty_service.check_award(
            event_code=str(inputs.get("event_code") or ""),
            uid=str(inputs.get("user_id") or ""),
            actor_id=str(inputs.get("actor_id") or ""),
            target_type=str(inputs.get("target_type") or ""),
            target_id=str(inputs.get("target_id") or ""),
            quantity=int(inputs.get("quantity", 1) or 1),
            idempotency_key=inputs.get("idempotency_key"),
            note=str(inputs.get("note") or ""),
        )
        return {
            "loyalty_allowed": decision.allowed,
            "loyalty_reason": decision.reason,
            "loyalty_decision": decision.model_dump(),
        }

    async def loyalty_points_settle(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not inputs.get("loyalty_allowed"):
            return {
                "loyalty_awarded": False,
                "loyalty_reason": inputs.get("loyalty_reason") or "not_allowed",
                "delta": 0,
            }
        decision = AwardDecision(**dict(inputs.get("loyalty_decision") or {}))
        result = loyalty_service.apply_award(decision)
        return {
            "loyalty_awarded": bool(result.get("awarded")),
            "loyalty_result": result,
            **result,
        }

    async def loyalty_points_settle_compensate(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ledger_id = str(inputs.get("ledger_id") or "")
        ok = loyalty_service.revoke_ledger(ledger_id) if ledger_id else False
        return {"compensated": ok, "ledger_id": ledger_id, "action": "ROLLED_BACK"}

    async def loyalty_points_revoke(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        result = loyalty_service.revoke(
            event_code=str(inputs.get("event_code") or ""),
            uid=str(inputs.get("user_id") or ""),
            actor_id=str(inputs.get("actor_id") or ""),
            target_type=str(inputs.get("target_type") or ""),
            target_id=str(inputs.get("target_id") or ""),
            idempotency_key=inputs.get("idempotency_key"),
        )
        return {
            "loyalty_revoked": bool(result.get("revoked")),
            "loyalty_result": result,
            **result,
        }

    async def loyalty_redeem_guard(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        uid = str(inputs.get("loyalty_actor_id") or _uid(inputs, context))
        decision = loyalty_service.check_redeem(
            uid=uid,
            item_code=str(inputs.get("item_code") or ""),
            qty=int(inputs.get("qty", 1) or 1),
            address=inputs.get("address"),
        )
        item = decision.pop("item", None)
        return {
            "loyalty_redeem_allowed": bool(decision.get("allowed")),
            "loyalty_reason": decision.get("reason", ""),
            "loyalty_redeem_decision": decision,
            "item_code": getattr(item, "code", inputs.get("item_code")),
        }

    async def loyalty_redeem_settle(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not inputs.get("loyalty_redeem_allowed"):
            return {
                "loyalty_redeemed": False,
                "loyalty_reason": inputs.get("loyalty_reason") or "not_allowed",
            }
        uid = str(inputs.get("loyalty_actor_id") or _uid(inputs, context))
        try:
            result = await loyalty_service.redeem(
                uid=uid,
                item_code=str(inputs.get("item_code") or ""),
                qty=int(inputs.get("qty", 1) or 1),
                address=inputs.get("address"),
                idempotency_key=inputs.get("idempotency_key"),
            )
        except ValueError as exc:
            return {"loyalty_redeemed": False, "loyalty_reason": str(exc)}
        order = result.get("order")
        account = result.get("account")
        membership = result.get("membership")
        return {
            "loyalty_redeemed": True,
            "redemption": result,
            "order": order.model_dump() if hasattr(order, "model_dump") else order,
            "account": account.model_dump() if hasattr(account, "model_dump") else account,
            "membership": membership.model_dump() if hasattr(membership, "model_dump") else membership,
            "message": result.get("message", "兑换成功"),
        }

    async def loyalty_subscribe_guard(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        uid = str(inputs.get("loyalty_actor_id") or _uid(inputs, context))
        plan_code = str(inputs.get("plan_code") or "")
        plan = loyalty_service.get_plan(plan_code)
        if not plan:
            return {"loyalty_subscribe_allowed": False, "loyalty_reason": "plan_not_found"}
        current = loyalty_service.get_membership(uid)
        tier_rank = {"PRO": 1, "BLACK_DIAMOND": 2}
        if tier_rank.get(current.tier, 0) > tier_rank.get(plan.tier, 0):
            return {"loyalty_subscribe_allowed": False, "loyalty_reason": "higher_tier_active"}
        method = str(inputs.get("pay_method") or "POINTS").upper()
        if method == "POINTS":
            account = loyalty_service.get_account(uid)
            if account.balance < plan.points_price:
                return {"loyalty_subscribe_allowed": False, "loyalty_reason": "insufficient_points"}
        return {
            "loyalty_subscribe_allowed": True,
            "loyalty_reason": "",
            "plan_code": plan_code,
            "pay_method": method,
        }

    async def loyalty_subscribe_settle(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not inputs.get("loyalty_subscribe_allowed"):
            return {
                "loyalty_subscribed": False,
                "loyalty_reason": inputs.get("loyalty_reason") or "not_allowed",
            }
        uid = str(inputs.get("loyalty_actor_id") or _uid(inputs, context))
        try:
            result = await loyalty_service.subscribe(
                uid=uid,
                plan_code=str(inputs.get("plan_code") or ""),
                pay_method=str(inputs.get("pay_method") or "POINTS"),
                idempotency_key=inputs.get("idempotency_key"),
            )
        except ValueError as exc:
            return {"loyalty_subscribed": False, "loyalty_reason": str(exc)}
        order = result.get("order")
        account = result.get("account")
        membership = result.get("membership")
        return {
            "loyalty_subscribed": True,
            "subscription": result,
            "order": order.model_dump() if hasattr(order, "model_dump") else order,
            "account": account.model_dump() if hasattr(account, "model_dump") else account,
            "membership": membership.model_dump() if hasattr(membership, "model_dump") else membership,
            "message": result.get("message", "会员已开通"),
            "payment_required": bool(result.get("payment_required", False)),
        }

    async def loyalty_telemetry_incr(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        metric = "loyalty.award"
        if inputs.get("loyalty_redeemed"):
            metric = "loyalty.redeem"
        elif inputs.get("loyalty_subscribed"):
            metric = "loyalty.subscribe"
        elif inputs.get("loyalty_revoked"):
            metric = "loyalty.revoke"
        return {
            "loyalty_telemetry": True,
            "metric": metric,
            "delta": int(inputs.get("delta", 0) or 0),
        }

    registry.register(
        "loyalty.identity_guard",
        loyalty_identity_guard,
        domain="loyalty",
        description="积分/会员操作登录身份门禁",
    )
    registry.register(
        "loyalty.event_resolve",
        loyalty_event_resolve,
        domain="loyalty",
        description="解析积分事件码与内容作者归属",
    )
    registry.register(
        "loyalty.award_guard",
        loyalty_award_guard,
        domain="loyalty",
        description="积分获取资格、上限、幂等与防互刷门禁",
    )
    registry.register(
        "loyalty.points_settle",
        loyalty_points_settle,
        domain="loyalty",
        description="积分入账与余额更新算子",
        compensator=loyalty_points_settle_compensate,
    )
    registry.register(
        "loyalty.points_revoke",
        loyalty_points_revoke,
        domain="loyalty",
        description="积分撤销与反向冲销算子",
    )
    registry.register(
        "loyalty.redeem_guard",
        loyalty_redeem_guard,
        domain="loyalty",
        description="积分兑换库存、限购、余额与地址门禁",
    )
    registry.register(
        "loyalty.redeem_settle",
        loyalty_redeem_settle,
        domain="loyalty",
        description="积分扣减、订单创建与会员/实物履约算子",
    )
    registry.register(
        "loyalty.subscribe_guard",
        loyalty_subscribe_guard,
        domain="loyalty",
        description="会员套餐与积分余额门禁",
    )
    registry.register(
        "loyalty.subscribe_settle",
        loyalty_subscribe_settle,
        domain="loyalty",
        description="会员开通、续期与权益同步算子",
    )
    registry.register(
        "loyalty.telemetry.incr",
        loyalty_telemetry_incr,
        domain="loyalty",
        description="积分体系度量打点算子",
    )
