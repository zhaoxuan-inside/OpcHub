"""Integration tests verifying decoupled Aliyun Content Moderation HTTP Mock Server.

Uses centralized mock_data/content_moderation.yaml dataset to verify:
1. Zero hardcoded mock datasets in core business logic.
2. The platform connects to the dedicated HTTP mock service via standard network requests.
3. Live moderation scan correctly allows safe content and blocks prohibited keywords.
4. Dynamic keyword injection via HTTP API is immediately reflected in business guards without code changes.
"""
import pytest
import pytest_asyncio
import httpx

from src.infrastructure.external_gateway.content_moderation_gateway import (
    content_moderation_gateway,
    check_content_safety,
)
from src.core.microkernel.registry import registry
from mock_data.loader import get_moderation_data

MOCK_ENDPOINT = "http://127.0.0.1:8099"


@pytest.mark.asyncio
async def test_mock_server_health_via_http():
    """Verify HTTP mock service is alive and healthy."""
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.get(f"{MOCK_ENDPOINT}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "UP"


@pytest.mark.asyncio
async def test_safe_content_passes_via_http():
    """Verify safe UGC text samples loaded from mock_data pass inspection via HTTP."""
    mod_data = get_moderation_data()
    safe_samples = mod_data["test_cases"]["safe_samples"]

    for safe_text in safe_samples:
        result = await content_moderation_gateway.scan_text(safe_text)
        assert result["passed"] is True
        assert result["suggestion"] == "pass"
        assert result["hit_words"] == []
        assert result["filtered_content"] == safe_text

        # Helper function should not raise error
        await check_content_safety(safe_text, field_name="test_field")


@pytest.mark.asyncio
async def test_prohibited_content_blocked_via_http():
    """Verify prohibited samples loaded from mock_data are blocked via HTTP."""
    mod_data = get_moderation_data()
    prohibited_samples = mod_data["test_cases"]["prohibited_samples"]

    for item in prohibited_samples:
        bad_text = item["text"]
        expected_hits = item["expected_hits"]

        result = await content_moderation_gateway.scan_text(bad_text)
        assert result["passed"] is False
        assert result["suggestion"] == "block"
        for kw in expected_hits:
            assert kw in result["hit_words"]
        assert "*****" in result["filtered_content"]

        # Helper function should raise ValueError with exact hit keywords
        with pytest.raises(ValueError) as exc_info:
            await check_content_safety(bad_text, field_name="forum thread")
        assert "Content moderation violation" in str(exc_info.value)
        assert any(kw in str(exc_info.value) for kw in expected_hits)


@pytest.mark.asyncio
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧私有算子 moderation.inspect_content 已按设计移除；"
        "纯函数预筛由 calc.moderation.prescreen / assemble.moderation.prescreen_decision "
        "表达（覆盖见 tests/test_moderation_operator_flows.py 与 "
        "tests/test_moderation_nlp_prescreen.py），HTTP mock 网关本身仍由本文件前序用例覆盖。"
    )
)
async def test_microkernel_moderation_inspect_operator():
    """Verify microkernel operator 'moderation.inspect_content' uses HTTP mock service with mock_data."""
    mod_data = get_moderation_data()
    safe_text = mod_data["test_cases"]["safe_samples"][0]
    bad_item = mod_data["test_cases"]["prohibited_samples"][0]

    operator = registry.get("moderation.inspect_content")
    assert operator is not None

    # Safe call
    out_safe = await operator({"content": safe_text}, {})
    assert out_safe["moderation_inspected"] is True
    assert out_safe["passed"] is True

    # Blocked call
    with pytest.raises(ValueError) as exc:
        await operator({"content": bad_item["text"]}, {})
    assert "Content moderation violation" in str(exc.value)


@pytest.mark.asyncio
async def test_dynamic_keyword_lifecycle_without_code_changes():
    """Verify adding/removing keywords dynamically via Mock HTTP API using mock_data templates."""
    mod_data = get_moderation_data()
    lifecycle_data = mod_data["test_cases"]["dynamic_lifecycle"]
    dynamic_bad_word = lifecycle_data["sample_dynamic_word"]
    sample_text = lifecycle_data["template_text"].format(word=dynamic_bad_word)

    # 1. Initially, dynamic word is not in dictionary -> passes
    res_before = await content_moderation_gateway.scan_text(sample_text)
    assert res_before["passed"] is True

    async with httpx.AsyncClient(trust_env=False) as client:
        # 2. Inject new sensitive keyword into Mock Server via HTTP POST
        add_resp = await client.post(
            f"{MOCK_ENDPOINT}/rules/keywords",
            json={"keyword": dynamic_bad_word}
        )
        assert add_resp.status_code == 200

        # 3. Now the same text is immediately blocked via HTTP, zero code change
        res_blocked = await content_moderation_gateway.scan_text(sample_text)
        assert res_blocked["passed"] is False
        assert dynamic_bad_word in res_blocked["hit_words"]

        # 4. Remove the keyword via HTTP DELETE
        del_resp = await client.delete(f"{MOCK_ENDPOINT}/rules/keywords/{dynamic_bad_word}")
        assert del_resp.status_code == 200

        # 5. Text passes again
        res_after = await content_moderation_gateway.scan_text(sample_text)
        assert res_after["passed"] is True
