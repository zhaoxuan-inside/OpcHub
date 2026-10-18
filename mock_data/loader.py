"""Unified Loader for Independent Mock Datasets.

Allows both the HTTP Mock Server and the Automated Test Suites to share the exact
same baseline dataset without coupling data directly inside service code.
"""
from pathlib import Path
from typing import Any, Dict, List
import yaml

DATA_DIR = Path(__file__).resolve().parent


def _load_yaml(filename: str) -> Dict[str, Any]:
    target = DATA_DIR / filename
    if not target.exists():
        raise FileNotFoundError(f"Mock data file not found: {target}")
    with open(target, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_moderation_data() -> Dict[str, Any]:
    """Retrieve content moderation keywords and sample test vectors."""
    return _load_yaml("content_moderation.yaml")


def get_oss_attachments_data() -> Dict[str, Any]:
    """Retrieve OSS and media upload mock specifications and sample attachments."""
    return _load_yaml("oss_attachments.yaml")


def get_sms_and_identity_data() -> Dict[str, Any]:
    """Retrieve SMS verification rules and enterprise real-name test cases."""
    return _load_yaml("sms_and_identity.yaml")


def get_payment_and_split_data() -> Dict[str, Any]:
    """Retrieve WeChat Pay and Stripe Connect order templates and receivers."""
    return _load_yaml("payment_and_split.yaml")


def get_ai_completions_data() -> Dict[str, Any]:
    """Retrieve AI inference prompts and response expectations."""
    return _load_yaml("ai_completions.yaml")
