"""Unified Payment & Fund Escrow Gateway (Anti-Fund Pooling)."""
from typing import Any
from .base_client import BaseOutboundClient


class PaymentGateway(BaseOutboundClient):
    """Outbound proxy for licensed payment channels (WeChat Pay, Stripe, PingPong)."""

    def __init__(self, base_url: str = "https://api.mch.weixin.qq.com", mock_mode: bool = True):
        super().__init__(service_name="PAYMENT_ESCROW", base_url=base_url, mock_mode=mock_mode)

    async def create_split_order(
        self,
        order_id: str,
        amount_cny: float,
        merchant_account: str,
        maker_account: str
    ) -> dict[str, Any]:
        """Create a split-payment order preventing illegal platform fund pooling."""
        def mock_order(payload):
            return {
                "status": "SUCCESS",
                "order_id": order_id,
                "escrow_channel": "LICENSED_WECHAT_SPLIT",
                "total_amount": amount_cny,
                "maker_share": round(amount_cny * 0.95, 2),
                "platform_fee": round(amount_cny * 0.05, 2),
                "transaction_no": f"wx_tx_{order_id}",
                "escrow_verified": True
            }

        return await self.execute_request(
            method="POST",
            path="/v3/profitsharing/orders",
            payload={
                "order_id": order_id,
                "amount": amount_cny,
                "merchant": merchant_account,
                "maker": maker_account
            },
            mock_handler=mock_order
        )


payment_gateway = PaymentGateway()
