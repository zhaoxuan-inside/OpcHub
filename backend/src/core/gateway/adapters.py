"""Generic adapters for domain services referenced by gateway routes configuration."""
import time
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


async def demand_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for enterprise outsourcing demand publishing."""
    inputs = dict(p)
    if "demand_payload" in inputs and isinstance(inputs["demand_payload"], dict):
        inputs.update(inputs["demand_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Demand publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_demand") or res.final_output


async def demand_bid_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for maker demand bidding."""
    inputs = dict(p)
    if "bid_payload" in inputs and isinstance(inputs["bid_payload"], dict):
        inputs.update(inputs["bid_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_BID_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Demand bidding pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_bid") or res.final_output


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

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Perk publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_perk") or res.final_output


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
    
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_THREAD_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum thread publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_thread") or res.final_output


async def forum_comment_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for forum comment publishing."""
    inputs = dict(p)
    if "comment_payload" in inputs and isinstance(inputs["comment_payload"], dict):
        inputs.update(inputs["comment_payload"])
    
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_COMMENT_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum comment publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_comment") or res.final_output


async def product_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for product showcase publishing."""
    inputs = dict(p)
    if "product_payload" in inputs and isinstance(inputs["product_payload"], dict):
        inputs.update(inputs["product_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PRODUCT_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Product showcase publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_product") or res.final_output


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

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_POLICY_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Policy publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_policy") or res.final_output


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
    )
    profile = await user_service.update_profile(req=req, token=token)
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
    return res.final_output.get("dag_record") or res.final_output


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


async def forum_upvote_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Toggle an upvote on a forum thread or comment (authenticated maker)."""
    from src.domains.forum.service import forum_service
    user_id = p.get("user_id") or (c or {}).get("user_id") or ""
    res = forum_service.toggle_upvote(user_id, p.get("target_type", "THREAD"), p.get("target_id", ""))
    return res.model_dump()


async def forum_bookmark_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Toggle a bookmark on a forum thread (authenticated maker)."""
    from src.domains.forum.service import forum_service
    user_id = p.get("user_id") or (c or {}).get("user_id") or ""
    res = forum_service.toggle_bookmark(user_id, p.get("thread_id", ""), p.get("folder_name", "默认收藏夹"))
    return res.model_dump()


async def operator_mode_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Update an operator's dispatch mode (IN_PROCESS vs HTTP_REMOTE) — ADMIN orchestration."""
    from src.domains.orchestration.models import OperatorModeUpdateRequest
    req = OperatorModeUpdateRequest(**p)
    res = orchestration_service.update_operator_mode(req)
    return res.model_dump()


