"""Unified Outbound External Gateway Package.

All external third-party API and network invocations (AI, Payments, SMS/Auth, Gov Data)
MUST be routed exclusively through this package.
"""
from .base_client import BaseOutboundClient
from .ai_gateway import AIGateway, ai_gateway, SiliconFlowGateway, siliconflow_gateway
from .payment_gateway import PaymentGateway, payment_gateway, WeChatPayGateway, StripeGateway
from .sms_auth_gateway import SMSAuthGateway, sms_auth_gateway
from .gov_crawler_gateway import GovCrawlerGateway, gov_crawler_gateway, AsyncTokenBucket

__all__ = [
    "BaseOutboundClient",
    "AIGateway",
    "ai_gateway",
    "SiliconFlowGateway",
    "siliconflow_gateway",
    "PaymentGateway",
    "payment_gateway",
    "WeChatPayGateway",
    "StripeGateway",
    "SMSAuthGateway",
    "sms_auth_gateway",
    "GovCrawlerGateway",
    "gov_crawler_gateway",
    "AsyncTokenBucket",
]
