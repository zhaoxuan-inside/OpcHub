"""Unified Government Policy Public Data Fetcher Gateway with Rate-Limiting."""
from typing import Any
from .base_client import BaseOutboundClient


class GovCrawlerGateway(BaseOutboundClient):
    """Outbound proxy for fetching official government open data with rate limiting."""

    def __init__(self, base_url: str = "https://www.gov.cn", mock_mode: bool = True):
        super().__init__(service_name="GOV_CRAWLER", base_url=base_url, mock_mode=mock_mode)

    async def fetch_public_policy(self, department: str, doc_number: str) -> dict[str, Any]:
        """Fetch open public policy document strictly from official gov.cn portals."""
        def mock_doc(_):
            return {
                "status": "SUCCESS",
                "department": department,
                "doc_number": doc_number,
                "title": f"{department}关于支持小微企业与个体创客高质量发展的若干政策通知",
                "source_url": f"https://www.gov.cn/zhengce/{doc_number}.htm",
                "is_classified": False,
                "disclaimer": "本条目直接自各级人民政府官方门户公开发布渠道获取"
            }

        return await self.execute_request(
            method="GET",
            path=f"/zhengce/query?dept={department}&doc={doc_number}",
            payload={"dept": department, "doc": doc_number},
            mock_handler=mock_doc
        )


gov_crawler_gateway = GovCrawlerGateway()
