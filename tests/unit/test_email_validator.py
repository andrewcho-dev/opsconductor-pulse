"""Unit tests for email validator."""

import pytest

from services.ui_iot.utils.email_validator import (
    validate_email_address,
    validate_email_integration,
    validate_smtp_host,
)

pytestmark = pytest.mark.unit


class TestEmailAddressValidation:
    """Test email address validation."""

    def test_valid_email(self):
        result = validate_email_address("user@example.com")
        assert result.valid

    def test_valid_email_with_plus(self):
        result = validate_email_address("user+tag@example.com")
        assert result.valid

    def test_invalid_email_no_at(self):
        result = validate_email_address("userexample.com")
        assert not result.valid

    def test_invalid_email_no_domain(self):
        result = validate_email_address("user@")
        assert not result.valid

    def test_empty_email(self):
        result = validate_email_address("")
        assert not result.valid

    def test_email_too_long(self):
        result = validate_email_address("a" * 250 + "@example.com")
        assert not result.valid


class TestSMTPHostValidation:
    """Test SMTP host validation."""

    def test_localhost_blocked(self):
        result = validate_smtp_host("localhost")
        assert not result.valid

    def test_loopback_blocked(self):
        result = validate_smtp_host("127.0.0.1")
        assert not result.valid

    def test_private_ip_blocked(self):
        result = validate_smtp_host("192.168.1.1")
        assert not result.valid

    def test_invalid_port(self):
        result = validate_smtp_host("smtp.example.com", port=0)
        assert not result.valid

    def test_public_smtp_allowed(self):
        # Note: This may fail if DNS doesn't resolve
        # In unit tests, we typically mock DNS
        result = validate_smtp_host("8.8.8.8")
        assert result.valid


class TestEmailIntegrationValidation:
    """Test complete integration validation."""

    def test_valid_integration(self):
        result = validate_email_integration(
            smtp_host="8.8.8.8",  # Using IP to avoid DNS
            smtp_port=587,
            from_address="alerts@example.com",
            recipients={"to": ["admin@example.com"]},
        )
        assert result.valid

    def test_no_recipients(self):
        result = validate_email_integration(
            smtp_host="8.8.8.8",
            smtp_port=587,
            from_address="alerts@example.com",
            recipients={"to": []},
        )
        assert not result.valid
        assert "recipient" in result.error.lower()

    def test_too_many_recipients(self):
        result = validate_email_integration(
            smtp_host="8.8.8.8",
            smtp_port=587,
            from_address="alerts@example.com",
            recipients={"to": [f"user{i}@example.com" for i in range(60)]},
        )
        assert not result.valid
        assert "50" in result.error

    def test_invalid_recipient(self):
        result = validate_email_integration(
            smtp_host="8.8.8.8",
            smtp_port=587,
            from_address="alerts@example.com",
            recipients={"to": ["not-an-email"]},
        )
        assert not result.valid
