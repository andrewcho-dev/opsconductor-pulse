from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

import email_sender

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


def _smtp_mock():
    smtp = AsyncMock()
    smtp.__aenter__.return_value = smtp
    smtp.__aexit__.return_value = False
    return smtp


async def test_send_email_success(monkeypatch):
    smtp = _smtp_mock()
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    result = await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_tls=True,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["ops@example.com"]},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    assert result.success is True
    smtp.send_message.assert_awaited_once()


async def test_send_email_tls(monkeypatch):
    smtp = _smtp_mock()
    smtp_cls = MagicMock(return_value=smtp)
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=smtp_cls))

    await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_tls=True,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["ops@example.com"]},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    _, kwargs = smtp_cls.call_args
    assert kwargs.get("start_tls") is True


async def test_send_email_auth(monkeypatch):
    smtp = _smtp_mock()
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_tls=True,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["ops@example.com"]},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    smtp.login.assert_awaited_once_with("user", "pass")


async def test_send_email_multiple_recipients(monkeypatch):
    smtp = _smtp_mock()
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_tls=False,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["a@example.com"], "cc": ["b@example.com"], "bcc": ["c@example.com"]},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    args, kwargs = smtp.send_message.call_args
    msg = args[0]
    assert "a@example.com" in msg["To"]
    assert "b@example.com" in msg["Cc"]
    assert "c@example.com" in kwargs["recipients"]


async def test_send_email_template_rendering(monkeypatch):
    smtp = _smtp_mock()
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_tls=False,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["ops@example.com"]},
        alert_id="a1",
        device_id="dev-9",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime(2024, 1, 1),
        subject_template="[{severity}] {device_id}",
        body_template="Alert {alert_id} on {device_id}",
    )

    msg = smtp.send_message.call_args.args[0]
    assert "dev-9" in msg["Subject"]


async def test_send_email_connection_refused(monkeypatch):
    smtp = _smtp_mock()
    smtp.__aenter__.side_effect = ConnectionRefusedError("refused")
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    result = await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_tls=False,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["ops@example.com"]},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    assert result.success is False
    assert "refused" in result.error.lower()


async def test_send_email_auth_failure(monkeypatch):
    smtp = _smtp_mock()
    smtp.login.side_effect = PermissionError("auth failed")
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    result = await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_tls=True,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": ["ops@example.com"]},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    assert result.success is False
    assert "auth failed" in result.error.lower()


async def test_send_email_no_recipients(monkeypatch):
    smtp = _smtp_mock()
    monkeypatch.setattr(email_sender, "AIOSMTPLIB_AVAILABLE", True)
    monkeypatch.setattr(email_sender, "aiosmtplib", MagicMock(SMTP=MagicMock(return_value=smtp)))

    result = await email_sender.send_alert_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_tls=False,
        from_address="alerts@example.com",
        from_name="Ops",
        recipients={"to": []},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        alert_type="TEMP",
        timestamp=datetime.utcnow(),
    )

    assert result.success is False
    assert result.error == "No recipients specified"
