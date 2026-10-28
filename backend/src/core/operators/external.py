"""External I/O operators.

All third-party access is funnelled through the anti-corruption gateways in
``src.infrastructure.external_gateway`` and ``src.core.rag``. Operators only
translate declarative params into gateway calls; no business rule lives here.
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator


@operator("external.ai.chat", category="ADAPTER", description="Chat completion through the AI gateway")
async def ai_chat(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.infrastructure.external_gateway import siliconflow_gateway

    messages = args.get("messages") or params.get("messages")
    if not messages:
        prompt = args.get("prompt") or params.get("prompt") or ""
        messages = [{"role": "user", "content": prompt}]
    result = await siliconflow_gateway.chat_completion(
        messages=messages,
        model=params.get("model") or args.get("model"),
        temperature=float(params.get("temperature", 0.3)),
        max_tokens=int(params.get("max_tokens", 1024)),
    )
    return {"ai": result}


@operator("external.ai.summarize", category="ADAPTER", description="Policy summarisation through the AI gateway")
async def ai_summarize(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.infrastructure.external_gateway import siliconflow_gateway

    result = await siliconflow_gateway.summarize_policy(
        policy_title=str(args.get("title") or params.get("title") or ""),
        policy_full_text=str(args.get("full_text") or params.get("full_text") or ""),
        model=params.get("model"),
    )
    return {"summary": result}


@operator("external.ai.charter", category="ADAPTER", description="Charter drafting through the AI gateway")
async def ai_charter(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.infrastructure.external_gateway import siliconflow_gateway

    result = await siliconflow_gateway.generate_charter_text(
        company_name=str(args.get("company_name") or params.get("company_name") or ""),
        biz_scope=str(args.get("biz_scope") or params.get("biz_scope") or ""),
        registered_capital_cny=float(args.get("registered_capital_cny") or params.get("registered_capital_cny") or 0),
        model=params.get("model"),
    )
    return {"charter": result}


@operator("external.payment.split", category="ADAPTER", description="Create a split payment order")
async def payment_split(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.infrastructure.external_gateway import payment_gateway

    result = await payment_gateway.create_split_order(
        order_id=str(args.get("order_id") or params.get("order_id") or ""),
        amount_cny=float(args.get("amount_cny") or params.get("amount_cny") or 0),
        merchant_account=str(args.get("merchant_account") or params.get("merchant_account") or "mch_opchub_platform"),
        maker_account=str(args.get("maker_account") or params.get("maker_account") or "maker_licensed_escrow"),
        channel=str(params.get("channel") or args.get("channel") or "WECHAT"),
    )
    return {"payment": result}


@operator("external.gov.fetch_announcement", category="ADAPTER", description="Fetch one government announcement")
async def gov_fetch(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.infrastructure.external_gateway import gov_crawler_gateway

    result = await gov_crawler_gateway.fetch_sat_announcement(
        year=int(args.get("year") or params.get("year") or 2023),
        num=int(args.get("num") or params.get("num") or 12),
    )
    return {"announcement": result}


@operator("external.sms.send", category="ADAPTER", description="Send one SMS/verification message")
async def sms_send(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.infrastructure.external_gateway import sms_auth_gateway

    result = await sms_auth_gateway.send_verification_code(
        phone=str(args.get("phone") or params.get("phone") or ""),
        code=str(args.get("code") or params.get("code") or ""),
    )
    return {"sms": result}


@operator("external.rag.policy_search", category="ADAPTER", description="Semantic policy search")
async def rag_policy(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.rag import policy_rag_service

    result = await policy_rag_service.search_policies(
        query=str(args.get("query") or params.get("query") or ""),
        top_k=int(args.get("top_k") or params.get("top_k") or 5),
        region=args.get("region") or params.get("region"),
        category=args.get("category") or params.get("category"),
    )
    return {"results": result}


@operator("external.rag.forum_qa", category="ADAPTER", description="Forum retrieval augmented Q&A")
async def rag_forum(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.rag import forum_rag_service

    result = await forum_rag_service.ask_forum_rag(
        question=str(args.get("question") or params.get("question") or ""),
        top_k=int(args.get("top_k") or params.get("top_k") or 3),
    )
    return {"answer": result}


@operator("external.rag.forum_search", category="ADAPTER", description="Semantic forum thread search")
async def rag_forum_search(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.rag import forum_rag_service

    query = str(args.get("query") or params.get("query") or "")
    if not query.strip():
        return {"results": []}
    result = await forum_rag_service.search_threads(
        query=query,
        top_k=int(args.get("top_k") or params.get("top_k") or 15),
        category_code=args.get("category_code") or params.get("category_code"),
    )
    return {"results": result}


@operator("external.rag.product_search", category="ADAPTER", description="Semantic product search")
async def rag_product(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.rag import product_rag_service

    query = str(args.get("query") or params.get("query") or "")
    if not query.strip():
        return {"results": []}
    result = await product_rag_service.search_products(
        query=query,
        top_k=int(args.get("top_k") or params.get("top_k") or 5),
        category=args.get("category") or params.get("category"),
    )
    return {"results": result}
