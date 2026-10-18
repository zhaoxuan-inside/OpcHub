"""Aliyun Content Moderation Gateway (Green Service Anti-corruption Layer).

Interacts with real external Aliyun Green API or dedicated HTTP Mock Server over network.
Strictly decoupled: zero hardcoded mock/keyword datasets inside business logic.
"""
from typing import Any, Dict, List, Optional
import os
import logging
import httpx

from src.core.telemetry import get_current_trace_id

logger = logging.getLogger("opchub.gateway.moderation")

DEFAULT_ENDPOINT = "http://127.0.0.1:8099"


class ContentModerationGateway:
    """Outbound client connecting to Aliyun Green content security service via standard HTTP."""

    def __init__(self, endpoint: Optional[str] = None, timeout: float = 5.0):
        self.endpoint = (endpoint or os.getenv("ALIYUN_GREEN_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")
        self.timeout = timeout

    async def scan_text(self, content: str, scenes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Scans UGC text via remote HTTP API.
        
        Returns:
            dict with:
                - passed (bool): whether content is safe
                - suggestion (str): 'pass', 'block', 'review'
                - hit_words (list[str]): hit sensitive keywords if blocked
                - filtered_content (str): masked content if modified
                - raw_response (dict): full third-party payload
        """
        trace_id = get_current_trace_id()
        url = f"{self.endpoint}/green/text/scan"
        payload = {
            "tasks": [{"dataId": f"task_{trace_id[:8]}", "content": content}],
            "scenes": scenes or ["antispam"],
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Trace-ID": trace_id,
        }

        try:
            # trust_env=False to avoid unwanted proxy interception for local mock endpoints
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error(f"[ContentModerationGateway] HTTP request failed to {url}: {exc}")
            raise RuntimeError(f"Content moderation service unreachable at {url}: {exc}") from exc

        # Parse Aliyun Green Standard Response Format
        passed = True
        suggestion = "pass"
        hit_words: List[str] = []
        filtered_content = content

        for task_res in data.get("data", []):
            for result in task_res.get("results", []):
                sug = result.get("suggestion", "pass")
                if sug in ["block", "review"]:
                    passed = False
                    suggestion = sug
                    for detail in result.get("details", []):
                        for ctx in detail.get("contexts", []):
                            if ctx.get("context"):
                                hit_words.append(ctx["context"])
                    if result.get("filteredContent"):
                        filtered_content = result["filteredContent"]

        hit_words = sorted(list(set(hit_words)))
        return {
            "passed": passed,
            "suggestion": suggestion,
            "hit_words": hit_words,
            "filtered_content": filtered_content,
            "raw_response": data,
        }


content_moderation_gateway = ContentModerationGateway()


async def check_content_safety(content: str, field_name: str = "content") -> None:
    """Convenience helper to enforce UGC text safety via remote HTTP moderation.
    
    Raises:
        ValueError if content violates moderation rules with hit keywords listed.
    """
    if not content or not content.strip():
        return
    res = await content_moderation_gateway.scan_text(content)
    if not res["passed"]:
        hits = res["hit_words"]
        msg = f"Content moderation violation: found prohibited keywords {hits} in {field_name}" if hits else f"Content moderation violation in {field_name}"
        raise ValueError(msg)
