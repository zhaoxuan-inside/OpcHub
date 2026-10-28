"""Outbound email adapter for the user / auth domain.

All network I/O for verification mail lives here, behind the generic-looking
``external.email.send`` operator. Scenario assets reference that operator; pure
functions (``calc.auth.*`` / ``assemble.auth.*``) only compose the message body,
so no calculation module imports ``smtplib``.
"""
from __future__ import annotations

import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.core.operators.sdk import operator
from src.domains.user.mail_config import resolve_mail_config

logger = logging.getLogger("opchub.user.mailer")


def send_email_message(
    to_email: str,
    subject: str,
    text: str,
    html_body: str,
    code: str = "",
) -> dict[str, Any]:
    """Transmit one email and return delivery diagnostics.

    When SMTP credentials are absent the message is recorded in audited mock
    mode (development / CI), matching the historical dispatcher behaviour.
    """
    clean_email = str(to_email or "").strip().lower()
    cfg = resolve_mail_config(clean_email)
    provider_name = str(cfg["provider_name"])

    if not cfg["configured"]:
        logger.info(
            "[EMAIL_DISPATCH] mock_audit target=%s provider=%s host=%s:%s code=%s",
            clean_email,
            provider_name,
            cfg["host"],
            cfg["port"],
            code or "<none>",
        )
        return {
            "success": True,
            "mode": "mock_audit",
            "routing_tier": cfg["routing_tier"],
            "provider_id": cfg["provider_id"],
            "provider_name": provider_name,
            "smtp_host": cfg["host"],
            "smtp_port": cfg["port"],
            "from_email": cfg["from_email"],
            "error": None,
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["from_email"]
        msg["To"] = clean_email
        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if cfg["port"] == 465 and not cfg["use_tls"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10) as server:
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from_email"], [clean_email], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as server:
                if cfg["use_tls"]:
                    server.starttls()
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from_email"], [clean_email], msg.as_string())

        logger.info(
            "[EMAIL_DISPATCH] sent target=%s provider=%s host=%s:%s",
            clean_email,
            provider_name,
            cfg["host"],
            cfg["port"],
        )
        return {
            "success": True,
            "mode": "smtp",
            "routing_tier": cfg["routing_tier"],
            "provider_id": cfg["provider_id"],
            "provider_name": provider_name,
            "smtp_host": cfg["host"],
            "smtp_port": cfg["port"],
            "from_email": cfg["from_email"],
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - delivery failures are reported, not raised
        logger.error(
            "[EMAIL_DISPATCH] failed target=%s provider=%s host=%s:%s error=%s",
            clean_email,
            provider_name,
            cfg["host"],
            cfg["port"],
            exc,
        )
        return {
            "success": False,
            "mode": "smtp",
            "routing_tier": cfg["routing_tier"],
            "provider_id": cfg["provider_id"],
            "provider_name": provider_name,
            "smtp_host": cfg["host"],
            "smtp_port": cfg["port"],
            "from_email": cfg["from_email"],
            "error": str(exc),
        }


@operator(
    "external.email.send",
    category="ADAPTER",
    description="Send one transactional email through the configured SMTP gateway",
)
async def email_send(
    params: dict[str, Any],
    args: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    to_email = str(args.get("to_email") or args.get("email") or params.get("to_email") or "")
    subject = str(args.get("subject") or params.get("subject") or "")
    text = str(args.get("text") or params.get("text") or "")
    html_body = str(
        args.get("html") or args.get("html_body") or params.get("html") or text
    )
    code = str(args.get("code") or params.get("code") or "")
    if not to_email:
        raise ValueError("external.email.send requires a recipient email")
    dispatch = send_email_message(
        to_email=to_email,
        subject=subject,
        text=text,
        html_body=html_body,
        code=code,
    )
    return {"dispatch": dispatch, "provider": html.escape(str(dispatch.get("provider_name") or ""))}
