"""Aliyun OSS & Media Attachment Upload Outbound Gateway.

Supports:
1. Aliyun OSS standard PostObject attachment upload.
2. WeChat Pay V3 merchant media upload.
Decoupled: connects to official cloud APIs or local HTTP Mock service over real HTTP.
"""
from typing import Any, Dict, Optional
import os
import logging
import httpx
from src.core.telemetry import get_current_trace_id

logger = logging.getLogger("opchub.gateway.storage")

DEFAULT_ENDPOINT = "http://127.0.0.1:8099"


class OSSStorageGateway:
    """Outbound client for object storage & attachment uploading."""

    def __init__(self, endpoint: Optional[str] = None, timeout: float = 30.0):
        self.endpoint = (endpoint or os.getenv("ALIYUN_OSS_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")
        self.timeout = timeout

    async def upload_attachment(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        bucket: str = "opchub-attachments",
        folder: str = "attachments",
    ) -> Dict[str, Any]:
        """Uploads a file attachment to OSS via standard multipart HTTP request."""
        trace_id = get_current_trace_id()
        url = f"{self.endpoint}/oss/upload"
        
        files = {
            "file": (filename, file_bytes, content_type)
        }
        data = {
            "bucket": bucket,
            "folder": folder,
        }
        headers = {
            "X-Trace-ID": trace_id,
        }

        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            resp = await client.post(url, files=files, data=data, headers=headers)
            resp.raise_for_status()
            res_data = resp.json()
            logger.info(f"[OSSStorageGateway] Uploaded attachment '{filename}' to {res_data.get('url')} (ETag: {res_data.get('etag')})")
            return res_data

    async def upload_wechat_media(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Uploads merchant license/identity media to WeChat Pay V3 via multipart/form-data."""
        trace_id = get_current_trace_id()
        url = f"{self.endpoint}/v3/merchant/media/upload"
        
        import json
        files = {
            "file": (filename, file_bytes, content_type)
        }
        data = {
            "meta": json.dumps(meta or {"filename": filename, "sha256": "auto"})
        }
        headers = {
            "X-Trace-ID": trace_id,
        }

        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            resp = await client.post(url, files=files, data=data, headers=headers)
            resp.raise_for_status()
            res_data = resp.json()
            logger.info(f"[OSSStorageGateway] Uploaded WeChat media '{filename}' (media_id: {res_data.get('media_id')})")
            return res_data


oss_storage_gateway = OSSStorageGateway()
