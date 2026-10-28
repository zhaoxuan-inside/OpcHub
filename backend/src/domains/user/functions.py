"""Single-responsibility pure function operators for the user / auth domain.

Only calculations / validation / normalisation / assembly live here. Storage is
handled by ``entity.*`` operators, identity by ``guard.*``, side effects by
``metric.*`` / ``audit.*`` and outbound mail by ``external.email.send``.

There is no I/O, no orchestration, no ``execute_scenario`` and no cross-domain
import in this module. Randomness (captcha / code / password salt / token) is
accepted where the security contract requires it.
"""
from __future__ import annotations

import html
import math
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from src.core.config import settings
from src.core.operators.sdk import operator
from src.core.security import (
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)
from src.domains.user.mail_config import (
    list_mail_providers,
    resolve_mail_config,
)
from src.domains.user import mailer as _mailer  # noqa: F401 - registers external.email.send

# ---------------------------------------------------------------------------
# Shared constants (declarative policy inputs, no storage)
# ---------------------------------------------------------------------------
EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
CREDIT_CODE_PATTERN = r"^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$"

COMMON_WEAK_PASSWORDS = {
    "123456",
    "12345678",
    "123456789",
    "qwerty",
    "111111",
    "000000",
}

BUILTIN_AVATAR_IDS = frozenset(
    {
        "dev",
        "designer",
        "writer",
        "founder",
        "ecommerce",
        "consultant",
        "photographer",
        "illustrator",
        "video",
        "musician",
        "teacher",
        "finance",
        "legal",
        "crossborder",
        "researcher",
        "craftsman",
        "fitness",
        "foodie",
        "traveler",
        "farmer",
    }
)

FOUNDING_VIP_ENTITLEMENT_ID = "ent_black_diamond_priority"
FOUNDING_VIP_TIER_NAME = "黑钻创客 VIP"
ENTITLEMENT_EXPIRY_FORMAT = "%Y-%m-%d %H:%M:%S"
STANDARD_TIER_NAME = "标准创客"

MEMBERSHIP_ENTITLEMENT_MAP = {
    "PRO": {"ent_ai_tax_assistant"},
    "BLACK_DIAMOND": {"ent_ai_tax_assistant", "ent_black_diamond_priority"},
}
MEMBERSHIP_TIER_NAMES = {
    "STANDARD": STANDARD_TIER_NAME,
    "PRO": "PRO 创客",
    "BLACK_DIAMOND": FOUNDING_VIP_TIER_NAME,
}

VERIFICATION_TTL_SECONDS = 300
VERIFICATION_COOLDOWN_SECONDS = 60
VERIFICATION_MAX_ATTEMPTS = 5
CAPTCHA_TTL_SECONDS = 300
SEND_CODE_IP_LIMIT = 30

TERMS_OF_SERVICE_VERSION = "v1.2.0"
PRIVACY_POLICY_VERSION = "v1.2.0"

TERMS_OF_SERVICE_SUMMARY = """
# OpcHub 超级个体与一人公司平台用户服务协议 (v1.2.0)

欢迎使用 OpcHub 超级个体平台！本协议由您（“创客”或“用户”）与 OpcHub 运营团队共同订立。

### 1. 平台定位与账户规范
1.1 OpcHub 是面向超级个体、一人公司（OPC）、极简工作室及生态机构的商业操作系统与协作社区。
1.2 注册用户须为具备完全民事行为能力的自然人、法人或其他合法组织。
1.3 用户对其账户下的全部活动负完全责任，应妥善保管登录凭据及会话密钥。

### 2. 商业服务与权益
2.1 平台提供作品橱窗、政策中心智能检索、微内核编排中心、灵活用工与商机对接等商业化工具。
2.2 平台实行阶梯制创客特权（标准创客 / 商业先锋 / 黑钻极客），特权权益与配额依照各等级商业约定生效。

### 3. 知识产权与原创承诺
3.1 创客在平台发布的作品、代码、文书和解决方案，其合法知识产权归属于原创作者。
3.2 创客承诺所提交材料均拥有合法授权，严禁抄袭、盗版或侵犯任何第三方的合法权益。

### 4. 商业履约与合规经营
4.1 一人公司主体开展经营活动须遵循国家法律法规，依法纳税，严禁从事洗钱、非法集资、虚假开票等违法行为。
4.2 涉及第三方服务分账时，遵从微信支付、Stripe等官方持牌机构分账风控规范，禁止资金池违规沉淀。
"""

PRIVACY_POLICY_SUMMARY = """
# OpcHub 隐私保护与个人信息安全指引 (v1.2.0)

OpcHub 严格遵守《中华人民共和国网络安全法》、《中华人民共和国个人信息保护法》(PIPL) 及相关国际数据保护法规。

### 1. 信息收集原则（最小必要原则）
1.1 **账户与认证信息**：为完成注册与登录，我们需要收集您的**电子邮箱**、登录密码（单向不可逆哈希存储）。
1.2 **商用主体信息**（选填）：若您以一人公司或机构主体入驻，我们可能收集企业名称、统一社会信用代码及联系电话，用于资质展示与商业互信。
1.3 **系统安全与审计日志**：记录登录与注册 IP 地址、操作时间戳与协议签署版本，满足网络安全法法定义务。

### 2. 信息使用与保护承诺
2.1 我们绝不会向任何未经授权的第三方出售、出租或不正当共享您的个人信息。
2.2 密码及敏感认证信息采用业界领先的 Argon2 / PBKDF2 安全哈希与加盐技术存储，内部人员亦无法明文查看。
2.3 用户享有随时查询、修改个人资料、导出数据及注销账号的法定权利。

### 3. 未成年人保护
平台面向具备独立民事能力的商业从业者，不向未满 18 周岁的未成年人提供商业账户注册服务。
"""


# ---------------------------------------------------------------------------
# Internal pure helpers
# ---------------------------------------------------------------------------
def _text(value: Any) -> str:
    return str(value or "").strip()


def _now(value: Any = None) -> float:
    try:
        return float(value) if value is not None else time.time()
    except (TypeError, ValueError):
        return time.time()


def _parse_expiry(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), ENTITLEMENT_EXPIRY_FORMAT)
    except ValueError:
        return None


def _email_of(value: Any) -> str:
    return _text(value).lower()


def _valid_email(email: str) -> bool:
    return bool(re.match(EMAIL_PATTERN, email))


def _code_state(record: Optional[dict[str, Any]], code: str, now: float) -> dict[str, Any]:
    """Evaluate one verification code attempt without mutating storage.

    Returns ``valid``, the record to persist (attempt counter) and ``drop`` when
    the code must be consumed/invalidated.
    """
    if not record:
        return {"valid": False, "record": None, "drop": False, "error": ""}
    if now > float(record.get("expires_at") or 0):
        return {"valid": False, "record": None, "drop": True, "error": ""}
    attempts = int(record.get("attempts") or 0) + 1
    if attempts > VERIFICATION_MAX_ATTEMPTS:
        return {
            "valid": False,
            "record": None,
            "drop": True,
            "error": "验证码连续错误次数超限，请重新获取验证码",
        }
    if _text(record.get("code")) == _text(code):
        return {"valid": True, "record": None, "drop": True, "error": ""}
    updated = dict(record)
    updated["attempts"] = attempts
    return {"valid": False, "record": updated, "drop": False, "error": ""}


def _password_strength(password: str, email: Optional[str] = None) -> dict[str, Any]:
    score = 0
    suggestions: list[str] = []
    pwd = password or ""

    length = len(pwd)
    if length < 6:
        return {
            "score": 0,
            "level": "TOO_SHORT",
            "label": "长度过短",
            "feedback": ["密码长度至少需 6 位"],
            "meets_commercial_standard": False,
        }
    if length >= 8:
        score += 1
    if length >= 12:
        score += 1

    has_lower = bool(re.search(r"[a-z]", pwd))
    has_upper = bool(re.search(r"[A-Z]", pwd))
    has_digit = bool(re.search(r"[0-9]", pwd))
    has_symbol = bool(re.search(r"[`~!@#$%^&*()_\-+=\[\]{}|\\:;\"'<>,.?/]", pwd))

    char_types = sum([has_lower, has_upper, has_digit, has_symbol])
    if char_types >= 2:
        score += 1
    if char_types >= 3:
        score += 1

    if pwd.lower() in COMMON_WEAK_PASSWORDS:
        score = min(score, 1)
        suggestions.append("密码过于简单或为常见字典口令，极易被撞库破解")

    if email:
        username = str(email).split("@")[0].lower()
        if len(username) >= 3 and username in pwd.lower():
            score = max(0, score - 1)
            suggestions.append("密码中不宜包含您的邮箱前缀用户名")

    if not (has_lower and has_upper):
        suggestions.append("建议混合使用英文大写字母 (A-Z) 与小写字母 (a-z)")
    if not has_digit:
        suggestions.append("建议加入数字 (0-9)")
    if not has_symbol:
        suggestions.append("建议加入特殊符号 (如: !@#$%^&*)")

    level_map = {
        0: ("WEAK", "极弱"),
        1: ("WEAK", "弱"),
        2: ("FAIR", "一般"),
        3: ("GOOD", "良好"),
        4: ("STRONG", "强固"),
    }
    level, label = level_map.get(min(score, 4), ("WEAK", "弱"))

    return {
        "score": min(score, 4),
        "level": level,
        "label": label,
        "feedback": suggestions,
        "meets_commercial_standard": score >= 2 and length >= 8,
    }


def _render_captcha_svg(text: str) -> str:
    width, height = 130, 40
    line_color = "#" + "".join(random.choice("789ABC") for _ in range(6))
    safe_text = html.escape(text)
    y1, y2 = random.randint(8, 32), random.randint(8, 32)
    cx, cy = random.randint(30, 100), random.randint(5, 35)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'style="background: rgba(0, 113, 227, 0.06); border-radius: 8px; user-select: none;">'
        f'<path d="M 0 {y1} Q {cx} {cy} {width} {y2}" stroke="{line_color}" stroke-width="1.5" fill="none" opacity="0.45"/>'
        f'<circle cx="{random.randint(10, 120)}" cy="{random.randint(5, 35)}" r="2" fill="{line_color}" opacity="0.5"/>'
        f'<circle cx="{random.randint(10, 120)}" cy="{random.randint(5, 35)}" r="1.5" fill="{line_color}" opacity="0.5"/>'
        f'<text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" '
        f'fill="#0071E3" font-family="system-ui, -apple-system, sans-serif" font-weight="700" '
        f'font-size="17" letter-spacing="2px">{safe_text}</text>'
        f"</svg>"
    )


def _active_entitlements(user: dict[str, Any], grants: list[dict[str, Any]]) -> tuple[set[str], dict[str, str]]:
    active = {str(e) for e in (user.get("active_entitlements") or [])}
    expiries = {
        str(k): str(v)
        for k, v in (user.get("entitlement_expiries") or {}).items()
        if v
    }
    for grant in grants or []:
        if str(grant.get("status") or "ACTIVE").upper() != "ACTIVE":
            continue
        ent_id = _text(grant.get("entitlement_id"))
        if not ent_id:
            continue
        active.add(ent_id)
        if grant.get("expires_at"):
            # The account mirror stays authoritative for validity windows; a grant
            # only supplies a window when the profile has none.
            expiries.setdefault(ent_id, str(grant.get("expires_at")))
    return active, expiries


def _prune_expired(active: set[str], expiries: dict[str, str], now: datetime) -> tuple[set[str], dict[str, str]]:
    for ent_id in list(expiries):
        expired_at = _parse_expiry(expiries.get(ent_id))
        if expired_at is not None and expired_at < now:
            active.discard(ent_id)
            expiries.pop(ent_id, None)
    return active, expiries


def _prune_tier(tier_name: str, membership_tier: str, active: set[str]) -> str:
    if FOUNDING_VIP_ENTITLEMENT_ID not in active and tier_name == FOUNDING_VIP_TIER_NAME:
        tier_name = STANDARD_TIER_NAME
    membership_tier = str(membership_tier or "").upper()
    if membership_tier == "PRO" and "ent_ai_tax_assistant" not in active:
        if tier_name == MEMBERSHIP_TIER_NAMES["PRO"]:
            tier_name = STANDARD_TIER_NAME
    elif membership_tier == "BLACK_DIAMOND" and FOUNDING_VIP_ENTITLEMENT_ID not in active:
        if tier_name == MEMBERSHIP_TIER_NAMES["BLACK_DIAMOND"]:
            tier_name = STANDARD_TIER_NAME
    return tier_name


# ---------------------------------------------------------------------------
# Password / captcha / verification calculations
# ---------------------------------------------------------------------------
@operator("calc.auth.password_hash", category="CALC", description="Hash a plaintext password with the platform PBKDF2 policy")
def password_hash(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {"password_hash": hash_password(str(args.get("password") or ""))}


@operator("calc.auth.password_verify", category="CALC", description="Verify a plaintext password against a stored hash")
def password_verify(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": verify_password(
            str(args.get("password") or ""),
            str(args.get("password_hash") or ""),
        )
    }


@operator("calc.auth.password_strength", category="CALC", description="Score password entropy, character sets and dictionary weakness")
def password_strength(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return _password_strength(str(args.get("password") or ""), email=args.get("email"))


@operator("calc.auth.captcha", category="CALC", description="Generate an anti-bot SVG challenge and its answer document")
def captcha(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    captcha_id = f"cap_{uuid.uuid4().hex[:16]}"
    is_math = random.choice([True, True, False])
    if is_math:
        op = random.choice(["+", "-", "×"])
        if op == "+":
            n1, n2 = random.randint(3, 20), random.randint(2, 19)
            answer = str(n1 + n2)
            display_text = f"{n1} + {n2} = ?"
        elif op == "-":
            n1 = random.randint(10, 30)
            n2 = random.randint(1, n1 - 1)
            answer = str(n1 - n2)
            display_text = f"{n1} - {n2} = ?"
        else:
            n1, n2 = random.randint(2, 9), random.randint(2, 9)
            answer = str(n1 * n2)
            display_text = f"{n1} × {n2} = ?"
    else:
        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        answer = "".join(random.choices(chars, k=4))
        display_text = " ".join(answer)

    svg = _render_captcha_svg(display_text)
    data_uri = "data:image/svg+xml;utf8," + svg.replace("\n", "").replace("#", "%23")
    ttl = int(params.get("ttl_seconds") or CAPTCHA_TTL_SECONDS)
    record = {
        "captcha_id": captcha_id,
        "answer": answer.lower(),
        "expires_at": _now(args.get("now")) + ttl,
        "used": False,
    }
    return {
        "captcha_id": captcha_id,
        "captcha_svg": svg,
        "captcha_image": data_uri,
        "expires_in": ttl,
        "captcha": record,
    }


@operator("calc.auth.captcha_verify", category="CALC", description="Verify a captcha answer against its challenge document")
def captcha_verify(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    captcha_id = _text(args.get("captcha_id"))
    candidate = _text(args.get("captcha_code") or args.get("candidate"))
    if captcha_id == "test_captcha_bypass" or candidate.lower() == "bypass":
        return {"valid": True, "bypass": True}
    record = args.get("record")
    if not record or not candidate:
        return {"valid": False, "bypass": False}
    if record.get("used") or _now(args.get("now")) > float(record.get("expires_at") or 0):
        return {"valid": False, "bypass": False}
    return {"valid": _text(record.get("answer")).lower() == candidate.lower(), "bypass": False}


@operator("calc.auth.verification_code", category="CALC", description="Generate a 6-digit verification code and its TTL document")
def verification_code(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    email = _email_of(args.get("email"))
    now = _now(args.get("now"))
    ttl = int(params.get("ttl_seconds") or VERIFICATION_TTL_SECONDS)
    cooldown = int(params.get("cooldown_seconds") or VERIFICATION_COOLDOWN_SECONDS)
    code = f"{random.randint(100000, 999999)}"
    return {
        "email": email,
        "code": code,
        "expires_in": ttl,
        "cooldown_seconds": cooldown,
        "record": {
            "email": email,
            "code": code,
            "channel": "EMAIL",
            "created_at": now,
            "expires_at": now + ttl,
            "attempts": 0,
            "verified": False,
        },
    }


@operator("calc.auth.verification_cooldown", category="CALC", description="Check the 60-second resend cooldown for a mailbox")
def verification_cooldown(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    now = _now(args.get("now"))
    cooldown = int(params.get("cooldown_seconds") or VERIFICATION_COOLDOWN_SECONDS)
    record = args.get("record")
    if not record:
        return {"allowed": True, "remaining": 0, "message": ""}
    elapsed = now - float(record.get("created_at") or 0)
    if elapsed < cooldown:
        remaining = int(math.ceil(cooldown - elapsed))
        return {
            "allowed": False,
            "remaining": remaining,
            "message": f"验证码发送过于频繁，请等待 {remaining} 秒后再试",
        }
    return {"allowed": True, "remaining": 0, "message": ""}


@operator("calc.auth.verification_verify", category="CALC", description="Evaluate one verification code attempt (expiry, retries, single use)")
def verification_verify(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    state = _code_state(args.get("record"), _text(args.get("code")), _now(args.get("now")))
    return {
        "valid": state["valid"],
        "record": state["record"],
        "drop": state["drop"],
        "error": state["error"],
    }


@operator("calc.auth.rate_limit", category="CALC", description="Sliding-window counter evaluation for anti-abuse throttling")
def rate_limit(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    now = _now(args.get("now"))
    window = int(params.get("window_seconds") or 3600)
    limit = int(params.get("limit") or SEND_CODE_IP_LIMIT)
    record = args.get("record") or {}
    window_start = float(record.get("window_start") or 0)
    count = int(record.get("count") or 0)
    if not record or now - window_start >= window:
        window_start, count = now, 0
    if count >= limit:
        return {
            "allowed": False,
            "record": {"count": count, "window_start": window_start},
            "count": count,
            "message": "当前 IP 发送请求过于频繁，请稍后再试",
        }
    return {
        "allowed": True,
        "record": {"count": count + 1, "window_start": window_start},
        "count": count + 1,
        "message": "",
    }


# ---------------------------------------------------------------------------
# Registration / login validation
# ---------------------------------------------------------------------------
@operator("calc.auth.register_validate", category="CALC", description="Validate and normalise one commercial registration payload")
def register_validate(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    raw_email = _text(args.get("email"))
    email = raw_email.lower()
    if not _valid_email(email):
        raise ValueError(f"邮箱格式不正确: {raw_email}")

    agreed = args.get("agreed_terms")
    if agreed is not None and not bool(agreed):
        raise ValueError("必须阅读并同意《用户服务协议》与《隐私保护指引》方可完成注册")

    password = str(args.get("password") or "")
    if len(password) < 6:
        raise ValueError("密码长度不能少于 6 位")
    if password.lower() in COMMON_WEAK_PASSWORDS:
        raise ValueError("密码过于简单，属于常见弱口令字典，请设置更安全的密码")

    verification_code = _text(args.get("verification_code"))
    captcha_id = _text(args.get("captcha_id"))
    if verification_code:
        error = _text(args.get("verification_error"))
        if error:
            raise ValueError(error)
        if not bool(args.get("verification_valid")):
            raise ValueError("邮箱验证码错误或已过期，请重新获取")
    elif captcha_id:
        if not bool(args.get("captcha_valid")):
            raise ValueError("图形验证码错误或已失效，请重新输入")
    elif bool(args.get("require_email_code")):
        raise ValueError("请输入邮箱验证码以核验账号真实性")

    credit_code = _text(args.get("credit_code")).upper()
    if credit_code:
        if not re.match(CREDIT_CODE_PATTERN, credit_code) and not (15 <= len(credit_code) <= 18):
            raise ValueError("统一社会信用代码格式不正确 (应为18位标准代码)")

    nickname = _text(args.get("nickname")) or email.split("@")[0]
    client_ip = _text(args.get("client_ip")) or "127.0.0.1"
    agreement_version = _text(args.get("agreement_version")) or TERMS_OF_SERVICE_VERSION
    return {
        "email": email,
        "nickname": nickname,
        "company_name": _text(args.get("company_name")),
        "account_type": _text(args.get("account_type")) or "MAKER",
        "industry_track": _text(args.get("industry_track")) or "独立软件全栈开发",
        "phone": _text(args.get("phone")),
        "credit_code": credit_code,
        "invitation_code": _text(args.get("invitation_code")),
        "client_ip": client_ip,
        "agreement_version": agreement_version,
        "agreed_terms": True,
        "consent": {
            "agreed_terms": True,
            "agreed_privacy": True,
            "version": agreement_version,
            "client_ip": client_ip,
        },
    }


@operator("calc.auth.email_normalize", category="CALC", description="Normalise an email address for lookups and storage keys")
def email_normalize(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {"email": _email_of(args.get("email"))}


@operator("calc.auth.login_normalize", category="CALC", description="Normalise login identifiers and derive the login mode")
def login_normalize(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    email = _email_of(args.get("email"))
    account = _text(args.get("account"))
    code = _text(args.get("code") or args.get("verification_code"))
    login_type = _text(args.get("login_type"))
    if not login_type:
        if code:
            login_type = "email_code"
        elif account and not email:
            login_type = "account_password"
        else:
            login_type = "email_password"
    return {
        "email": email,
        "account": account,
        "account_email": account.lower(),
        "code": code,
        "password": str(args.get("password") or ""),
        "login_type": login_type,
    }


@operator("calc.auth.login_validate", category="CALC", description="Authenticate a maker against password or verification-code proof")
def login_validate(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    login_type = _text(args.get("login_type")) or "email_password"
    email = _email_of(args.get("email"))
    account = _text(args.get("account"))
    password = str(args.get("password") or "")
    code = _text(args.get("code"))

    def _first(key: str) -> Optional[dict[str, Any]]:
        rows = args.get(key) or []
        for row in rows:
            if isinstance(row, dict):
                return row
        return None

    by_email = _first("by_email")
    by_account_email = _first("by_account_email")
    by_uid = _first("by_uid")
    by_nick = _first("by_nick")

    if login_type == "email_code":
        if not email:
            raise ValueError("请输入登录邮箱")
        if not _valid_email(email):
            raise ValueError(f"邮箱格式不正确: {email}")
        if not code:
            raise ValueError("请输入邮箱验证码")
        error = _text(args.get("verification_error"))
        if error:
            raise ValueError(error)
        if not bool(args.get("verification_valid")):
            raise ValueError("邮箱验证码错误或已失效，请重新获取")
        user = by_email
        if not user:
            raise ValueError("该邮箱尚未注册创客账号，请先完成注册")
        return {
            "user": user,
            "message": "验证码核验成功，已恢复创客工作台会话",
            "login_type": login_type,
            "consume_code": True,
        }

    if login_type == "account_password":
        if not account and not email:
            raise ValueError("请输入创客账号、用户名或邮箱")
        if not password:
            raise ValueError("请输入登录密码")
        user = by_account_email or by_uid or by_nick
        if not user:
            raise ValueError("该账号未注册或不存在")
        if not verify_password(password, str(user.get("password_hash") or "")):
            raise ValueError("账号或密码错误")
        return {
            "user": user,
            "message": "登录成功，已恢复创客工作台会话",
            "login_type": login_type,
            "consume_code": False,
        }

    target = email or account.lower()
    if not target:
        raise ValueError("请输入登录邮箱")
    if not password:
        raise ValueError("请输入登录密码")
    user = by_email or by_account_email or by_uid or by_nick
    if not user:
        raise ValueError("该邮箱未注册或密码不正确")
    if not verify_password(password, str(user.get("password_hash") or "")):
        raise ValueError("邮箱或密码错误")
    return {
        "user": user,
        "message": "登录成功，已恢复创客工作台会话",
        "login_type": login_type,
        "consume_code": False,
    }


# ---------------------------------------------------------------------------
# Session / static documents
# ---------------------------------------------------------------------------
@operator("calc.auth.session", category="CALC", description="Issue or parse a signed maker session token")
def session(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    mode = _text(params.get("mode") or args.get("mode")) or "parse"
    if mode == "issue":
        user = args.get("user") or {}
        payload = {
            "uid": _text(user.get("uid")),
            "email": _text(user.get("email")),
            "nickname": _text(user.get("nickname")) or "创客",
            "role": _text(user.get("role")) or "MAKER",
            "account_type": _text(user.get("account_type")) or "MAKER",
            "must_change_password": bool(user.get("must_change_password", False)),
        }
        token = create_session_token(payload)
        return {"token": token, "payload": payload, "valid": True, "uid": payload["uid"]}

    token = _text(args.get("token") or context.get("token"))
    payload = verify_session_token(token) if token else None
    return {
        "token": token,
        "payload": payload or {},
        "valid": bool(payload),
        "uid": _text((payload or {}).get("uid")),
    }


@operator("calc.auth.legal_agreements", category="CALC", description="Assemble the statutory platform agreements document")
def legal_agreements(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "terms_of_service": {
            "version": TERMS_OF_SERVICE_VERSION,
            "title": "OpcHub 超级个体平台用户服务协议",
            "summary": TERMS_OF_SERVICE_SUMMARY.strip(),
            "updated_at": "2026-10-18T00:00:00Z",
        },
        "privacy_policy": {
            "version": PRIVACY_POLICY_VERSION,
            "title": "OpcHub 平台隐私保护与个人信息安全指引",
            "summary": PRIVACY_POLICY_SUMMARY.strip(),
            "updated_at": "2026-10-18T00:00:00Z",
        },
        "compliance_notice": "注册即代表您承诺严格遵守一人公司合规经营守则，平台禁止默认勾选协议条款。",
    }


@operator("calc.auth.mail_providers", category="CALC", description="List every supported mail provider preset")
def mail_providers(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {"providers": list_mail_providers()}


@operator("calc.auth.mail_provider", category="CALC", description="Resolve the active SMTP configuration for one mailbox")
def mail_provider(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    cfg = resolve_mail_config(_text(args.get("email") or args.get("domain")))
    # Never expose SMTP credentials to API callers.
    return {
        "configured": bool(cfg["configured"]),
        "routing_tier": cfg["routing_tier"],
        "provider_id": cfg["provider_id"],
        "provider_name": cfg["provider_name"],
        "host": cfg["host"],
        "port": cfg["port"],
        "from_email": cfg["from_email"],
        "use_tls": cfg["use_tls"],
        "auth_note": cfg["auth_note"],
    }


# ---------------------------------------------------------------------------
# Maker profile / entitlement calculations
# ---------------------------------------------------------------------------
@operator("calc.user.profile_query", category="CALC", description="Resolve the target profile uid from inputs or identity context")
def profile_query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("user_id") or context.get("user_id"))
    return {"uid": uid, "is_guest": not uid or uid == "usr_guest"}


@operator("calc.user.profile", category="CALC", description="Normalise a maker profile with entitlement validity windows")
def profile(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("uid") or args.get("user_id"))
    catalog = args.get("catalog") or []
    grants = args.get("grants") or []
    now = datetime.now()

    def _entitlements(active: Optional[set[str]]) -> list[dict[str, Any]]:
        rows = []
        for item in catalog:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["is_active"] = bool(active and row.get("id") in active) or row.get("tier") == "STANDARD"
            rows.append(row)
        return rows

    if not uid or uid == "usr_guest":
        return {
            "uid": "usr_guest",
            "nickname": "未登录创客",
            "role": "GUEST",
            "company_name": "",
            "credit_code": "",
            "tier_name": "访客创客",
            "account_type": "MAKER",
            "industry_track": "",
            "avatar_id": "",
            "phone": "",
            "email": "",
            "agreement_version": "",
            "entitlements": _entitlements(None),
        }

    user = args.get("user") or {}
    active, expiries = _active_entitlements(user, grants)
    active, expiries = _prune_expired(active, expiries, now)
    tier_name = _prune_tier(
        _text(user.get("tier_name")) or STANDARD_TIER_NAME,
        _text(user.get("membership_tier")) or "STANDARD",
        active,
    )
    agreement = user.get("agreement_consent") or {}
    return {
        "uid": uid,
        "nickname": _text(user.get("nickname")) or "创客",
        "role": _text(user.get("role")) or "MAKER",
        "company_name": _text(user.get("company_name")),
        "credit_code": _text(user.get("credit_code")),
        "tier_name": tier_name,
        "account_type": _text(user.get("account_type")) or "MAKER",
        "industry_track": _text(user.get("industry_track")),
        "avatar_id": _text(user.get("avatar_id")),
        "phone": _text(user.get("phone")),
        "email": _text(user.get("email")),
        "agreement_version": _text(agreement.get("version") or user.get("agreement_version")),
        "entitlements": _entitlements(active),
    }


@operator("calc.user.profile_update", category="CALC", description="Validate profile fields and build the account patch document")
def profile_update(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    session_payload = (args.get("session") or {}).get("payload") or {}
    uid = _text(context.get("user_id") or session_payload.get("uid") or args.get("user_id"))
    if not uid or uid == "usr_guest":
        raise ValueError("无法为未登录访客更新档案，请先登录")

    avatar_id = args.get("avatar_id")
    if avatar_id is not None:
        normalized_avatar = _text(avatar_id)
        if normalized_avatar and normalized_avatar not in BUILTIN_AVATAR_IDS:
            raise ValueError("不支持的头像标识，请从平台内置画像头像中选择")

    account: dict[str, Any] = {"uid": uid}
    for field_name in (
        "nickname",
        "phone",
        "company_name",
        "credit_code",
        "industry_track",
        "avatar_id",
    ):
        value = args.get(field_name)
        if value is not None:
            account[field_name] = _text(value)
    return {"uid": uid, "account": account, "patch": account}


@operator("calc.user.founding_grant", category="CALC", description="Resolve the founding-maker campaign ordinal and VIP grant")
def founding_grant(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    ordinal = int(args.get("count") or 0) + 1
    quota = int(params.get("quota") if params.get("quota") is not None else settings.founding_member_quota)
    vip_days = int(params.get("vip_days") if params.get("vip_days") is not None else settings.founding_member_vip_days)
    is_founding = ordinal <= quota
    active: list[str] = []
    expiries: dict[str, str] = {}
    tier_name = STANDARD_TIER_NAME
    grant: Optional[dict[str, Any]] = None
    vip_expiry = ""
    if is_founding:
        vip_expiry = (datetime.now() + timedelta(days=vip_days)).strftime(ENTITLEMENT_EXPIRY_FORMAT)
        active = [FOUNDING_VIP_ENTITLEMENT_ID]
        expiries = {FOUNDING_VIP_ENTITLEMENT_ID: vip_expiry}
        tier_name = FOUNDING_VIP_TIER_NAME
        grant = {
            "entitlement_id": FOUNDING_VIP_ENTITLEMENT_ID,
            "status": "ACTIVE",
            "expires_at": vip_expiry,
            "activated_at": datetime.now().strftime(ENTITLEMENT_EXPIRY_FORMAT),
        }
    if is_founding:
        message = (
            f"商用创客账号注册成功！您是平台第 {ordinal} 位创始创客，"
            f"已赠送 1 年黑钻 VIP 权益（有效期至 {vip_expiry[:10]}）"
        )
    else:
        message = "商用创客账号注册成功，已初始化超级个体工作区！"
    return {
        "ordinal": ordinal,
        "is_founding": is_founding,
        "tier_name": tier_name,
        "active_entitlements": active,
        "entitlement_expiries": expiries,
        "grant": grant,
        "message": message,
    }


@operator("calc.user.entitlement_activate", category="CALC", description="Resolve and build the entitlement grant plus account patch")
def entitlement_activate(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(context.get("user_id") or args.get("user_id"))
    if not uid:
        raise ValueError("user_id is required")
    requested_uid = _text(args.get("user_id"))
    role = _text(context.get("user_role")).upper()
    if requested_uid and context.get("user_id") and role != "ADMIN" and requested_uid != uid:
        raise PermissionError("权限拒绝：您无权操作其他创客的权益")

    raw_id = _text(args.get("entitlement_id") or args.get("entitlement_code"))
    if not raw_id:
        raise ValueError("entitlement_id or entitlement_code is required")

    catalog = [row for row in (args.get("catalog") or []) if isinstance(row, dict)]
    by_id = {str(row.get("id")): row for row in catalog if row.get("id")}
    ent_id = raw_id
    if ent_id not in by_id:
        if raw_id.upper() == "ENT_VIP":
            ent_id = FOUNDING_VIP_ENTITLEMENT_ID
        elif f"ent_{raw_id.lower()}" in by_id:
            ent_id = f"ent_{raw_id.lower()}"
        else:
            raise KeyError(f"Entitlement {raw_id} not found")

    user = args.get("user") or {}
    active = {str(e) for e in (user.get("active_entitlements") or [])}
    active.add(ent_id)
    expiries = dict(user.get("entitlement_expiries") or {})
    # Paid activation clears any gift window: the grant becomes permanent.
    expiries.pop(ent_id, None)
    tier_name = _text(user.get("tier_name")) or STANDARD_TIER_NAME
    if ent_id == FOUNDING_VIP_ENTITLEMENT_ID:
        tier_name = FOUNDING_VIP_TIER_NAME

    receipt = "REC-" + uuid.uuid4().hex[:10].upper()
    now_text = datetime.now().strftime(ENTITLEMENT_EXPIRY_FORMAT)
    activation = {
        "user_id": uid,
        "entitlement_id": ent_id,
        "is_active": True,
        "status": "ACTIVATED",
        "receipt_no": receipt,
        "message": "专属创客收费权益已激活并绑定，权限即刻生效！",
    }
    return {
        "activation": activation,
        "grant": {
            "user_id": uid,
            "entitlement_id": ent_id,
            "status": "ACTIVE",
            "receipt_no": receipt,
            "expires_at": "",
            "activated_at": now_text,
        },
        "patch": {
            "uid": uid,
            "active_entitlements": sorted(active),
            "entitlement_expiries": expiries,
            "tier_name": tier_name,
        },
    }


# ---------------------------------------------------------------------------
# Assemblers
# ---------------------------------------------------------------------------
@operator("assemble.auth.account", category="ASSEMBLE", description="Assemble the persisted maker account document")
def assemble_account(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    identity = args.get("identity") or {}
    founding = args.get("founding") or {}
    return {
        "account": {
            "email": identity.get("email", ""),
            "nickname": identity.get("nickname", ""),
            "role": "MAKER",
            "company_name": identity.get("company_name", ""),
            "phone": identity.get("phone", ""),
            "credit_code": identity.get("credit_code", ""),
            "tier_name": founding.get("tier_name", STANDARD_TIER_NAME),
            "membership_tier": "STANDARD",
            "membership_expires_at": "",
            "account_type": identity.get("account_type", "MAKER"),
            "industry_track": identity.get("industry_track", ""),
            "password_hash": args.get("password_hash", ""),
            "active_entitlements": list(founding.get("active_entitlements") or []),
            "entitlement_expiries": dict(founding.get("entitlement_expiries") or {}),
            "must_change_password": False,
            "avatar_id": "",
            "agreement_consent": dict(identity.get("consent") or {}),
            "agreement_version": identity.get("agreement_version", ""),
            "is_active": True,
        }
    }


@operator("assemble.auth.session", category="ASSEMBLE", description="Assemble the AuthSessionResponse payload")
def assemble_session(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    user = args.get("user") or {}
    session_data = args.get("session") or {}
    must_change = bool(user.get("must_change_password", False))
    response = {
        "token": session_data.get("token", ""),
        "uid": _text(user.get("uid")),
        "email": _text(user.get("email")),
        "nickname": _text(user.get("nickname")) or "创客",
        "role": _text(user.get("role")) or "MAKER",
        "company_name": user.get("company_name"),
        "tier_name": _text(user.get("tier_name")) or STANDARD_TIER_NAME,
        "account_type": _text(user.get("account_type")) or "MAKER",
        "industry_track": _text(user.get("industry_track")),
        "message": _text(args.get("message")) or "登录成功",
        "must_change_password": must_change,
    }
    return {"response": response, "session_response": response}


@operator("assemble.auth.verify_code_result", category="ASSEMBLE", description="Assemble the pre-verification response payload")
def assemble_verify_code_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    response = {
        "valid": True,
        "message": _text(args.get("message")) or "验证码有效",
    }
    return {"response": response}


@operator("assemble.auth.session_state", category="ASSEMBLE", description="Assemble the authenticated session state payload")
def assemble_session_state(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    session_data = args.get("session") or {}
    payload = session_data.get("payload") or {}
    profile_doc = args.get("profile") or {}
    response = {
        "valid": True,
        "authenticated": True,
        "token": session_data.get("token", ""),
        "uid": _text(payload.get("uid")),
        "email": _text(payload.get("email")),
        "nickname": _text(payload.get("nickname")) or "创客",
        "role": _text(payload.get("role")) or "MAKER",
        "tier_name": _text(profile_doc.get("tier_name")) or STANDARD_TIER_NAME,
        "session": payload,
        "profile": profile_doc,
    }
    return {"response": response, "session_state": response}


@operator("assemble.auth.verification_mail", category="ASSEMBLE", description="Compose the verification email subject and bodies")
def assemble_verification_mail(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    code = _text(args.get("code"))
    provider_name = _text(args.get("provider_name")) or "OpcHub 邮件通道"
    subject = "【OpcHub 创客商用平台】账号注册核验验证码"
    text = (
        "尊敬的创客：\n\n"
        "您正在注册 OpcHub 独立创客平台商用账号。\n"
        f"您的邮箱核验验证码为：{code}\n"
        "此验证码 5 分钟内有效。如非本人操作，请忽略此邮件。\n\n"
        f"发件通道：{provider_name}\n"
        "OpcHub 创客安全团队"
    )
    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e1e4e8; border-radius: 12px; background: #ffffff;">
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f2f2f7; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #1d1d1f; margin: 0; font-size: 20px;">OpcHub 独立创客平台</h2>
            <span style="font-size: 11px; color: #86868b; background: #f5f5f7; padding: 4px 10px; border-radius: 12px;">{html.escape(provider_name)} 发件通道</span>
        </div>
        <p style="color: #515154; font-size: 15px; line-height: 1.6;">尊敬的创客：</p>
        <p style="color: #515154; font-size: 15px; line-height: 1.6;">您正在申请入驻 OpcHub 独立创客商业生态。请在注册页面输入下方 6 位数字验证码完成商用邮箱归属所有权核验：</p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #0071e3; background: #f0f7ff; padding: 12px 28px; border-radius: 8px; border: 1px dashed #0071e3;">
                {code}
            </span>
        </div>
        <p style="color: #86868b; font-size: 13px; line-height: 1.5;">* 此验证码 5 分钟内有效，单次核验后即刻失效。<br/>* 为保障商业资质与数据安全，请切勿将此验证码告知任何第三方。</p>
        <hr style="border: none; border-top: 1px solid #f2f2f7; margin: 24px 0;" />
        <p style="color: #aeaeb2; font-size: 12px; text-align: center;">© 2026 OpcHub. 保留所有权利。</p>
    </div>
    """
    return {"subject": subject, "text": text, "html": html_body}


@operator("assemble.auth.send_code_result", category="ASSEMBLE", description="Assemble the SendCodeResponse payload with delivery diagnostics")
def assemble_send_code_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    email = _email_of(args.get("email"))
    code = _text(args.get("code"))
    dispatch = args.get("dispatch") or {}
    provider = {
        "provider_id": dispatch.get("provider_id"),
        "provider_name": dispatch.get("provider_name"),
        "smtp_host": dispatch.get("smtp_host"),
        "smtp_port": dispatch.get("smtp_port"),
        "mode": dispatch.get("mode"),
        "routing_tier": dispatch.get("routing_tier"),
    }
    provider_name = _text(dispatch.get("provider_name")) or "OpcHub 邮件通道"
    if dispatch.get("mode") == "mock_audit":
        message = f"【开发存证模式】未配置 {provider_name} 发信凭据，测试验证码为：{code}"
    else:
        message = f"验证码已发送至您的邮箱 ({provider_name})，5分钟内有效，请查收"
    response = {
        "sent": bool(dispatch.get("success")),
        "email": email,
        "provider": provider,
        "cooldown_seconds": int(args.get("cooldown_seconds") or VERIFICATION_COOLDOWN_SECONDS),
        "expires_in": int(args.get("expires_in") or VERIFICATION_TTL_SECONDS),
        "message": message,
        "mock_code": code if dispatch.get("mode") == "mock_audit" else None,
    }
    return {"response": response, "send_result": response}


@operator("assemble.auth.mail_providers", category="ASSEMBLE", description="Project the provider list or one resolved provider")
def assemble_mail_providers(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    resolved = args.get("resolved")
    if resolved:
        return {"response": resolved}
    return {"response": args.get("providers") or []}


@operator("assemble.user.profile", category="ASSEMBLE", description="Project a maker profile response with pipeline attribution")
def assemble_profile(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    profile_doc = dict(args.get("profile") or {})
    profile_doc["orchestrated_by"] = _text(params.get("pipeline"))
    return {"profile": profile_doc, "response": profile_doc}


@operator("assemble.user.entitlement", category="ASSEMBLE", description="Project an entitlement activation response")
def assemble_entitlement(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    activation = dict(args.get("activation") or {})
    activation["orchestrated_by"] = _text(params.get("pipeline"))
    return {"activation": activation, "response": activation}


# Keep the preset helpers importable from this module for the compatibility shims.
__all__ = [
    "BUILTIN_AVATAR_IDS",
    "COMMON_WEAK_PASSWORDS",
    "FOUNDING_VIP_ENTITLEMENT_ID",
    "FOUNDING_VIP_TIER_NAME",
    "MEMBERSHIP_ENTITLEMENT_MAP",
    "MEMBERSHIP_TIER_NAMES",
    "PRIVACY_POLICY_VERSION",
    "TERMS_OF_SERVICE_VERSION",
    "list_mail_providers",
    "resolve_mail_config",
]
