"""User, authentication, and entitlement management service."""
import re
import uuid
from typing import Dict, Set, Optional, Any

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


class UserService:
    """Manages maker profile, authentication, and entitlements."""

    def __init__(self):
        self._active_entitlements: Set[str] = set()
        self._entitlements: Dict[str, EntitlementItem] = {}
        self._users_by_email: Dict[str, Dict[str, Any]] = {}
        self._users_by_uid: Dict[str, Dict[str, Any]] = {}
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

    def _seed_default_entitlements(self):
        items = [
            (
                "ent_microkernel_pipeline",
                "超级个体全链路出海与合规通道",
                "STANDARD",
                0.0,
                "一站式连通海外支付结算、企业合规自检与政务申报全套通道。",
                "实时就绪",
            ),
            (
                "ent_policy_radar_basic",
                "全国与地方政策雷达白话提炼",
                "STANDARD",
                0.0,
                "免费查阅与匹配国家级增值税与小微企业免税政策。",
                "实时全量",
            ),
            (
                "ent_ai_tax_assistant",
                "AI 政策智能测算与申报材料极速出具",
                "PRO",
                199.0,
                "解锁一键生成符合政务标准的设立登记、软著申报全套文书。",
                "无限次导出",
            ),
            (
                "ent_black_diamond_priority",
                "黑钻合伙人 VIP 优先需求派单特权",
                "BLACK_DIAMOND",
                899.0,
                "获得企业技术外包与出海委托优先推荐接单权限，技术担保履约背书。",
                "顶格优先派单",
            ),
        ]
        for eid, name, tier, price, desc, quota in items:
            self._entitlements[eid] = EntitlementItem(
                id=eid,
                name=name,
                tier=tier,
                price_cny=price,
                description=desc,
                is_active=(eid in self._active_entitlements),
                quota_desc=quota,
            )

    def validate_email(self, email: str) -> bool:
        """Validate standard email format."""
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email.strip()))

    async def register_by_email(self, req: UserRegisterRequest) -> AuthSessionResponse:
        """Register a new maker using email and password."""
        email = req.email.strip().lower()
        if not self.validate_email(email):
            raise ValueError(f"邮箱格式不正确: {req.email}")

        if len(req.password) < 6:
            raise ValueError("密码长度不能少于 6 位")

        # Check DB first if available
        db_user = await db_repository.get_user_by_email(email)
        if db_user is not None:
            raise ValueError("该邮箱已被注册，请直接登录")

        # Check in-memory store
        if email in self._users_by_email:
            raise ValueError("该邮箱已被注册，请直接登录")

        nickname = req.nickname.strip() if req.nickname else email.split("@")[0]
        company = req.company_name.strip() if req.company_name else ""
        pwd_hash = hash_password(req.password)
        uid = str(uuid.uuid4())

        # Persist to database if live
        try:
            created_db_user = await db_repository.create_user(
                email=email,
                password_plain=req.password,
                nickname=nickname,
                company_name=company,
                role="MAKER",
            )
            if created_db_user:
                uid = created_db_user.uid
        except Exception:
            pass

        # Save to in-memory cache
        user_record = {
            "uid": uid,
            "email": email,
            "nickname": nickname,
            "role": "MAKER",
            "company_name": company,
            "phone": "",
            "credit_code": "",
            "tier_name": "标准创客",
            "password_hash": pwd_hash,
            "active_entitlements": set(),
        }
        self._users_by_email[email] = user_record
        self._users_by_uid[uid] = user_record

        # Issue signed token
        token = create_session_token({
            "uid": uid,
            "email": email,
            "nickname": nickname,
            "role": "MAKER",
        })

        return AuthSessionResponse(
            token=token,
            uid=uid,
            email=email,
            nickname=nickname,
            role="MAKER",
            company_name=company,
            tier_name="标准创客",
            message="注册成功，欢迎加入超级个体创客中心！",
        )

    async def login_by_email(self, req: UserLoginRequest) -> AuthSessionResponse:
        """Authenticate user by email and password, issuing a signed session token."""
        email = req.email.strip().lower()

        # Try fetching from DB
        db_user = await db_repository.get_user_by_email(email)
        user_record = None
        if db_user is not None:
            user_record = {
                "uid": db_user.uid,
                "email": db_user.email,
                "nickname": db_user.nickname,
                "role": db_user.role,
                "company_name": db_user.company_name or "",
                "tier_name": (db_user.metadata_payload or {}).get("tier_name", "标准创客"),
                "password_hash": db_user.password_hash,
            }
        elif email in self._users_by_email:
            user_record = self._users_by_email[email]

        if not user_record:
            raise ValueError("该邮箱未注册或密码不正确")

        pwd_hash = user_record.get("password_hash")
        if not pwd_hash or not verify_password(req.password, pwd_hash):
            raise ValueError("邮箱或密码错误")

        # Issue signed token (carries must_change_password for first-login enforcement)
        must_chg = bool(user_record.get("must_change_password", False))
        token = create_session_token({
            "uid": user_record["uid"],
            "email": user_record["email"],
            "nickname": user_record["nickname"],
            "role": user_record.get("role", "MAKER"),
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
            message="登录成功，已恢复创客工作台会话",
            must_change_password=must_chg,
        )

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
            return AuthSessionResponse(
                token=token,
                uid=db_user.uid,
                email=db_user.email,
                nickname=db_user.nickname,
                role=db_user.role,
                company_name=db_user.company_name,
                tier_name=(db_user.metadata_payload or {}).get("tier_name", "标准创客"),
                message="会话有效",
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
            phone = user_record.get("phone", "")
            email = user_record.get("email", "")
        else:
            nickname = "创客"
            role = "MAKER"
            company = ""
            credit_code = ""
            tier_name = "标准创客"
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

        # Update DB if available
        try:
            email = user_record.get("email")
            if email:
                db_user = await db_repository.get_user_by_email(email)
                if db_user:
                    if req.nickname is not None:
                        db_user.nickname = req.nickname.strip()
                    if req.company_name is not None:
                        db_user.company_name = req.company_name.strip()
                    meta = db_user.metadata_payload or {}
                    if req.phone is not None:
                        meta["phone"] = req.phone.strip()
                    if req.credit_code is not None:
                        meta["credit_code"] = req.credit_code.strip()
                    db_user.metadata_payload = meta
        except Exception:
            pass

        return self.get_profile(uid)

    def activate_entitlement(self, req: EntitlementActivateRequest) -> EntitlementActivateResponse:
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

        receipt = "REC-" + uuid.uuid4().hex[:10].upper()
        return EntitlementActivateResponse(
            user_id=req.user_id,
            entitlement_id=ent_id,
            is_active=True,
            status="ACTIVATED",
            receipt_no=receipt,
            message="专属创客收费权益已激活并绑定，权限即刻生效！",
        )

    def deactivate_entitlement(self, entitlement_id: str, user_id: Optional[str] = None) -> bool:
        ent_id = entitlement_id
        if ent_id not in self._active_entitlements and ent_id == "ENT_VIP":
            ent_id = "ent_black_diamond_priority"

        removed = False
        if ent_id in self._active_entitlements:
            self._active_entitlements.remove(ent_id)
            removed = True

        # Keep per-user active_entitlements consistent (Saga compensation symmetry)
        targets = [self._users_by_uid.get(user_id)] if user_id else list(self._users_by_uid.values())
        for rec in targets:
            if rec and "active_entitlements" in rec and ent_id in rec["active_entitlements"]:
                rec["active_entitlements"].discard(ent_id)
                removed = True
            if rec and ent_id == "ent_black_diamond_priority" and rec.get("tier_name") == "黑钻创客 VIP":
                rec["tier_name"] = "标准创客"
        return removed


    def change_password(self, req: ChangePasswordRequest) -> AuthSessionResponse:
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

        user_record["password_hash"] = hash_password(req.new_password)
        user_record["must_change_password"] = False

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
