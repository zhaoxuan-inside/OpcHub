"""User, authentication, and entitlement management service."""
import re
import uuid
from typing import Dict, List, Set, Optional, Any

from src.core.security import hash_password, verify_password, create_session_token, verify_session_token
from src.infrastructure.database.repository import db_repository
from src.domains.user.models import (
    EntitlementItem,
    MakerProfileResponse,
    EntitlementActivateRequest,
    EntitlementActivateResponse,
    UserRegisterRequest,
    UserLoginRequest,
    AuthSessionResponse,
)


class UserService:
    """Manages maker profile, authentication, and entitlements."""

    def __init__(self):
        self._active_entitlements: Set[str] = {"ent_microkernel_pipeline", "ent_policy_radar_basic"}
        self._entitlements: Dict[str, EntitlementItem] = {}
        self._users_by_email: Dict[str, Dict[str, Any]] = {}
        self._users_by_uid: Dict[str, Dict[str, Any]] = {}
        self._seed_default_entitlements()
        self._seed_default_users()

    def _seed_default_users(self):
        default_user = {
            "uid": "usr_2026_opc_9981",
            "email": "maker@opchub.cn",
            "nickname": "赵玄",
            "role": "MAKER",
            "company_name": "极客视界（杭州）信息技术工作室",
            "credit_code": "92330106MAD7XXXX8Y",
            "tier_name": "黑钻创客 VIP",
            "password_hash": hash_password("maker123456"),
        }
        self._users_by_email[default_user["email"]] = default_user
        self._users_by_uid[default_user["uid"]] = default_user

    def _seed_default_entitlements(self):
        items = [
            (
                "ent_microkernel_pipeline",
                "微内核高并发编排算力通道",
                "STANDARD",
                0.0,
                "基础微内核 DAG 串联与沙箱执行能力，日调用上限 10,000 次。",
                "10,000 次/日",
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
        company = req.company_name.strip() if req.company_name else f"{nickname}独立工作室"
        pwd_hash = hash_password(req.password)
        uid = f"usr_{uuid.uuid4().hex[:12]}"

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
            "credit_code": "92" + uuid.uuid4().hex[:16].upper(),
            "tier_name": "标准创客",
            "password_hash": pwd_hash,
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
                "company_name": db_user.company_name or f"{db_user.nickname}工作室",
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

        # Issue signed token
        token = create_session_token({
            "uid": user_record["uid"],
            "email": user_record["email"],
            "nickname": user_record["nickname"],
            "role": user_record.get("role", "MAKER"),
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

    def get_profile(self, uid: str = "usr_2026_opc_9981") -> MakerProfileResponse:
        """Fetch maker profile."""
        user_record = self._users_by_uid.get(uid)
        nickname = user_record["nickname"] if user_record else "赵玄"
        role = user_record["role"] if user_record else "MAKER"
        company = user_record["company_name"] if user_record else "极客视界（杭州）信息技术工作室"
        credit_code = user_record.get("credit_code", "92330106MAD7XXXX8Y") if user_record else "92330106MAD7XXXX8Y"
        tier_name = user_record.get("tier_name", "黑钻创客 VIP") if user_record else "黑钻创客 VIP"

        ent_list = []
        for e in self._entitlements.values():
            e_copy = e.model_copy()
            e_copy.is_active = e.id in self._active_entitlements
            ent_list.append(e_copy)

        return MakerProfileResponse(
            uid=uid,
            nickname=nickname,
            role=role,
            company_name=company,
            credit_code=credit_code,
            tier_name=tier_name,
            entitlements=ent_list,
        )

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
        receipt = "REC-" + uuid.uuid4().hex[:10].upper()
        return EntitlementActivateResponse(
            user_id=req.user_id,
            entitlement_id=ent_id,
            is_active=True,
            status="ACTIVATED",
            receipt_no=receipt,
            message="专属创客收费权益已激活并绑定，权限即刻生效！",
        )

    def deactivate_entitlement(self, entitlement_id: str) -> bool:
        ent_id = entitlement_id
        if ent_id not in self._active_entitlements and ent_id == "ENT_VIP":
            ent_id = "ent_black_diamond_priority"
        if ent_id in self._active_entitlements:
            self._active_entitlements.remove(ent_id)
            return True
        return False


user_service = UserService()
