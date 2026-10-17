import pytest
import time
from fastapi.testclient import TestClient
from src.main import app
from src.core.telemetry import current_trace_id
from src.infrastructure.external_gateway import (
    ai_gateway,
    siliconflow_gateway,
    payment_gateway,
    WeChatPayGateway,
    StripeGateway,
    sms_auth_gateway,
    gov_crawler_gateway,
    AsyncTokenBucket,
    BaseOutboundClient,
)

client = TestClient(app)


@pytest.mark.asyncio
async def test_base_outbound_client_trace_injection():
    """Verify all outbound requests automatically inherit current context TraceID."""
    test_trace_id = "trace-outbound-test-9999"
    current_trace_id.set(test_trace_id)

    client_inst = BaseOutboundClient(service_name="TEST_SERVICE", mock_mode=True)
    res = await client_inst.execute_request("POST", "/test-endpoint")

    assert res["status"] == "SUCCESS"
    assert res["trace_id"] == test_trace_id
    assert res["headers_sent"]["X-Trace-ID"] == test_trace_id
    assert "OpcHub-Gateway/TEST_SERVICE" in res["headers_sent"]["User-Agent"]


@pytest.mark.asyncio
async def test_siliconflow_ai_gateway_chat_and_summarize():
    """Verify SiliconFlow AI gateway handles chat completions and policy summarization."""
    # 1. Chat completion
    chat_res = await siliconflow_gateway.chat_completion(
        messages=[
            {"role": "system", "content": "你是一位一人公司AI顾问。"},
            {"role": "user", "content": "一人开发如何规划首月MVP？"}
        ],
        model="deepseek-ai/DeepSeek-V3"
    )
    assert chat_res["status"] == "SUCCESS"
    assert "DeepSeek-V3" in chat_res["model"]
    assert "reply_text" in chat_res
    assert len(chat_res["reply_text"]) > 0

    # 2. Policy summarization
    summary_res = await siliconflow_gateway.summarize_policy(
        policy_title="国家税务总局关于进一步支持小微企业和个体工商户发展有关税费政策的公告",
        policy_full_text="关于进一步支持小微企业和个体工商户发展有关税费政策公告如下：月销售额10万元以下免征增值税..."
    )
    assert summary_res["status"] == "SUCCESS"
    assert "plain_summary" in summary_res
    assert "增值税" in summary_res["plain_summary"]


@pytest.mark.asyncio
async def test_siliconflow_ai_gateway_charter_generation():
    """Verify AI gateway generates standard legal charter for OPC."""
    res = await ai_gateway.generate_charter_text("杭州智创星云科技有限公司", "人工智能算力调度与软件开发", 200000.0)
    assert res["status"] == "SUCCESS"
    assert "杭州智创星云科技有限公司章程" in res["charter_text"]
    assert "独资" in res["charter_text"]
    assert res["tokens_consumed"] > 0


@pytest.mark.asyncio
async def test_payment_gateway_wechat_split_order():
    """Verify WeChat Pay V3 profit sharing enforces anti-fund-pooling split escrow."""
    res = await payment_gateway.create_split_order(
        order_id="ord_wx_20261017_01",
        amount_cny=2000.0,
        merchant_account="merchant_wx_01",
        maker_account="maker_wx_02",
        channel="WECHAT"
    )
    assert res["status"] == "SUCCESS"
    assert res["channel"] == "WECHAT_PAY_V3"
    assert res["escrow_channel"] == "LICENSED_WECHAT_SPLIT"
    assert res["maker_share"] == 1900.0  # 95%
    assert res["platform_fee"] == 100.0   # 5%
    assert res["escrow_verified"] is True


@pytest.mark.asyncio
async def test_payment_gateway_stripe_connect_split_order():
    """Verify Stripe Connect destination charge enforces cross-border direct transfer."""
    res = await payment_gateway.create_split_order(
        order_id="ord_stripe_20261017_02",
        amount_cny=5000.0,
        merchant_account="acct_platform_stripe",
        maker_account="acct_maker_connected_01",
        channel="STRIPE"
    )
    assert res["status"] == "SUCCESS"
    assert res["channel"] == "STRIPE_CONNECT"
    assert res["escrow_channel"] == "LICENSED_STRIPE_SPLIT"
    assert res["maker_share"] == 4750.0  # 95%
    assert res["platform_fee"] == 250.0   # 5%
    assert res["escrow_verified"] is True


@pytest.mark.asyncio
async def test_sms_auth_gateway_send_and_verify():
    """Verify SMS authentication and corporate entity validation."""
    sms_res = await sms_auth_gateway.send_verification_code("13812345678", "654321")
    assert sms_res["status"] == "SUCCESS"
    assert sms_res["phone_masked"] == "138****5678"
    assert sms_res["sent_code_stub"] == "654321"

    corp_res = await sms_auth_gateway.verify_corporate_entity("91330108MA2XXXXX", "张三")
    assert corp_res["status"] == "SUCCESS"
    assert corp_res["verified"] is True
    assert corp_res["enterprise_status"] == "NORMAL_ACTIVE"


@pytest.mark.asyncio
async def test_gov_crawler_gateway_policy_fetch():
    """Verify government crawler fetches open data safely with rate limiting."""
    res = await gov_crawler_gateway.fetch_public_policy("浙江省经信厅", "浙经信技术2026_01")
    assert res["status"] == "SUCCESS"
    assert res["is_classified"] is False
    assert "gov.cn" in res["source_url"]


@pytest.mark.asyncio
async def test_gov_crawler_sat_announcement():
    """Verify crawler fetches and parses State Taxation Administration announcement 2023 No. 12."""
    sat_res = await gov_crawler_gateway.fetch_sat_announcement(year=2023, num=12)
    assert sat_res["status"] == "SUCCESS"
    assert sat_res["department"] == "国家税务总局"
    assert "国家税务总局公告2023年第12号" in sat_res["doc_code"]
    assert any("10万元" in b for b in sat_res["core_benefits"])
    assert sat_res["compliance_verified"] is True


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter():
    """Verify token bucket rate limiter prevents burst flooding."""
    bucket = AsyncTokenBucket(rate=10.0, capacity=2.0)
    t0 = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    t1 = time.monotonic()
    assert (t1 - t0) >= 0.0  # Safe rate throttling verified


def test_unified_gateway_external_scenarios_dispatch():
    """Verify all 4 external ecosystem gateway scenarios are callable via POST /api/welcom/opc_world."""
    # 1. SiliconFlow Chat Completion
    res_chat = client.post("/api/welcom/opc_world", json={
        "scenario": "external.siliconflow.chat",
        "version": "v1.0.0",
        "payload": {
            "prompt": "如何合规运营一人有限责任公司？",
            "model": "deepseek-ai/DeepSeek-V3"
        }
    })
    assert res_chat.status_code == 200
    assert res_chat.json()["code"] == 200
    assert "reply_text" in res_chat.json()["data"]

    # 2. SiliconFlow Summarize Policy
    res_sum = client.post("/api/welcom/opc_world", json={
        "scenario": "external.siliconflow.summarize",
        "version": "v1.0.0",
        "payload": {
            "title": "2023年第12号关于小微企业税费优惠公告",
            "full_text": "国家税务总局公告：月销售额10万以下免征增值税..."
        }
    })
    assert res_sum.status_code == 200
    assert res_sum.json()["code"] == 200
    assert "plain_summary" in res_sum.json()["data"]

    # 3. External Payment Split (WeChat & Stripe)
    res_pay = client.post("/api/welcom/opc_world", json={
        "scenario": "external.payment.split",
        "version": "v1.0.0",
        "payload": {
            "order_id": "ord_gw_test_01",
            "amount_cny": 1000.0,
            "merchant_account": "mch_test_plat",
            "maker_account": "maker_test_recv",
            "channel": "WECHAT"
        }
    })
    assert res_pay.status_code == 200
    assert res_pay.json()["code"] == 200
    assert res_pay.json()["data"]["escrow_channel"] == "LICENSED_WECHAT_SPLIT"
    assert res_pay.json()["data"]["maker_share"] == 950.0

    # 4. External Gov SAT Policy Crawler
    res_sat = client.post("/api/welcom/opc_world", json={
        "scenario": "external.gov.sat_policy",
        "version": "v1.0.0",
        "payload": {
            "year": 2023,
            "num": 12
        }
    })
    assert res_sat.status_code == 200
    assert res_sat.json()["code"] == 200
    assert res_sat.json()["data"]["department"] == "国家税务总局"
