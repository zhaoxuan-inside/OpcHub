#!/usr/bin/env python3
"""
Provision an OpcHub platform administrator account.

Uses the application's own repository layer (not raw SQL) so that password
hashing, metadata payloads and the persistence contract stay identical to
accounts created through the regular registration path.

Usage:
    PYTHONPATH=backend python3 scripts/create_admin_account.py \
        --account admin --password 'iPasswd1234'

The login form resolves the "account" field against email / uid / nickname,
so `--account` is applied as the nickname. The email must be unique.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from src.infrastructure.database.repository import db_repository  # noqa: E402
from src.core.security import hash_password  # noqa: E402


async def provision(account: str, email: str, password: str, nickname: str) -> int:
    if not await db_repository.is_ready():
        print("[ERROR] Database is not reachable; cannot provision the account.", file=sys.stderr)
        return 1

    # Idempotency: refuse to silently overwrite an existing account.
    existing = await db_repository.get_user_by_account(account)
    if existing is not None:
        print(f"[ERROR] Account '{account}' already exists (uid={existing.uid}, email={existing.email}).", file=sys.stderr)
        return 1

    by_email = await db_repository.get_user_by_email(email)
    if by_email is not None:
        print(f"[ERROR] Email '{email}' is already registered (uid={by_email.uid}).", file=sys.stderr)
        return 1

    user = await db_repository.create_user(
        email=email,
        password_plain=password,
        nickname=nickname or account,
        company_name="OpcHub 平台运营",
        role="ADMIN",
        metadata={
            "tier": "STANDARD",
            "tier_name": "平台管理员",
            "account_type": "MAKER",
            "industry_track": "平台运营管理",
            "phone": "",
            "credit_code": "",
            "created_source": "ADMIN_PROVISION",
            # Full admin console access without a forced first-login rotation.
            "must_change_password": False,
        },
    )

    print("[SUCCESS] Administrator account provisioned:")
    print(f"  uid     : {user.uid}")
    print(f"  account : {user.nickname}")
    print(f"  email   : {user.email}")
    print(f"  role    : {user.role}")
    print(f"  active  : {user.is_active}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision an OpcHub administrator account.")
    parser.add_argument("--account", required=True, help="Login account (stored as nickname)")
    parser.add_argument("--password", required=True, help="Plaintext password (hashed with PBKDF2-SHA256)")
    parser.add_argument("--email", default=None, help="Unique email address")
    parser.add_argument("--nickname", default=None, help="Display name (defaults to --account)")
    args = parser.parse_args()

    email = (args.email or f"{args.account}@opchub.local").strip().lower()

    if len(args.password) < 8:
        print("[ERROR] Password must be at least 8 characters.", file=sys.stderr)
        return 1

    # Validate the password against the platform policy before writing anything.
    from src.domains.user.verification import PasswordPolicyService
    verdict = PasswordPolicyService.evaluate(args.password, email)
    if not verdict.get("meets_commercial_standard"):
        print(f"[ERROR] Password does not meet the platform policy: {verdict.get('feedback')}", file=sys.stderr)
        return 1

    return asyncio.run(provision(args.account, email, args.password, args.nickname))


if __name__ == "__main__":
    raise SystemExit(main())
