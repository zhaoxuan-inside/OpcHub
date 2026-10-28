"""Compatibility entrypoint for the loyalty operator-kernel pipelines.

The four legacy DAG codes are preserved because ``core/gateway/adapters.py``
imports them by name; the actual topology now lives in
``config/scenarios/loyalty.yaml`` and is compiled by the scenario loader.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("opchub.loyalty.pipelines")

AWARD_PIPELINE = "OPC_LOYALTY_AWARD_PIPELINE"
REVOKE_PIPELINE = "OPC_LOYALTY_REVOKE_PIPELINE"
REDEEM_PIPELINE = "OPC_LOYALTY_REDEEM_PIPELINE"
SUBSCRIBE_PIPELINE = "OPC_LOYALTY_SUBSCRIBE_PIPELINE"

LOYALTY_PIPELINES = (
    AWARD_PIPELINE,
    REVOKE_PIPELINE,
    REDEEM_PIPELINE,
    SUBSCRIBE_PIPELINE,
    "OPC_LOYALTY_AUTO_RENEW_PIPELINE",
    "OPC_LOYALTY_ACCOUNT_PIPELINE",
    "OPC_LOYALTY_LEDGER_PIPELINE",
    "OPC_LOYALTY_RULES_PIPELINE",
    "OPC_LOYALTY_MEMBERSHIP_PLANS_PIPELINE",
    "OPC_LOYALTY_MEMBERSHIP_ME_PIPELINE",
    "OPC_LOYALTY_REWARDS_ITEMS_PIPELINE",
    "OPC_LOYALTY_REWARDS_ORDERS_PIPELINE",
    "OPC_LOYALTY_CONTENT_READ_PIPELINE",
    "OPC_LOYALTY_ADMIN_GRANT_PIPELINE",
)


def ensure_loyalty_pipelines() -> None:
    """Idempotently compile the loyalty scenarios and seed their data assets."""
    from src.core.scenario import ensure_scenarios_loaded

    ensure_scenarios_loaded()
    try:
        from src.domains.loyalty.service import loyalty_service

        loyalty_service.prepare_runtime()
    except Exception as exc:  # pragma: no cover - data seeding is best effort
        logger.warning("Loyalty runtime preparation skipped: %s", exc)
