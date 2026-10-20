"""Base Outbound HTTP Client with TraceID Penetration and Deterministic Mock Fallback."""
from typing import Any, Callable, Optional, Dict
import logging
import asyncio
import os
import httpx
from src.core.telemetry import get_current_trace_id

logger = logging.getLogger("opchub.gateway.external")


class BaseOutboundClient:
    """Unified base client for all outbound third-party integrations with anti-corruption safeguards."""

    def __init__(
        self,
        service_name: str,
        base_url: str = "",
        timeout: float = 15.0,
        mock_mode: bool = True,
        api_key_env: Optional[str] = None,
        bearer_token: Optional[str] = None
    ):
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key_env = api_key_env
        self.bearer_token = bearer_token

        # If explicit api key is present in environment, auto-enable live mode unless mock_mode is forced
        resolved_key = os.getenv(api_key_env, "") if api_key_env else ""
        if resolved_key and not mock_mode:
            self.mock_mode = False
        else:
            self.mock_mode = mock_mode

    def get_api_key(self) -> str:
        """Resolve current API key from environment variable safely."""
        if self.bearer_token:
            return self.bearer_token
        if self.api_key_env:
            return os.getenv(self.api_key_env, "")
        return ""

    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Inject current X-Trace-ID and authorization headers into outbound requests."""
        trace_id = get_current_trace_id()
        headers = {
            "User-Agent": f"OpcHub-Gateway/{self.service_name}-Client-1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Trace-ID": trace_id,
        }
        api_key = self.get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if custom_headers:
            headers.update(custom_headers)
        return headers

    async def execute_request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        mock_handler: Optional[Callable[[Optional[Dict[str, Any]]], Dict[str, Any]]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute outbound request with transparent trace propagation, error trapping, and offline fallback."""
        trace_id = get_current_trace_id()
        logger.info(
            f"[OutboundGateway:{self.service_name}] method={method} path={path} trace_id={trace_id} mock={self.mock_mode}"
        )

        # 1. Deterministic Mock Mode (For offline testing, local dev & CI pipelines)
        if self.mock_mode:
            if mock_handler:
                await asyncio.sleep(0.005)
                res = mock_handler(payload)
                res["trace_id"] = trace_id
                res["service"] = self.service_name
                res["mocked"] = True
                return res
            return {
                "status": "SUCCESS",
                "service": self.service_name,
                "path": path,
                "trace_id": trace_id,
                "mocked": True,
                "headers_sent": self._get_headers(custom_headers)
            }

        # 2. Live HTTP Execution Mode
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._get_headers(custom_headers)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.request(
                    method=method.upper(),
                    url=url,
                    json=payload if payload and method.upper() in ["POST", "PUT", "PATCH"] else None,
                    params=params,
                    headers=headers
                )
                try:
                    data = resp.json()
                except Exception:
                    data = {"text": resp.text}

                return {
                    "status": "SUCCESS" if resp.is_success else "ERROR",
                    "status_code": resp.status_code,
                    "service": self.service_name,
                    "url": str(resp.url),
                    "trace_id": trace_id,
                    "mocked": False,
                    "data": data,
                    "headers_sent": headers
                }
        except Exception as exc:
            logger.warning(
                f"[OutboundGateway:{self.service_name}] Live request failed to {url}: {exc}. Checking fallback."
            )
            if mock_handler:
                logger.info(f"[OutboundGateway:{self.service_name}] Degrading to mock handler for stability.")
                res = mock_handler(payload)
                res["trace_id"] = trace_id
                res["service"] = self.service_name
                res["mocked"] = True
                res["mock_fallback"] = True
                res["live_error"] = str(exc)
                return res
            return {
                "status": "ERROR",
                "service": self.service_name,
                "url": url,
                "trace_id": trace_id,
                "error": str(exc),
                "mocked": False
            }
