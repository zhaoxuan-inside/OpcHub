"""Comprehensive Third-Party External API Mock Server.

Simulates official API specifications for all external third-party integrations:
1. Aliyun Green (Content Moderation / Sensitive Words) - POST /green/text/scan & POST /v2/text/scan
2. Aliyun OSS & Attachment Upload (Official multipart & binary upload) - POST /oss/upload & PUT /oss/{bucket}/{key}
3. WeChat Pay V3 Media/Attachment Upload - POST /v3/merchant/media/upload
4. WeChat Pay V3 Profit Sharing (Anti-fund-pooling) - POST /v3/profitsharing/orders
5. Stripe Connect Cross-Border Direct Split - POST /v1/transfers
6. Aliyun SMS (Dysmsapi) - POST /?Action=SendSms & POST /sms/send
7. State Enterprise Real-Name Verification - POST /api/v1/enterprise/verify
8. SiliconFlow / OpenAI Compatible LLM Inference - POST /v1/chat/completions
"""
import hashlib
import json
import os
import shutil
import time
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mock_server.service import moderation_engine
from mock_data.loader import (
    get_moderation_data,
    get_oss_attachments_data,
    get_sms_and_identity_data,
    get_payment_and_split_data,
    get_ai_completions_data,
)

app = FastAPI(
    title="OpcHub Unified External Gateway Mock Service",
    description="Simulates official third-party cloud service protocols for end-to-end integration testing",
    version="2.0.0",
)

STORAGE_DIR = Path(__file__).resolve().parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# 0. Health & Probe
# =============================================================================
@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "opchub_unified_mock_server",
        "timestamp": time.time(),
        "capabilities": [
            "aliyun_green",
            "aliyun_oss_attachment_upload",
            "wechat_media_upload",
            "wechat_pay_v3_profit_sharing",
            "stripe_connect_transfers",
            "aliyun_sms",
            "enterprise_verify",
            "siliconflow_llm_inference",
        ]
    }


# =============================================================================
# 1. Aliyun Green Content Moderation (官方文本垃圾与敏感词检测)
# =============================================================================
class TaskItem(BaseModel):
    dataId: Optional[str] = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    content: str


class GreenTextScanRequest(BaseModel):
    tasks: List[TaskItem]
    scenes: List[str] = ["antispam"]


@app.post("/green/text/scan")
async def green_text_scan(payload: GreenTextScanRequest) -> Dict[str, Any]:
    task_results = []
    for task in payload.tasks:
        scan_res = moderation_engine.scan_content(task.content)
        detail_contexts = [{"context": kw} for kw in scan_res["hit_words"]]
        results = [
            {
                "scene": "antispam",
                "suggestion": scan_res["suggestion"],
                "label": scan_res["label"],
                "rate": scan_res["rate"],
                "filteredContent": scan_res["filtered_content"],
                "details": [{"contexts": detail_contexts}] if detail_contexts else [],
            }
        ]
        task_results.append({
            "code": 200,
            "msg": "OK",
            "dataId": task.dataId,
            "taskId": f"txt_scan_{uuid.uuid4().hex[:12]}",
            "results": results,
        })
    return {"code": 200, "msg": "OK", "data": task_results}


@app.post("/v2/text/scan")
async def green_v2_text_scan(payload: GreenTextScanRequest) -> Dict[str, Any]:
    return await green_text_scan(payload)


@app.get("/rules/keywords")
async def list_keywords():
    return {"keywords": moderation_engine.list_keywords()}


@app.post("/rules/keywords")
async def add_keyword(payload: Dict[str, str]):
    kw = payload.get("keyword", "").strip()
    if not kw:
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")
    added = moderation_engine.add_keyword(kw)
    return {"status": "SUCCESS", "added": added, "keyword": kw}


@app.delete("/rules/keywords/{keyword}")
async def delete_keyword(keyword: str):
    removed = moderation_engine.remove_keyword(keyword)
    return {"status": "SUCCESS", "removed": removed, "keyword": keyword}


@app.post("/rules/reset")
async def reset_keywords():
    return {"status": "SUCCESS", "keywords": moderation_engine.reset_keywords()}


# =============================================================================
# 2. Aliyun OSS 附件与对象存储官方标准接入 (Multipart / Form-data 传附件)
# =============================================================================
@app.post("/oss/upload")
async def oss_upload_attachment(
    file: UploadFile = File(...),
    bucket: str = Form(default="opchub-attachments"),
    folder: str = Form(default="attachments"),
):
    """Aliyun OSS standard PostObject attachment upload implementation."""
    content = await file.read()
    etag = hashlib.md5(content).hexdigest()
    ext = Path(file.filename or "file.bin").suffix
    obj_key = f"{folder}/{time.strftime('%Y%m%d')}/{uuid.uuid4().hex[:12]}{ext}"
    
    save_path = STORAGE_DIR / obj_key
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)
        
    return {
        "status": "SUCCESS",
        "code": 200,
        "bucket": bucket,
        "object_key": obj_key,
        "filename": file.filename,
        "size_bytes": len(content),
        "content_type": file.content_type or "application/octet-stream",
        "etag": f'"{etag}"',
        "url": f"/oss/files/{obj_key}",
        "x_oss_request_id": f"OSS_REQ_{uuid.uuid4().hex[:16].upper()}",
    }


@app.put("/oss/{bucket}/{object_name:path}")
async def oss_put_object(bucket: str, object_name: str, request: Request):
    """Aliyun OSS standard PutObject stream upload."""
    content = await request.body()
    etag = hashlib.md5(content).hexdigest()
    save_path = STORAGE_DIR / object_name
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)

    return Response(
        status_code=200,
        headers={
            "ETag": f'"{etag}"',
            "x-oss-request-id": f"OSS_REQ_{uuid.uuid4().hex[:16].upper()}",
            "x-oss-object-type": "Normal",
        }
    )


@app.get("/oss/files/{filepath:path}")
async def oss_download_file(filepath: str):
    """Serve uploaded attachments back to clients."""
    target = STORAGE_DIR / filepath
    if not target.exists():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(target)


# =============================================================================
# 3. 微信支付商户媒体文件/证件附件上传官方标准 (POST /v3/merchant/media/upload)
# =============================================================================
@app.post("/v3/merchant/media/upload")
async def wechat_media_upload(
    file: UploadFile = File(...),
    meta: Optional[str] = Form(default="{}"),
):
    """WeChat Pay V3 Merchant Media/Certificate upload endpoint."""
    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()
    media_id = f"MEDIA_wx_{uuid.uuid4().hex[:16]}"
    
    # Save media attachment
    save_path = STORAGE_DIR / "wechat_media" / f"{media_id}_{file.filename}"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)

    return {
        "media_id": media_id,
        "digest": sha256_hash,
        "size": len(content),
        "filename": file.filename,
    }


# =============================================================================
# 4. 微信支付 V3 分账与合规结算 (POST /v3/profitsharing/orders)
# =============================================================================
@app.post("/v3/profitsharing/orders")
async def wechat_profitsharing_orders(payload: Dict[str, Any]):
    """WeChat Pay V3 profit sharing execution."""
    out_order_no = payload.get("out_order_no", f"pf_{uuid.uuid4().hex[:12]}")
    transaction_id = payload.get("transaction_id", f"tx_{uuid.uuid4().hex[:14]}")
    receivers = payload.get("receivers", [])
    total_fen = sum(int(r.get("amount", 0)) for r in receivers)

    return {
        "sub_mchid": payload.get("sub_mchid", ""),
        "transaction_id": transaction_id,
        "out_order_no": out_order_no,
        "order_id": f"300000000{int(time.time()*1000)}",
        "state": "FINISHED",
        "receivers": [
            {
                "amount": r.get("amount", 0),
                "account": r.get("account", ""),
                "type": r.get("type", "MERCHANT_ID"),
                "result": "SUCCESS",
                "finish_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "detail_id": f"360000000{uuid.uuid4().hex[:8]}",
            }
            for r in receivers
        ],
        "total_amount_fen": total_fen,
        "unfreeze_unsplit": payload.get("unfreeze_unsplit", True),
    }


# =============================================================================
# 5. Stripe Connect 跨境商户分账官方接入 (POST /v1/transfers)
# =============================================================================
@app.post("/v1/transfers")
async def stripe_connect_transfers(request: Request):
    """Stripe Connect Transfers endpoint."""
    # Handles both JSON and application/x-www-form-urlencoded
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        from urllib.parse import parse_qs
        parsed = parse_qs(body_bytes.decode("utf-8"))
        body = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    transfer_id = f"tr_{uuid.uuid4().hex[:20]}"
    amount = int(body.get("amount", 1000))
    currency = body.get("currency", "cny")
    destination = body.get("destination", "acct_test_dest_001")

    return {
        "id": transfer_id,
        "object": "transfer",
        "amount": amount,
        "amount_reversed": 0,
        "balance_transaction": f"txn_{uuid.uuid4().hex[:18]}",
        "created": int(time.time()),
        "currency": currency,
        "description": body.get("description", "OpcHub Solo Maker Settlement"),
        "destination": destination,
        "livemode": False,
        "reversed": False,
        "status": "paid",
    }


# =============================================================================
# 6. 阿里云短信验证码 (Aliyun Dysmsapi SendSms)
# =============================================================================
@app.api_route("/sms/send", methods=["GET", "POST"])
@app.api_route("/", methods=["GET", "POST"])
async def aliyun_sms_send(request: Request):
    """Aliyun Dysmsapi SendSms simulation."""
    params = dict(request.query_params)
    action = params.get("Action", "SendSms")
    
    if action == "SendSms":
        phone = params.get("PhoneNumbers", "")
        return {
            "Code": "OK",
            "Message": "OK",
            "BizId": f"9000{int(time.time()*1000)}^0",
            "RequestId": f"REQ_{uuid.uuid4().hex[:16].upper()}",
            "PhoneNumbers": phone,
        }

    return {"status": "SUCCESS", "message": f"Action {action} handled."}


# =============================================================================
# 7. 企业工商四要素实名资质核验 (POST /api/v1/enterprise/verify)
# =============================================================================
@app.post("/api/v1/enterprise/verify")
async def enterprise_verify(payload: Dict[str, Any]):
    credit_code = payload.get("credit_code", "").strip()
    legal_person = payload.get("legal_person", "").strip()
    
    sms_data = get_sms_and_identity_data()
    enterprises = sms_data.get("enterprises", {})
    
    # Check invalid records configured in mock_data
    for inv in enterprises.get("invalid_records", []):
        if credit_code == inv.get("credit_code"):
            return {
                "status": inv.get("expected_status", "FAILED"),
                "verified": False,
                "message": inv.get("expected_message", "统一社会信用代码格式非法"),
            }
            
    if not credit_code or len(credit_code) < 10:
        return {
            "status": "FAILED",
            "verified": False,
            "message": "统一社会信用代码格式非法",
        }

    # Match against valid records in mock_data
    company_name = payload.get("company_name", "")
    for val in enterprises.get("valid_records", []):
        if credit_code == val.get("credit_code"):
            legal_person = legal_person or val.get("legal_person", "")
            company_name = val.get("company_name", company_name)
            break

    return {
        "status": "SUCCESS",
        "verified": True,
        "credit_code": credit_code,
        "legal_person": legal_person,
        "company_name": company_name or "杭州创客科技有限公司",
        "enterprise_status": "NORMAL_ACTIVE",
        "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# =============================================================================
# 8. SiliconFlow / OpenAI 官方兼容大模型推理 (POST /v1/chat/completions)
# =============================================================================
@app.post("/v1/chat/completions")
async def siliconflow_chat_completions(payload: Dict[str, Any]):
    """Standard OpenAI/SiliconFlow chat completions mock endpoint."""
    model = payload.get("model", "deepseek-ai/DeepSeek-V3")
    messages = payload.get("messages", [])
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    # Dynamic intelligent mock response
    reply_text = f"【SiliconFlow 官方推理 Mock】已为您生成响应：针对'{last_user_msg[:40]}'，提供标准化的一人公司方案。"
    
    return {
        "id": f"chatcmpl_{uuid.uuid4().hex[:20]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": reply_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(last_user_msg) // 2 + 10,
            "completion_tokens": len(reply_text) // 2 + 15,
            "total_tokens": (len(last_user_msg) + len(reply_text)) // 2 + 25,
        },
    }
