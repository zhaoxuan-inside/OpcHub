"""Unified SMS and Identity Authentication Gateway."""
from typing import Any
from .base_client import BaseOutboundClient


class SMSAuthGateway(BaseOutboundClient):
    """Outbound proxy for SMS verification and legal entity identity checks."""

    def __init__(self, base_url: str = "https://dysmsapi.aliyuncs.com", mock_mode: bool = True):
        super().__init__(service_name="SMS_AUTH", base_url=base_url, mock_mode=mock_mode)

    async def send_verification_code(self, phone_number: str, code: str) -> dict[str, Any]:
        """Send 6-digit SMS verification code for real-name authentication."""
        def mock_sms(_):
            return {
                "status": "SUCCESS",
                "phone_masked": f"{phone_number[:3]}****{phone_number[-4:]}",
                "sms_channel": "ALIYUN_SMS_DIRECT",
                "sent_code_stub": code,
                "valid_seconds": 300
            }

        return await self.execute_request(
            method="POST",
            path="/?Action=SendSms",
            payload={"PhoneNumbers": phone_number, "TemplateParam": f"{{\"code\":\"{code}\"}}"},
            mock_handler=mock_sms
        )

    async def verify_corporate_entity(self, credit_code: str, legal_person: str) -> dict[str, Any]:
        """Verify business license and legal representative via state enterprise database."""
        def mock_corp(_):
            return {
                "status": "SUCCESS",
                "credit_code": credit_code,
                "legal_person": legal_person,
                "verified": True,
                "enterprise_status": "NORMAL_ACTIVE"
            }

        return await self.execute_request(
            method="POST",
            path="/api/v1/enterprise/verify",
            payload={"credit_code": credit_code, "legal_person": legal_person},
            mock_handler=mock_corp
        )


sms_auth_gateway = SMSAuthGateway()
