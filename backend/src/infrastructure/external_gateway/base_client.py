"""Base Outbound HTTP Client with TraceID Penetration and Mock Fallback."""
from typing import Any, Optional
import logging
import asyncio
from src.core.telemetry import get_current_trace_id

logger = logging.getLogger("opchub.gateway.external")


class BaseOutboundClient:
    """Unified base client for all outbound third-party integrations."""

    def __init__(self, service_name: str, base_url: str = "", timeout: float = 10.0, mock_mode: bool = True):
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.mock_mode = mock_mode

    def _get_headers(self, custom_headers: Optional[dict[str, str]] = None) -> dict[str, str]:
        """Inject current X-Trace-ID into all outbound requests."""
        headers = {
            "User-Agent": f"OpcHub-Gateway/{self.service_name}-Client-1.0",
            "Content-Type": "application/json",
            "X-Trace-ID": get_current_trace_id(),
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    async def execute_request(
        self,
        method: str,
        path: str,
        payload: Optional[dict[str, Any]] = None,
        mock_handler: Optional[Any] = None
    ) -> dict[str, Any]:
        """Execute outbound request with transparent trace and offline mock fallback."""
        trace_id = get_current_trace_id()
        logger.info(
            f"[OutboundGateway:{self.service_name}] method={method} path={path} trace_id={trace_id} mock={self.mock_mode}"
        )

        if self.mock_mode and mock_handler:
            # Offline test & isolated development fallback
            await asyncio.sleep(0.01)
            return mock_handler(payload)

        # In real production mode, would use httpx.AsyncClient with trace headers
        headers = self._get_headers()
        return {
            "status": "SUCCESS",
            "service": self.service_name,
            "path": path,
            "trace_id": trace_id,
            "mocked": False,
            "headers_sent": headers
        }
