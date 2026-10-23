"""Aliyun Content Moderation Gateway (Green Service Anti-corruption Layer).

Interacts with real external Aliyun Green API or dedicated HTTP Mock Server over network.
Strictly decoupled: zero hardcoded mock/keyword datasets inside business logic.

Two-tier moderation pipeline:
  Tier 1 (local NLP pre-screen)  —— fast, dependency-free, answers the high-confidence
                                    majority itself (CONFIRMED_SAFE / CONFIRMED_VIOLATION).
  Tier 2 (external service)      —— authoritative, reached only for UNCERTAIN content.
See ``src.domains.moderation.nlp_prescreen`` for the local NLP engine.
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
            # Graceful degradation (ADR-002/003): a downed third-party moderation
            # service must not hard-block the platform's write operations. We fail
            # OPEN — log the outage and report "passed" so the caller can proceed —
            # while still hard-blocking on genuine violations whenever the service
            # is reachable. The outage is surfaced to operators via the returned
            # `unavailable` flag and the warning log below.
            logger.warning(
                f"[ContentModerationGateway] moderation service unreachable at {url}; "
                f"failing open to preserve availability: {exc}"
            )
            return {
                "passed": True,
                "suggestion": "pass",
                "hit_words": [],
                "filtered_content": content,
                "raw_response": {},
                "unavailable": True,
                "unavailable_reason": str(exc),
            }

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
            "unavailable": False,
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
    if res.get("unavailable"):
        # Outage handled fail-open in scan_text; surface it to operators so they
        # know content passed the gate without a live moderation scan.
        logger.warning(f"Content moderation gate degraded (service unavailable) for {field_name}")
        return
    if not res["passed"]:
        hits = res["hit_words"]
        msg = f"Content moderation violation: found prohibited keywords {hits} in {field_name}" if hits else f"Content moderation violation in {field_name}"
        raise ValueError(msg)


async def prescreen_and_scan(content: str, field_name: str = "content") -> Dict[str, Any]:
    """Two-tier moderation gate: local NLP pre-screen, then external scan when uncertain.

    Tier 1 runs the dependency-free NLP pre-screen. When it is confident —
    ``CONFIRMED_SAFE`` (肯定没问题) or ``CONFIRMED_VIOLATION`` (肯定有问题) — it
    short-circuits and returns immediately, avoiding the cost/latency of an external
    call (and staying available even when the external service is down).

    Tier 2 defers only ``UNCERTAIN`` content to the external moderation service, which
    remains the authoritative source of truth.

    Returns a result dict carrying the full evidence trail:
        - verdict: "CONFIRMED_SAFE" | "CONFIRMED_VIOLATION" | "UNCERTAIN"
        - passed (bool): whether the content is allowed
        - external_scan_used (bool): whether the external service was consulted
        - external_unavailable (bool): external service was down and we failed open
        - nlp (dict): the local NLP pre-screen evidence (scores, hits, patterns)
        - external (dict): the external scan raw result, when consulted
    """
    from src.domains.moderation.nlp_prescreen import prescreen_text, VERDICT_SAFE, VERDICT_VIOLATION

    if not content or not content.strip():
        return {
            "verdict": VERDICT_SAFE, "passed": True, "external_scan_used": False,
            "external_unavailable": False,
            "nlp": {"verdict": VERDICT_SAFE, "reason": "empty content"},
            "external": {},
        }

    nlp = prescreen_text(content)

    if nlp["verdict"] == VERDICT_SAFE:
        return {
            "verdict": VERDICT_SAFE, "passed": True, "external_scan_used": False,
            "external_unavailable": False, "nlp": nlp, "external": {},
        }

    if nlp["verdict"] == VERDICT_VIOLATION:
        raise ValueError(
            f"Content moderation violation: local NLP pre-screen flagged prohibited content "
            f"{nlp['hit_sensitive'] or nlp['matched_patterns']} in {field_name}"
        )

    # UNCERTAIN → defer to the external service.
    ext = await content_moderation_gateway.scan_text(content)
    if ext.get("unavailable"):
        logger.warning(f"Content moderation gate degraded (service unavailable) for {field_name}")
        return {
            "verdict": "UNCERTAIN", "passed": True, "external_scan_used": True,
            "external_unavailable": True, "nlp": nlp, "external": ext,
        }
    if not ext["passed"]:
        raise ValueError(
            f"Content moderation violation: found prohibited keywords {ext['hit_words']} in {field_name}"
        )
    return {
        "verdict": "UNCERTAIN", "passed": True, "external_scan_used": True,
        "external_unavailable": False, "nlp": nlp, "external": ext,
    }
