"""Data models for Maker Profile and Paid Entitlements."""
from typing import List, Optional
from pydantic import BaseModel


class EntitlementItem(BaseModel):
    id: str
    name: str
    tier: str  # "STANDARD", "PRO", "BLACK_DIAMOND"
    price_cny: float
    description: str
    is_active: bool = False
    quota_desc: str


class MakerProfileResponse(BaseModel):
    uid: str
    nickname: str
    role: str
    company_name: str
    credit_code: str
    tier_name: str
    account_type: Optional[str] = "MAKER"
    industry_track: Optional[str] = ""
    avatar_id: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    agreement_version: Optional[str] = ""
    entitlements: List[EntitlementItem]


class UserProfileUpdateRequest(BaseModel):
    user_id: Optional[str] = None
    nickname: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    credit_code: Optional[str] = None
    industry_track: Optional[str] = None
    avatar_id: Optional[str] = None



class EntitlementActivateRequest(BaseModel):
    user_id: str
    entitlement_id: str


class EntitlementActivateResponse(BaseModel):
    user_id: str
    entitlement_id: str
    is_active: bool
    status: str = "ACTIVATED"
    receipt_no: str
    message: str


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    nickname: Optional[str] = None
    company_name: Optional[str] = None
    # Commercialization Extensions
    verification_code: Optional[str] = None
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None
    agreed_terms: bool = True  # Defaults to True for backward compatibility in programmatic tests
    account_type: str = "MAKER"  # "MAKER" (个人创客) | "OPC" (一人公司) | "ENTERPRISE" (企业机构)
    industry_track: Optional[str] = None
    credit_code: Optional[str] = None
    phone: Optional[str] = None
    invitation_code: Optional[str] = None
    client_ip: Optional[str] = None
    agreement_version: str = "v1.2.0"


class SendCodeRequest(BaseModel):
    email: str
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None
    client_ip: Optional[str] = None


class SendCodeResponse(BaseModel):
    sent: bool
    email: str
    cooldown_seconds: int = 60
    expires_in: int = 300
    message: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


class VerifyCodeResponse(BaseModel):
    valid: bool
    message: str


class CaptchaResponse(BaseModel):
    captcha_id: str
    captcha_svg: str
    captcha_image: str
    expires_in: int


class PasswordStrengthRequest(BaseModel):
    password: str
    email: Optional[str] = None


class PasswordStrengthResponse(BaseModel):
    score: int
    level: str
    label: str
    feedback: List[str]
    meets_commercial_standard: bool


class UserLoginRequest(BaseModel):
    email: Optional[str] = None
    account: Optional[str] = None
    password: Optional[str] = None
    verification_code: Optional[str] = None
    code: Optional[str] = None
    login_type: Optional[str] = None  # "account_password" | "email_code" | "email_password"


class AuthSessionResponse(BaseModel):
    token: str
    uid: str
    email: str
    nickname: str
    role: str = "MAKER"
    company_name: Optional[str] = None
    tier_name: str = "标准创客"
    account_type: Optional[str] = "MAKER"
    industry_track: Optional[str] = None
    message: str = "登录成功"
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    """Change password (used to rotate the built-in admin's initial credential)."""
    old_password: str
    new_password: str
    user_id: Optional[str] = None
    token: Optional[str] = None


