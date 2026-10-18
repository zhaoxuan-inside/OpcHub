"""End-to-End integration tests for all external third-party services over HTTP.

Strictly verifies that:
1. Aliyun OSS multipart attachment upload connects over real HTTP using data from mock_data/oss_attachments.yaml.
2. WeChat Pay V3 media/attachment upload works over official multipart protocol using mock_data.
3. Aliyun SMS and Enterprise verification work over official protocol using mock_data/sms_and_identity.yaml.
4. WeChat Pay V3 profit sharing and Stripe Connect transfers work using mock_data/payment_and_split.yaml.
5. SiliconFlow LLM chat completions work using mock_data/ai_completions.yaml.
6. Zero hardcoded mock datasets in business logic or tests.
"""
import pytest
import pytest_asyncio
import httpx

from src.infrastructure.external_gateway.oss_storage_gateway import oss_storage_gateway
from mock_data.loader import (
    get_oss_attachments_data,
    get_sms_and_identity_data,
    get_payment_and_split_data,
    get_ai_completions_data,
)

MOCK_ENDPOINT = "http://127.0.0.1:8099"


@pytest.mark.asyncio
async def test_oss_attachment_upload_and_download():
    """Verify Aliyun OSS standard PostObject attachment upload & download over HTTP using mock_data."""
    oss_data = get_oss_attachments_data()
    sample = oss_data["sample_attachments"]["business_license"]
    
    file_content = sample["raw_content_utf8"].encode("utf-8")
    filename = sample["filename"]
    content_type = sample["content_type"]
    bucket = sample.get("target_bucket", "opchub-attachments")
    folder = sample.get("target_folder", "attachments")

    # 1. Upload attachment via real HTTP
    upload_res = await oss_storage_gateway.upload_attachment(
        file_bytes=file_content,
        filename=filename,
        content_type=content_type,
        bucket=bucket,
        folder=folder,
    )

    assert upload_res["status"] == "SUCCESS"
    assert upload_res["code"] == 200
    assert upload_res["bucket"] == bucket
    assert upload_res["filename"] == filename
    assert upload_res["size_bytes"] == len(file_content)
    assert "etag" in upload_res
    assert upload_res["url"].startswith(f"/oss/files/{folder}/")

    # 2. Download the uploaded file back over HTTP to verify physical persistence
    async with httpx.AsyncClient(trust_env=False) as client:
        download_resp = await client.get(f"{MOCK_ENDPOINT}{upload_res['url']}")
        assert download_resp.status_code == 200
        assert download_resp.content == file_content


@pytest.mark.asyncio
async def test_wechat_media_attachment_upload():
    """Verify WeChat Pay V3 merchant certificate/media upload over HTTP using mock_data."""
    oss_data = get_oss_attachments_data()
    sample = oss_data["sample_attachments"]["wechat_id_card"]
    
    img_content = bytes.fromhex(sample["raw_content_hex"])
    filename = sample["filename"]
    content_type = sample["content_type"]
    meta = sample.get("meta", {})

    media_res = await oss_storage_gateway.upload_wechat_media(
        file_bytes=img_content,
        filename=filename,
        content_type=content_type,
        meta=meta
    )

    assert "media_id" in media_res
    assert media_res["media_id"].startswith("MEDIA_wx_")
    assert media_res["size"] == len(img_content)
    assert media_res["filename"] == filename


@pytest.mark.asyncio
async def test_aliyun_sms_and_enterprise_verify():
    """Verify Aliyun SMS send and legal enterprise identity verify over HTTP using mock_data."""
    sms_identity_data = get_sms_and_identity_data()
    sms_cfg = sms_identity_data["sms"]
    valid_corp = sms_identity_data["enterprises"]["valid_records"][0]
    invalid_corp = sms_identity_data["enterprises"]["invalid_records"][0]

    async with httpx.AsyncClient(trust_env=False) as client:
        # 1. SMS Send
        phone = sms_cfg["test_phone"]
        code = sms_cfg["test_code"]
        sms_resp = await client.post(
            f"{MOCK_ENDPOINT}/?Action=SendSms&PhoneNumbers={phone}&TemplateParam=%7B%22code%22%3A%22{code}%22%7D"
        )
        assert sms_resp.status_code == 200
        sms_data = sms_resp.json()
        assert sms_data["Code"] == "OK"
        assert "BizId" in sms_data

        # 2. Enterprise Real-name verify (Valid Case)
        corp_resp = await client.post(
            f"{MOCK_ENDPOINT}/api/v1/enterprise/verify",
            json={
                "credit_code": valid_corp["credit_code"],
                "legal_person": valid_corp["legal_person"],
                "company_name": valid_corp["company_name"],
            }
        )
        assert corp_resp.status_code == 200
        corp_data = corp_resp.json()
        assert corp_data["status"] == "SUCCESS"
        assert corp_data["verified"] is True
        assert corp_data["enterprise_status"] == valid_corp["enterprise_status"]

        # 3. Enterprise Real-name verify (Invalid Case)
        inv_resp = await client.post(
            f"{MOCK_ENDPOINT}/api/v1/enterprise/verify",
            json={
                "credit_code": invalid_corp["credit_code"],
                "legal_person": invalid_corp["legal_person"],
            }
        )
        assert inv_resp.status_code == 200
        inv_data = inv_resp.json()
        assert inv_data["status"] == invalid_corp["expected_status"]
        assert inv_data["verified"] is False


@pytest.mark.asyncio
async def test_wechat_pay_and_stripe_split_orders():
    """Verify WeChat Pay V3 profit sharing and Stripe Connect transfers over HTTP using mock_data."""
    pay_data = get_payment_and_split_data()
    wx_sample = pay_data["wechat_pay"]["sample_order"]
    stripe_sample = pay_data["stripe_connect"]["sample_transfer"]

    async with httpx.AsyncClient(trust_env=False) as client:
        # 1. WeChat Pay V3 Profit Sharing
        wx_resp = await client.post(
            f"{MOCK_ENDPOINT}/v3/profitsharing/orders",
            json={
                "transaction_id": wx_sample["transaction_id"],
                "out_order_no": wx_sample["out_order_no"],
                "receivers": wx_sample["receivers"]
            }
        )
        assert wx_resp.status_code == 200
        wx_data = wx_resp.json()
        assert wx_data["state"] == wx_sample["expected_state"]
        assert wx_data["total_amount_fen"] == wx_sample["expected_total_fen"]
        assert len(wx_data["receivers"]) == len(wx_sample["receivers"])

        # 2. Stripe Connect Transfers
        stripe_resp = await client.post(
            f"{MOCK_ENDPOINT}/v1/transfers",
            json={
                "amount": stripe_sample["amount"],
                "currency": stripe_sample["currency"],
                "destination": stripe_sample["destination"],
                "description": stripe_sample["description"],
            }
        )
        assert stripe_resp.status_code == 200
        stripe_data = stripe_resp.json()
        assert stripe_data["status"] == stripe_sample["expected_status"]
        assert stripe_data["amount"] == stripe_sample["amount"]
        assert stripe_data["currency"] == stripe_sample["currency"]


@pytest.mark.asyncio
async def test_siliconflow_llm_chat_completions():
    """Verify SiliconFlow / OpenAI compatible chat completions over HTTP using mock_data."""
    ai_data = get_ai_completions_data()
    prompt_cfg = ai_data["sample_prompts"]["charter_generation"]

    async with httpx.AsyncClient(trust_env=False) as client:
        ai_resp = await client.post(
            f"{MOCK_ENDPOINT}/v1/chat/completions",
            json={
                "model": ai_data.get("defaults", {}).get("default_model", "deepseek-ai/DeepSeek-V3"),
                "messages": [
                    {"role": "system", "content": prompt_cfg["system_role"]},
                    {"role": "user", "content": prompt_cfg["user_message"]},
                ]
            }
        )
        assert ai_resp.status_code == 200
        ai_data_res = ai_resp.json()
        assert ai_data_res["object"] == "chat.completion"
        assert len(ai_data_res["choices"]) > 0
        reply = ai_data_res["choices"][0]["message"]["content"]
        assert prompt_cfg["expected_keyword"] in reply
