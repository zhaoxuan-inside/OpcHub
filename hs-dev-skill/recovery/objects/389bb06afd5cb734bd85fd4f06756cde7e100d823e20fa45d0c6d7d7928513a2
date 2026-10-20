"""Unified Payment & Fund Escrow Gateway (WeChat Pay Profit Sharing & Stripe Connect).

Strictly enforces Chinese regulatory anti-fund-pooling (防二清) safeguards:
1. Platform NEVER touches or pools customer funds into private accounts.
2. Direct multi-party settlement via licensed clearing channels:
   - Domestic transactions: WeChat Pay V3 Profit Sharing (微信支付商户分账).
   - Cross-border/Global SaaS: Stripe Connect Direct Transfers & Application Fees.
"""
from typing import Any, Dict, List, Optional
import time
from src.core.config import settings
from .base_client import BaseOutboundClient


class WeChatPayGateway(BaseOutboundClient):
    """Outbound client for WeChat Pay V3 Profit Sharing (微信商户分账与结算)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        mch_id: Optional[str] = None,
        api_key_env: Optional[str] = None,
        mock_mode: Optional[bool] = None
    ):
        super().__init__(
            service_name="WECHAT_PAY_V3",
            base_url=base_url or settings.wechat_pay_base_url,
            mock_mode=mock_mode if mock_mode is not None else settings.wechat_pay_mock_mode,
            api_key_env=api_key_env or settings.wechat_pay_api_key_env
        )
        self.mch_id = mch_id or settings.wechat_pay_mch_id

    async def create_profit_sharing_order(
        self,
        transaction_id: str,
        out_order_no: str,
        receivers: List[Dict[str, Any]],
        unfreeze_unsplit: bool = True
    ) -> Dict[str, Any]:
        """Call WeChat Pay V3 POST /v3/profitsharing/orders."""
        def mock_split(payload):
            total_share = sum(r.get("amount", 0) for r in receivers)
            return {
                "status": "SUCCESS",
                "order_id": out_order_no,
                "transaction_id": transaction_id,
                "mch_id": self.mch_id,
                "state": "FINISHED",
                "receivers": receivers,
                "total_shared_fen": total_share,
                "unfreeze_unsplit": unfreeze_unsplit,
                "wechat_order_id": f"wx_pf_{int(time.time()*1000)}"
            }

        payload = {
            "mchid": self.mch_id,
            "transaction_id": transaction_id,
            "out_order_no": out_order_no,
            "receivers": receivers,
            "unfreeze_unsplit": unfreeze_unsplit
        }

        return await self.execute_request(
            method="POST",
            path="/v3/profitsharing/orders",
            payload=payload,
            mock_handler=mock_split
        )


class StripeGateway(BaseOutboundClient):
    """Outbound client for Stripe Connect Cross-Border Direct Split (出海结汇与分账)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key_env: Optional[str] = None,
        mock_mode: Optional[bool] = None
    ):
        super().__init__(
            service_name="STRIPE_CONNECT",
            base_url=base_url or settings.stripe_base_url,
            mock_mode=mock_mode if mock_mode is not None else settings.stripe_mock_mode,
            api_key_env=api_key_env or settings.stripe_api_key_env
        )

    async def create_destination_charge(
        self,
        amount_cents: int,
        currency: str,
        destination_account: str,
        application_fee_cents: int,
        description: str
    ) -> Dict[str, Any]:
        """Create a Stripe PaymentIntent with direct destination transfer and platform fee."""
        def mock_charge(payload):
            return {
                "status": "SUCCESS",
                "id": f"pi_mock_{int(time.time()*1000)}",
                "object": "payment_intent",
                "amount": amount_cents,
                "currency": currency.lower(),
                "destination_account": destination_account,
                "application_fee_amount": application_fee_cents,
                "maker_net_amount": amount_cents - application_fee_cents,
                "client_secret": f"pi_secret_{int(time.time()*1000)}",
                "livemode": False
            }

        payload = {
            "amount": amount_cents,
            "currency": currency.lower(),
            "transfer_data": {"destination": destination_account},
            "application_fee_amount": application_fee_cents,
            "description": description
        }

        return await self.execute_request(
            method="POST",
            path="/v1/payment_intents",
            payload=payload,
            mock_handler=mock_charge
        )


class PaymentGateway(BaseOutboundClient):
    """Unified anti-fund-pooling payment router coordinating WeChat Pay and Stripe channels."""

    def __init__(self, base_url: str = "https://api.mch.weixin.qq.com", mock_mode: Optional[bool] = None):
        super().__init__(
            service_name="PAYMENT_ESCROW",
            base_url=base_url,
            mock_mode=mock_mode if mock_mode is not None else settings.wechat_pay_mock_mode
        )
        self.wechat = WeChatPayGateway(mock_mode=mock_mode)
        self.stripe = StripeGateway(mock_mode=mock_mode)

    async def create_split_order(
        self,
        order_id: str,
        amount_cny: float,
        merchant_account: str,
        maker_account: str,
        channel: str = "WECHAT"
    ) -> Dict[str, Any]:
        """Unified method creating an anti-fund-pooling split order across WeChat or Stripe."""
        platform_fee = round(amount_cny * 0.05, 2)
        maker_share = round(amount_cny - platform_fee, 2)

        if channel.upper() == "STRIPE":
            amount_cents = int(round(amount_cny * 100))
            fee_cents = int(round(platform_fee * 100))
            res = await self.stripe.create_destination_charge(
                amount_cents=amount_cents,
                currency="cny",
                destination_account=maker_account,
                application_fee_cents=fee_cents,
                description=f"OpcHub Order {order_id}"
            )
            return {
                "status": res.get("status", "ERROR"),
                "order_id": order_id,
                "channel": "STRIPE_CONNECT",
                "escrow_channel": "LICENSED_STRIPE_SPLIT" if res.get("status") == "SUCCESS" else "NONE",
                "total_amount": amount_cny,
                "maker_share": maker_share,
                "platform_fee": platform_fee,
                "transaction_no": res.get("id", ""),
                "escrow_verified": res.get("status") == "SUCCESS",
                "trace_id": res.get("trace_id", ""),
                "mocked": res.get("mocked", False),
            }

        # Default WeChat Pay V3
        receivers = [
            {
                "type": "MERCHANT_ID",
                "account": maker_account,
                "amount": int(round(maker_share * 100)),
                "description": f"创客劳务报酬 {order_id}"
            },
            {
                "type": "MERCHANT_ID",
                "account": merchant_account,
                "amount": int(round(platform_fee * 100)),
                "description": f"平台撮合服务费 {order_id}"
            }
        ]

        wx_res = await self.wechat.create_profit_sharing_order(
            transaction_id=f"wx_tx_{order_id}",
            out_order_no=f"split_{order_id}",
            receivers=receivers,
            unfreeze_unsplit=True
        )

        return {
            "status": wx_res.get("status", "ERROR"),
            "order_id": order_id,
            "channel": "WECHAT_PAY_V3",
            "escrow_channel": "LICENSED_WECHAT_SPLIT" if wx_res.get("status") == "SUCCESS" else "NONE",
            "total_amount": amount_cny,
            "maker_share": maker_share,
            "platform_fee": platform_fee,
            "transaction_no": wx_res.get("wechat_order_id", ""),
            "escrow_verified": wx_res.get("status") == "SUCCESS",
            "trace_id": wx_res.get("trace_id", ""),
            "mocked": wx_res.get("mocked", False),
        }


payment_gateway = PaymentGateway()
