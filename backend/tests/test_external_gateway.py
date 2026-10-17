import pytest
from src.core.telemetry import current_trace_id
from src.infrastructure.external_gateway import (
    ai_gateway,
    payment_gateway,
    sms_auth_gateway,
    gov_crawler_gateway,
    BaseOutboundClient,
)


@pytest.mark.asyncio
async def test_base_outbound_client_trace_injection():
    """Verify all outbound requests automatically inherit current context TraceID."""
    test_trace_id = "trace-outbound-test-9999"
    current_trace_id.set(test_trace_id)

    client = BaseOutboundClient(service_name="TEST_SERVICE", mock_mode=False)
    res = await client.execute_request("POST", "/test-endpoint")

    assert res["status"] == "SUCCESS"
    assert res["trace_id"] == test_trace_id
    assert res["headers_sent"]["X-Trace-ID"] == test_trace_id
    assert "OpcHub-Gateway/TEST_SERVICE" in res["headers_sent"]["User-Agent"]


@pytest.mark.asyncio
async def test_ai_gateway_charter_generation():
    """Verify AI gateway properly formats charter generation request."""
    res = await ai_gateway.generate_charter_text("杭州智创星云科技有限公司", "人工智能算力调度与软件开发")
    assert res["status"] == "SUCCESS"
    assert res["model"] == "gemini-2.5-pro"
    assert "杭州智创星云科技有限公司章程" in res["charter_text"]
    assert res["tokens_consumed"] > 0


@pytest.mark.asyncio
async def test_payment_gateway_split_order():
    """Verify payment gateway enforces anti-fund-pooling split escrow."""
    res = await payment_gateway.create_split_order(
        order_id="ord_20261017_01",
        amount_cny=1000.0,
        merchant_account="merchant_wx_01",
        maker_account="maker_wx_02"
    )
    assert res["status"] == "SUCCESS"
    assert res["escrow_channel"] == "LICENSED_WECHAT_SPLIT"
    assert res["maker_share"] == 950.0
    assert res["platform_fee"] == 50.0
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
    """Verify government crawler fetches open data safely."""
    res = await gov_crawler_gateway.fetch_public_policy("浙江省经信厅", "浙经信技术2026_01")
    assert res["status"] == "SUCCESS"
    assert res["is_classified"] is False
    assert "gov.cn" in res["source_url"]
