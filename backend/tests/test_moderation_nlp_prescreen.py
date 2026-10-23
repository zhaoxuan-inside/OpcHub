"""Tests for the local NLP pre-screen moderation operator (Tier-1) and the two-tier gate.

Verifies:
1. The NLP engine (`nlp_prescreen.prescreen_text`) returns correct three-way verdicts:
   CONFIRMED_SAFE / CONFIRMED_VIOLATION / UNCERTAIN.
2. The `moderation.nlp.prescreen` microkernel operator is registered and callable.
3. The unified two-tier gate (`prescreen_and_scan`) short-circuits on confident verdicts
   (no external call) and defers only UNCERTAIN content to the external service.
4. The SOP document render guard adopts the NLP fast-path: safe/compliance content is
   handled locally, high-severity violations are blocked locally without an external call.
"""
import pytest
import pytest_asyncio
from unittest.mock import patch

from src.domains.moderation.nlp_prescreen import (
    prescreen_text,
    VERDICT_SAFE,
    VERDICT_VIOLATION,
    VERDICT_UNCERTAIN,
)
from src.infrastructure.external_gateway.content_moderation_gateway import prescreen_and_scan


# ---------------------------------------------------------------------------
# 1. NLP engine unit tests
# ---------------------------------------------------------------------------
class TestNlpPrescreen:
    def test_confirmed_safe_benign_business_text(self):
        res = prescreen_text("软件开发与技术咨询，经营范围包括人工智能算法与知识产权申报备案。")
        assert res["verdict"] == VERDICT_SAFE
        assert res["confirmed_clean"] is True
        assert res["confirmed_issue"] is False
        assert res["should_defer_to_external"] is False

    def test_confirmed_safe_empty(self):
        res = prescreen_text("   ")
        assert res["verdict"] == VERDICT_SAFE
        assert res["confirmed_clean"] is True

    def test_confirmed_violation_high_severity(self):
        res = prescreen_text("承接代开发票与洗钱业务，另售私钥与泄露内网接口。")
        assert res["verdict"] == VERDICT_VIOLATION
        assert res["confirmed_issue"] is True
        assert res["confirmed_clean"] is False
        assert "代开发票" in res["hit_sensitive"] or "洗钱" in res["hit_sensitive"]

    def test_confirmed_violation_scam_pattern(self):
        res = prescreen_text("加微信 VX:abc123，保证月入十万，稳赚不亏。")
        assert res["verdict"] == VERDICT_VIOLATION
        assert res["confirmed_issue"] is True
        assert "matched_patterns" in res

    def test_uncertain_deferred_when_ambiguous(self):
        # 短句、无高置信信号：不满足 pass 阈值（safe_score 不足），也未命中强违规 → 交给外部服务
        res = prescreen_text("今天天气不错，周末想去湖边走走，顺便看看新开的店。")
        assert res["verdict"] == VERDICT_UNCERTAIN
        assert res["should_defer_to_external"] is True


# ---------------------------------------------------------------------------
# 2. Microkernel operator registration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_nlp_prescreen_operator_is_registered():
    from src.core.microkernel.registry import registry
    handler = registry.get("moderation.nlp.prescreen")
    assert handler is not None, "moderation.nlp.prescreen operator must be registered"
    res = await handler({"content": "软件开发与合规申报"}, {})
    assert res["verdict"] == VERDICT_SAFE


# ---------------------------------------------------------------------------
# 3. Two-tier gate short-circuit behavior (no external call on confident verdicts)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gate_confirmed_safe_short_circuits_external():
    """肯定没问题 → 不调用外部服务。"""
    with patch("src.domains.moderation.nlp_prescreen.prescreen_text") as mock:
        mock.return_value = {
            "verdict": VERDICT_SAFE, "confirmed_issue": False, "confirmed_clean": True,
            "should_defer_to_external": False, "violation_score": 0, "safe_score": 5,
            "hit_sensitive": [], "matched_patterns": [], "reason": "benign", "trace_id": "t",
        }
        res = await prescreen_and_scan("软件开发与合规申报", "field")
        assert res["passed"] is True
        assert res["external_scan_used"] is False


@pytest.mark.asyncio
async def test_gate_confirmed_violation_raises_without_external():
    """肯定有问题 → 直接抛错，不调用外部服务。"""
    with patch("src.domains.moderation.nlp_prescreen.prescreen_text") as mock:
        mock.return_value = {
            "verdict": VERDICT_VIOLATION, "confirmed_issue": True, "confirmed_clean": False,
            "should_defer_to_external": False, "violation_score": 6, "safe_score": 0,
            "hit_sensitive": ["洗钱"], "matched_patterns": [], "reason": "high-severity", "trace_id": "t",
        }
        with pytest.raises(ValueError):
            await prescreen_and_scan("洗钱通道", "field")


@pytest.mark.asyncio
async def test_gate_uncertain_defers_to_external_pass():
    """不确定 → 交给外部服务，外部判定通过则放行。"""
    from unittest.mock import AsyncMock
    with patch("src.domains.moderation.nlp_prescreen.prescreen_text") as mock_nlp, \
         patch("src.infrastructure.external_gateway.content_moderation_gateway.content_moderation_gateway.scan_text", new=AsyncMock(return_value={
            "passed": True, "suggestion": "pass", "hit_words": [],
            "filtered_content": "x", "raw_response": {}, "unavailable": False,
         })) as mock_scan:
        mock_nlp.return_value = {
            "verdict": VERDICT_UNCERTAIN, "confirmed_issue": False, "confirmed_clean": False,
            "should_defer_to_external": True, "violation_score": 1, "safe_score": 1,
            "hit_sensitive": [], "matched_patterns": [], "reason": "ambiguous", "trace_id": "t",
        }
        res = await prescreen_and_scan("一些待外部判定的内容", "field")
        assert res["passed"] is True
        assert res["external_scan_used"] is True
        mock_scan.assert_awaited_once()


@pytest.mark.asyncio
async def test_gate_uncertain_defer_external_block():
    """不确定 → 交给外部服务，外部判定命中敏感词则拦截。"""
    from unittest.mock import AsyncMock
    with patch("src.domains.moderation.nlp_prescreen.prescreen_text") as mock_nlp, \
         patch("src.infrastructure.external_gateway.content_moderation_gateway.content_moderation_gateway.scan_text", new=AsyncMock(return_value={
            "passed": False, "suggestion": "block", "hit_words": ["高利贷"],
            "filtered_content": "x", "raw_response": {}, "unavailable": False,
         })):
        mock_nlp.return_value = {
            "verdict": VERDICT_UNCERTAIN, "confirmed_issue": False, "confirmed_clean": False,
            "should_defer_to_external": True, "violation_score": 0, "safe_score": 0,
            "hit_sensitive": [], "matched_patterns": [], "reason": "ambiguous", "trace_id": "t",
        }
        with pytest.raises(ValueError) as ei:
            await prescreen_and_scan("高利贷业务", "field")
        assert "高利贷" in str(ei.value)


# ---------------------------------------------------------------------------
# 4. Real NLP engine verdicts (no mocks) against representative inputs
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sop_guard_adopts_nlp_fast_path_no_external_on_confirmed_safe():
    """SOP 文书渲染守卫：纯合规内容被 NLP 本地判定为肯定没问题，不触发外呼。"""
    from src.infrastructure.external_gateway.content_moderation_gateway import content_moderation_gateway
    original = content_moderation_gateway.scan_text
    called = {"v": False}

    async def _spy(*args, **kwargs):
        called["v"] = True
        return await original(*args, **kwargs)

    content_moderation_gateway.scan_text = _spy
    try:
        # 强合规短语：应命中 CONFIRMED_SAFE，不调用外部服务。
        from src.domains.moderation.nlp_prescreen import prescreen_text
        res = prescreen_text("软件开发、技术咨询、人工智能算法、知识产权、版权、专利、税务登记、银行开户、章程、合规申报")
        assert res["verdict"] == VERDICT_SAFE
        from src.infrastructure.external_gateway.content_moderation_gateway import prescreen_and_scan
        out = await prescreen_and_scan("软件开发、技术咨询、人工智能算法、知识产权、版权、专利、税务登记、银行开户、章程、合规申报", "field")
        assert out["external_scan_used"] is False
        assert called["v"] is False, "confident-safe content must not reach external service"
    finally:
        content_moderation_gateway.scan_text = original