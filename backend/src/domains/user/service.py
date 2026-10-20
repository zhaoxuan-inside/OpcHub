"""User, authentication, and entitlement management service."""
import re
import uuid
from typing import Dict, Set, Optional, Any, List

from src.core.config import settings
from src.core.security import hash_password, verify_password, create_session_token, verify_session_token
from src.infrastructure.database.repository import db_repository
from src.domains.user.models import (
    EntitlementItem,
    MakerProfileResponse,
    UserProfileUpdateRequest,
    ChangePasswordRequest,
    EntitlementActivateRequest,
    EntitlementActivateResponse,
    UserRegisterRequest,
    UserLoginRequest,
    AuthSessionResponse,
)
from src.domains.user.verification import (
    captcha_service,
    email_verification_service,
    email_provider_registry,
    email_dispatcher,
    PasswordPolicyService,
    LegalAgreementsRepository,
)


class UserService:
    """Manages maker profile, authentication, and entitlements."""

    def __init__(self):
        self._active_entitlements: Set[str] = set()
        self._entitlements: Dict[str, EntitlementItem] = {}
        self._users_by_email: Dict[str, Dict[str, Any]] = {}
        self._users_by_uid: Dict[str, Dict[str, Any]] = {}
        self.require_email_code: bool = False
        self._seed_default_entitlements()
        self._ensure_builtin_admin()

    def _ensure_builtin_admin(self):
        """Idempotently provision the built-in administrator (RBAC §1.1).

        Credentials come from env (safe defaults); the account is flagged
        must_change_password and forced to rotate on first login.
        """
        admin_uid = "usr_admin_builtin"
        if admin_uid in self._users_by_uid:
            return
        admin = {
            "uid": admin_uid,
            "email": settings.admin_email.strip().lower(),
            "nickname": settings.admin_nickname,
            "role": "ADMIN",
            "company_name": "OpcHub 平台运营",
            "phone": "",
            "credit_code": "",
            "tier_name": "平台管理员",
            "password_hash": hash_password(settings.admin_initial_password),
            "active_entitlements": set(),
            "must_change_password": True,
        }
        self._users_by_uid[admin_uid] = admin
        self._users_by_email[admin["email"]] = admin

    @staticmethod
    def _record_from_db_user(db_user: Any) -> Dict[str, Any]:
        """Project a persisted User row into the service's in-memory record shape."""
        meta = db_user.metadata_payload or {}
        return {
            "uid": db_user.uid,
            "email": db_user.email,
            "nickname": db_user.nickname,
            "role": db_user.role,
            "company_name": db_user.company_name or "",
            "phone": meta.get("phone", ""),
            "credit_code": getattr(db_user, "unified_social_credit_code", None) or meta.get("credit_code", ""),
            "tier_name": meta.get("tier_name", "标准创客"),
            "account_type": meta.get("account_type", "MAKER"),
            "industry_track": meta.get("industry_track", ""),
            "password_hash": db_user.password_hash or "",
            "active_entitlements": set(meta.get("active_entitlements", [])),
            "must_change_password": bool(meta.get("must_change_password", False)),
        }

    async def hydrate_from_db(self) -> int:
        """Rebuild the in-memory user index from the canonical ``users`` table on startup."""
        rows = await db_repository.list_users()
        for db_user in rows:
            record = self._record_from_db_user(db_user)
            self._users_by_uid[record["uid"]] = record
            self._users_by_email[record["email"]] = record
        return len(rows)

    def _seed_default_entitlements(self):
        """Load entitlements catalog from external seed data file (zero hardcoded catalog data in code)."""
        import json
        from pathlib import Path

        search_paths = [
            Path("backend/data/seeds/entitlements.json"),
            Path("data/seeds/entitlements.json"),
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "entitlements.json",
        ]
        items_raw: List[Dict[str, Any]] = []
        for p in search_paths:
            if p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        items_raw = json.load(f)
                    break
                except Exception:
                    pass

        for raw in items_raw:
            eid = raw.get("id")
            if eid:
                self._entitlements[eid] = EntitlementItem(
                    id=eid,
                    name=raw.get("name", ""),
                    tier=raw.get("tier", "STANDARD"),
                    price_cny=float(raw.get("price_cny", 0.0)),
                    description=raw.get("description", ""),
                    is_active=(eid in self._active_entitlements) or bool(raw.get("is_active", False)),
                    quota_desc=raw.get("quota_desc", ""),
                )

    def validate_email(self, email: str) -> bool:
        """Validate standard email format."""
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email.strip()))

    def generate_captcha(self) -> Dict[str, Any]:
        """Generate a lightweight anti-bot SVG challenge."""
        return captcha_service.generate()

    def send_verification_code(
        self,
        email: str,
        captcha_id: Optional[str] = None,
        captcha_code: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send 6-digit email verification code with anti-bot check and rate limiting."""
        clean_email = email.strip().lower()
        if not self.validate_email(clean_email):
            raise ValueError(f"邮箱格式不正确: {email}")

        # If a captcha was requested or provided, enforce single-use verification
        if captcha_id:
            if not captcha_service.verify(captcha_id, captcha_code):
                raise ValueError("图形验证码错误或已失效，请重新输入")

        return email_verification_service.send_code(clean_email, client_ip=client_ip)

    def verify_email_code(self, email: str, code: str) -> bool:
        """Directly verify if the email verification code is valid."""
        return email_verification_service.verify_code(email, code)

    def evaluate_password_strength(self, password: str, email: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate password entropy, complexity, and compliance suggestions."""
        return PasswordPolicyService.evaluate(password, email=email)

    def get_legal_agreements(self) -> Dict[str, Any]:
        """Retrieve statutory platform user terms and privacy policy documents."""
        return LegalAgreementsRepository.get_agreements()

    def get_supported_mail_providers(self) -> List[Dict[str, Any]]:
        """List all supported commercial email providers and preset metadata."""
        return email_provider_registry.list_supported_providers()

    def resolve_mail_provider(self, email: str) -> Dict[str, Any]:
        """Resolve email provider preset and active configuration state."""
        return email_dispatcher.get_provider_config(email)

    async def register_by_email(self, req: UserRegisterRequest) -> AuthSessionResponse:
        """Register a new maker using email, password, and commercial validations."""
        email = req.email.strip().lower()
        if not self.validate_email(email):
            raise ValueError(f"邮箱格式不正确: {req.email}")

        # 1. Statutory Consent (网络安全法 / 个人信息保护法: 明确同意条款且禁止默认勾选)
        if not req.agreed_terms:
            raise ValueError("必须阅读并同意《用户服务协议》与《隐私保护指引》方可完成注册")

        # 2. Password Strength & Policy
        if len(req.password) < 6:
            raise ValueError("密码长度不能少于 6 位")

        if req.password.lower() in PasswordPolicyService.COMMON_WEAK_PASSWORDS:
            raise ValueError("密码过于简单，属于常见弱口令字典，请设置更安全的密码")

        # 3. Ownership Proof & Anti-Bot Protection
        if req.verification_code:
            # Primary commercial registration flow: Email verification code proves mailbox ownership.
            # Anti-bot captcha was already challenged and consumed during auth.send-code.
            if not email_verification_service.verify_code(email, req.verification_code):
                raise ValueError("邮箱验证码错误或已过期，请重新获取")
        elif req.captcha_id:
            # Fallback for flows where email verification code is not configured
            if not captcha_service.verify(req.captcha_id, req.captcha_code):
                raise ValueError("图形验证码错误或已失效，请重新输入")
        elif self.require_email_code:
            raise ValueError("请输入邮箱验证码以核验账号真实性")

        # 5. Commercial Identity & Credit Code validation
        credit_code = (req.credit_code or "").strip().upper()
        if credit_code:
            if not re.match(r"^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$", credit_code) and (
                len(credit_code) < 15 or len(credit_code) > 18
            ):
                raise ValueError("统一社会信用代码格式不正确 (应为18位标准代码)")

        # 6. Duplicate Check in DB & Memory
        db_user = await db_repository.get_user_by_email(email)
        if db_user is not None:
            raise ValueError("该邮箱已被注册，请直接登录")

        if email in self._users_by_email:
            raise ValueError("该邮箱已被注册，请直接登录")

        nickname = req.nickname.strip() if req.nickname else email.split("@")[0]
        company = req.company_name.strip() if req.company_name else ""
        account_type = req.account_type or "MAKER"
        industry_track = req.industry_track or "独立软件全栈开发"
        phone = (req.phone or "").strip()
        pwd_hash = hash_password(req.password)
        uid = str(uuid.uuid4())

        metadata = {
            "tier": "STANDARD",
            "tier_name": "标准创客",
            "account_type": account_type,
            "industry_track": industry_track,
            "phone": phone,
            "credit_code": credit_code,
            "invitation_code": req.invitation_code or "",
            "agreement_consent": {
                "agreed_terms": True,
                "agreed_privacy": True,
                "version": req.agreement_version,
                "client_ip": req.client_ip or "127.0.0.1",
            },
            "created_source": "COMMERCIAL_REG",
        }

        # 7. Persist to PostgreSQL database (Mandatory Commercial Strong Persistence)
        created_db_user = await db_repository.create_user(
            email=email,
            password_plain=req.password,
            nickname=nickname,
            company_name=company,
            role="MAKER",
            credit_code=credit_code if credit_code else None,
            metadata=metadata,
        )
        if created_db_user:
            uid = created_db_user.uid

        # 8. Save to in-memory cache
        user_record = {
            "uid": uid,
            "email": email,
            "nickname": nickname,
            "role": "MAKER",
            "company_name": company,
            "phone": phone,
            "credit_code": credit_code,
            "tier_name": "标准创客",
            "account_type": account_type,
            "industry_track": industry_track,
            "password_hash": pwd_hash,
            "active_entitlements": set(),
        }
        self._users_by_email[email] = user_record
        self._users_by_uid[uid] = user_record

        # 9. Issue signed token
        token = create_session_token({
            "uid": uid,
            "email": email,
            "nickname": nickname,
            "role": "MAKER",
            "account_type": account_type,
        })

        return AuthSessionResponse(
            token=token,
            uid=uid,
            email=email,
            nickname=nickname,
            role="MAKER",
            company_name=company,
            tier_name="标准创客",
            account_type=account_type,
            industry_track=industry_track,
            message="商用创客账号注册成功，已初始化超级个体工作区！",
        )

    async def _fetch_user_record_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        db_user = await db_repository.get_user_by_email(clean_email)
        if db_user is not None:
            return self._record_from_db_user(db_user)
        if clean_email in self._users_by_email:
            return self._users_by_email[clean_email]
        return None

    async def _fetch_user_record_by_account(self, account: str) -> Optional[Dict[str, Any]]:
        clean = account.strip()
        clean_lower = clean.lower()
        db_user = await db_repository.get_user_by_account(clean)
        if db_user is not None:
            return self._record_from_db_user(db_user)
        if clean_lower in self._users_by_email:
            return self._users_by_email[clean_lower]
        if clean in self._users_by_uid:
            return self._users_by_uid[clean]
        for u in self._users_by_uid.values():
            if u.get("nickname") == clean or u.get("email") == clean_lower:
                return u
        return None

    def _build_auth_session_response(
        self, user_record: Dict[str, Any], message: str = "登录成功，已恢复创客工作台会话"
    ) -> AuthSessionResponse:
        must_chg = bool(user_record.get("must_change_password", False))
        token = create_session_token({
            "uid": user_record["uid"],
            "email": user_record["email"],
            "nickname": user_record["nickname"],
            "role": user_record.get("role", "MAKER"),
            "account_type": user_record.get("account_type", "MAKER"),
            "must_change_password": must_chg,
        })
        return AuthSessionResponse(
            token=token,
            uid=user_record["uid"],
            email=user_record["email"],
            nickname=user_record["nickname"],
            role=user_record.get("role", "MAKER"),
            company_name=user_record.get("company_name"),
            tier_name=user_record.get("tier_name", "标准创客"),
            account_type=user_record.get("account_type", "MAKER"),
            industry_track=user_record.get("industry_track", ""),
            message=message,
            must_change_password=must_chg,
        )

    async def login_by_email(self, req: UserLoginRequest) -> AuthSessionResponse:
        """Authenticate user by account/password, email/code, or email/password."""
        login_type = req.login_type or ""
        code = req.code or req.verification_code
        email = (req.email or "").strip().lower()
        account = (req.account or "").strip()

        # Deduce login_type if not explicitly set
        if not login_type:
            if code:
                login_type = "email_code"
            elif account and not email:
                login_type = "account_password"
            else:
                login_type = "email_password"

        if login_type == "email_code":
            if not email:
                raise ValueError("请输入登录邮箱")
            if not self.validate_email(email):
                raise ValueError(f"邮箱格式不正确: {email}")
            if not code:
                raise ValueError("请输入邮箱验证码")

            if not email_verification_service.verify_code(email, code):
                raise ValueError("邮箱验证码错误或已失效，请重新获取")

            user_record = await self._fetch_user_record_by_email(email)
            if not user_record:
                raise ValueError("该邮箱尚未注册创客账号，请先完成注册")

            return self._build_auth_session_response(user_record, message="验证码核验成功，已恢复创客工作台会话")

        elif login_type == "account_password":
            target_account = account or email
            if not target_account:
                raise ValueError("请输入创客账号、用户名或邮箱")
            if not req.password:
                raise ValueError("请输入登录密码")

            user_record = await self._fetch_user_record_by_account(target_account)
            if not user_record:
                raise ValueError("该账号未注册或不存在")

            pwd_hash = user_record.get("password_hash")
            if not pwd_hash or not verify_password(req.password, pwd_hash):
                raise ValueError("账号或密码错误")

            return self._build_auth_session_response(user_record, message="登录成功，已恢复创客工作台会话")

        else:  # email_password
            target_email = email or account
            if not target_email:
                raise ValueError("请输入登录邮箱")
            if not req.password:
                raise ValueError("请输入登录密码")

            user_record = await self._fetch_user_record_by_email(target_email)
            if not user_record:
                user_record = await self._fetch_user_record_by_account(target_email)

            if not user_record:
                raise ValueError("该邮箱未注册或密码不正确")

            pwd_hash = user_record.get("password_hash")
            if not pwd_hash or not verify_password(req.password, pwd_hash):
                raise ValueError("邮箱或密码错误")

            return self._build_auth_session_response(user_record, message="登录成功，已恢复创客工作台会话")

    login_user = login_by_email

    async def get_session_by_token(self, token: str) -> AuthSessionResponse | None:
        """Decode and verify session token, returning session response or None."""
        payload = verify_session_token(token)
        if not payload:
            return None
        uid = payload.get("uid")
        email = payload.get("email")

        # Query DB or fallback
        db_user = await db_repository.get_user_by_email(email) if email else None
        if db_user:
            db_meta = db_user.metadata_payload or {}
            return AuthSessionResponse(
                token=token,
                uid=db_user.uid,
                email=db_user.email,
                nickname=db_user.nickname,
                role=db_user.role,
                company_name=db_user.company_name,
                tier_name=db_meta.get("tier_name", "标准创客"),
                message="会话有效",
                must_change_password=bool(db_meta.get("must_change_password", False)),
            )
        user_record = self._users_by_uid.get(uid) or self._users_by_email.get(email)
        if user_record:
            return AuthSessionResponse(
                token=token,
                uid=user_record["uid"],
                email=user_record["email"],
                nickname=user_record["nickname"],
                role=user_record.get("role", "MAKER"),
                company_name=user_record.get("company_name"),
                tier_name=user_record.get("tier_name", "标准创客"),
                message="会话有效",
                must_change_password=bool(user_record.get("must_change_password", False)),
            )
        return AuthSessionResponse(
            token=token,
            uid=payload.get("uid", ""),
            email=payload.get("email", ""),
            nickname=payload.get("nickname", "创客"),
            role=payload.get("role", "MAKER"),
            company_name=payload.get("company_name"),
            tier_name="标准创客",
            message="会话有效",
        )

    def get_profile(self, uid: Optional[str] = None) -> MakerProfileResponse:
        """Fetch maker profile. Unauthenticated or unknown users get the guest profile."""
        if not uid or uid == "usr_guest":
            ent_list = []
            for e in self._entitlements.values():
                e_copy = e.model_copy()
                e_copy.is_active = False
                ent_list.append(e_copy)
            return MakerProfileResponse(
                uid="usr_guest",
                nickname="未登录创客",
                role="GUEST",
                company_name="",
                credit_code="",
                tier_name="访客创客",
                account_type="MAKER",
                industry_track="",
                phone="",
                email="",
                entitlements=ent_list,
            )

        user_record = self._users_by_uid.get(uid)
        if user_record:
            nickname = user_record.get("nickname", "创客")
            role = user_record.get("role", "MAKER")
            company = user_record.get("company_name", "")
            credit_code = user_record.get("credit_code", "")
            tier_name = user_record.get("tier_name", "标准创客")
            account_type = user_record.get("account_type", "MAKER")
            industry_track = user_record.get("industry_track", "")
            phone = user_record.get("phone", "")
            email = user_record.get("email", "")
        else:
            nickname = "创客"
            role = "MAKER"
            company = ""
            credit_code = ""
            tier_name = "标准创客"
            account_type = "MAKER"
            industry_track = ""
            phone = ""
            email = ""

        ent_list = []
        for e in self._entitlements.values():
            e_copy = e.model_copy()
            user_active = user_record.get("active_entitlements", set()) if user_record else set()
            e_copy.is_active = (e.id in user_active) or (e.tier == "STANDARD")
            ent_list.append(e_copy)

        return MakerProfileResponse(
            uid=uid,
            nickname=nickname,
            role=role,
            company_name=company,
            credit_code=credit_code,
            tier_name=tier_name,
            account_type=account_type,
            industry_track=industry_track,
            phone=phone,
            email=email,
            entitlements=ent_list,
        )

    async def update_profile(self, req: UserProfileUpdateRequest, token: Optional[str] = None) -> MakerProfileResponse:
        """Update maker profile fields in memory and DB."""
        uid = req.user_id
        if token:
            payload = verify_session_token(token)
            if payload and payload.get("uid"):
                uid = payload.get("uid")

        if not uid or uid == "usr_guest":
            raise ValueError("无法为未登录访客更新档案，请先登录")

        user_record = self._users_by_uid.get(uid)
        if not user_record:
            user_record = {
                "uid": uid,
                "email": "",
                "nickname": req.nickname or "创客",
                "role": "MAKER",
                "company_name": req.company_name or "",
                "credit_code": req.credit_code or "",
                "phone": req.phone or "",
                "tier_name": "标准创客",
                "password_hash": "",
                "active_entitlements": set(),
            }
            self._users_by_uid[uid] = user_record

        if req.nickname is not None:
            user_record["nickname"] = req.nickname.strip()
        if req.phone is not None:
            user_record["phone"] = req.phone.strip()
        if req.company_name is not None:
            user_record["company_name"] = req.company_name.strip()
        if req.credit_code is not None:
            user_record["credit_code"] = req.credit_code.strip()
        if req.industry_track is not None:
            user_record["industry_track"] = req.industry_track.strip()

        # Update DB if available
        metadata_patch: Dict[str, Any] = {}
        if req.phone is not None:
            metadata_patch["phone"] = req.phone.strip()
        if req.credit_code is not None:
            metadata_patch["credit_code"] = req.credit_code.strip()
        if req.industry_track is not None:
            metadata_patch["industry_track"] = req.industry_track.strip()
        await db_repository.update_user_fields(
            uid,
            nickname=req.nickname.strip() if req.nickname is not None else None,
            company_name=req.company_name.strip() if req.company_name is not None else None,
            metadata_patch=metadata_patch or None,
        )

        return self.get_profile(uid)

    async def activate_entitlement(self, req: EntitlementActivateRequest) -> EntitlementActivateResponse:
        ent_id = req.entitlement_id
        if ent_id not in self._entitlements:
            if ent_id == "ENT_VIP":
                ent_id = "ent_black_diamond_priority"
            elif f"ent_{ent_id.lower()}" in self._entitlements:
                ent_id = f"ent_{ent_id.lower()}"
            else:
                raise KeyError(f"Entitlement {req.entitlement_id} not found")

        self._active_entitlements.add(ent_id)
        if req.user_id in self._users_by_uid:
            rec = self._users_by_uid[req.user_id]
            if "active_entitlements" not in rec:
                rec["active_entitlements"] = set()
            rec["active_entitlements"].add(ent_id)
            if ent_id == "ent_black_diamond_priority":
                rec["tier_name"] = "黑钻创客 VIP"
            await db_repository.update_user_fields(
                req.user_id,
                metadata_patch={
                    "active_entitlements": sorted(rec.get("active_entitlements", set())),
                    "tier_name": rec.get("tier_name", "标准创客"),
                },
            )

        receipt = "REC-" + uuid.uuid4().hex[:10].upper()
        return EntitlementActivateResponse(
            user_id=req.user_id,
            entitlement_id=ent_id,
            is_active=True,
            status="ACTIVATED",
            receipt_no=receipt,
            message="专属创客收费权益已激活并绑定，权限即刻生效！",
        )

    async def deactivate_entitlement(self, entitlement_id: str, user_id: Optional[str] = None) -> bool:
        ent_id = entitlement_id
        if ent_id not in self._active_entitlements and ent_id == "ENT_VIP":
            ent_id = "ent_black_diamond_priority"

        removed = False
        if ent_id in self._active_entitlements:
            self._active_entitlements.remove(ent_id)
            removed = True

        # Keep per-user active_entitlements consistent (Saga compensation symmetry)
        targets = [user_id] if user_id else list(self._users_by_uid.keys())
        for uid in targets:
            rec = self._users_by_uid.get(uid)
            if not rec:
                continue
            if "active_entitlements" in rec and ent_id in rec["active_entitlements"]:
                rec["active_entitlements"].discard(ent_id)
                removed = True
            if ent_id == "ent_black_diamond_priority" and rec.get("tier_name") == "黑钻创客 VIP":
                rec["tier_name"] = "标准创客"
            await db_repository.update_user_fields(
                uid,
                metadata_patch={
                    "active_entitlements": sorted(rec.get("active_entitlements", set())),
                    "tier_name": rec.get("tier_name", "标准创客"),
                },
            )
        return removed


    async def change_password(self, req: ChangePasswordRequest) -> AuthSessionResponse:
        """Rotate a maker's password; clears must_change_password and re-issues a token."""
        uid = req.user_id
        if req.token:
            payload = verify_session_token(req.token)
            if payload and payload.get("uid"):
                uid = payload.get("uid")
        if not uid or uid == "usr_guest":
            raise ValueError("无法为未登录访客修改密码，请先登录")

        user_record = self._users_by_uid.get(uid)
        if not user_record:
            raise KeyError(f"User '{uid}' not found")

        stored_hash = user_record.get("password_hash") or ""
        if not stored_hash or not verify_password(req.old_password, stored_hash):
            raise ValueError("原密码不正确")
        if len(req.new_password) < 8:
            raise ValueError("新密码长度不能少于 8 位")
        if req.new_password == req.old_password:
            raise ValueError("新密码不能与原密码相同")

        new_hash = hash_password(req.new_password)
        user_record["password_hash"] = new_hash
        user_record["must_change_password"] = False

        # Durable rotation: persist the new credential + clear the first-login flag
        await db_repository.update_user_fields(
            uid,
            password_hash=new_hash,
            metadata_patch={"must_change_password": False},
        )

        token = create_session_token({
            "uid": user_record["uid"],
            "email": user_record.get("email", ""),
            "nickname": user_record.get("nickname", "创客"),
            "role": user_record.get("role", "MAKER"),
            "must_change_password": False,
        })
        return AuthSessionResponse(
            token=token,
            uid=user_record["uid"],
            email=user_record.get("email", ""),
            nickname=user_record.get("nickname", "创客"),
            role=user_record.get("role", "MAKER"),
            company_name=user_record.get("company_name"),
            tier_name=user_record.get("tier_name", "标准创客"),
            message="密码修改成功，请使用新密码登录",
            must_change_password=False,
        )


user_service = UserService()
