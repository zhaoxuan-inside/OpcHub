"""Unified AI Large Language Model Gateway Adapter."""
from typing import Any, Optional
from .base_client import BaseOutboundClient


class AIGateway(BaseOutboundClient):
    """Outbound proxy for external LLM calls (Gemini, OpenAI, etc.)."""

    def __init__(self, base_url: str = "https://generativelanguage.googleapis.com", mock_mode: bool = True):
        super().__init__(service_name="AI_LLM", base_url=base_url, mock_mode=mock_mode)

    async def generate_charter_text(self, company_name: str, biz_scope: str) -> dict[str, Any]:
        """Generate legal corporate charter content using AI model."""
        def mock_charter(_):
            return {
                "status": "SUCCESS",
                "model": "gemini-2.5-pro",
                "charter_text": f"【{company_name}章程】第一章总则：依据公司法设立，主营{biz_scope}，设执行董事兼法定代表人...",
                "tokens_consumed": 380
            }

        return await self.execute_request(
            method="POST",
            path="/v1/models/gemini-2.5-pro:generateContent",
            payload={"company_name": company_name, "biz_scope": biz_scope},
            mock_handler=mock_charter
        )


ai_gateway = AIGateway()
