# Task 004: Email Validation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Email integrations need validation to prevent abuse. We need to validate:
1. Email addresses are properly formatted
2. SMTP hosts are not internal/private addresses (like SNMP/webhook validation)
3. Rate limit email sends to prevent spam

**Read first**:
- `services/ui_iot/utils/snmp_validator.py` (SSRF prevention pattern)
- `services/ui_iot/utils/url_validator.py` (validation patterns)

**Depends on**: Task 003

---

## Task

### 4.1 Create email validator

Create `services/ui_iot/utils/email_validator.py`:

```python
"""Email integration validation."""

import re
import socket
import ipaddress
from typing import Optional
from dataclasses import dataclass

# Reuse blocked networks from SNMP validator
BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = ["localhost", "localhost.localdomain"]

# Common disposable email domains to block (optional, can be extended)
BLOCKED_EMAIL_DOMAINS = [
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "throwaway.email",
    "10minutemail.com",
]

# Email regex pattern (simplified but effective)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


@dataclass
class EmailValidationResult:
    """Result of email validation."""
    valid: bool
    error: Optional[str] = None


@dataclass
class SMTPValidationResult:
    """Result of SMTP host validation."""
    valid: bool
    error: Optional[str] = None
    resolved_ip: Optional[str] = None


def validate_email_address(email: str) -> EmailValidationResult:
    """Validate a single email address."""
    if not email:
        return EmailValidationResult(valid=False, error="Email address is empty")

    email = email.strip().lower()

    if len(email) > 254:
        return EmailValidationResult(valid=False, error="Email address too long")

    if not EMAIL_PATTERN.match(email):
        return EmailValidationResult(valid=False, error="Invalid email format")

    # Extract domain
    try:
        domain = email.split("@")[1]
    except IndexError:
        return EmailValidationResult(valid=False, error="Invalid email format")

    # Check for blocked disposable domains (optional)
    if domain in BLOCKED_EMAIL_DOMAINS:
        return EmailValidationResult(valid=False, error=f"Disposable email domain not allowed: {domain}")

    return EmailValidationResult(valid=True)


def validate_smtp_host(host: str, port: int = 587) -> SMTPValidationResult:
    """Validate SMTP host is not internal/private."""
    if not host:
        return SMTPValidationResult(valid=False, error="SMTP host is empty")

    if not 1 <= port <= 65535:
        return SMTPValidationResult(valid=False, error=f"Invalid port: {port}")

    host_lower = host.lower().strip()

    if host_lower in BLOCKED_HOSTNAMES:
        return SMTPValidationResult(valid=False, error=f"Blocked hostname: {host}")

    # Check if it's an IP address
    try:
        ip = ipaddress.ip_address(host)
        return _validate_ip(ip)
    except ValueError:
        pass

    # Resolve hostname
    try:
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            return SMTPValidationResult(valid=False, error=f"Could not resolve: {host}")

        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                result = _validate_ip(ip)
                if not result.valid:
                    return result
            except ValueError:
                continue

        return SMTPValidationResult(valid=True, resolved_ip=addr_info[0][4][0])

    except socket.gaierror as e:
        return SMTPValidationResult(valid=False, error=f"DNS resolution failed: {e}")
    except Exception as e:
        return SMTPValidationResult(valid=False, error=str(e))


def _validate_ip(ip) -> SMTPValidationResult:
    """Validate a resolved IP address."""
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return SMTPValidationResult(
                valid=False,
                error=f"IP {ip} is in blocked network {network}"
            )

    if ip.is_private:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is private")
    if ip.is_loopback:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is loopback")
    if ip.is_link_local:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is link-local")
    if ip.is_multicast:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is multicast")

    return SMTPValidationResult(valid=True, resolved_ip=str(ip))


def validate_email_integration(
    smtp_host: str,
    smtp_port: int,
    from_address: str,
    recipients: dict,
) -> EmailValidationResult:
    """Validate complete email integration configuration."""
    # Validate SMTP host
    smtp_result = validate_smtp_host(smtp_host, smtp_port)
    if not smtp_result.valid:
        return EmailValidationResult(valid=False, error=f"SMTP host: {smtp_result.error}")

    # Validate from address
    from_result = validate_email_address(from_address)
    if not from_result.valid:
        return EmailValidationResult(valid=False, error=f"From address: {from_result.error}")

    # Validate recipients
    to_list = recipients.get("to", [])
    cc_list = recipients.get("cc", [])
    bcc_list = recipients.get("bcc", [])

    if not to_list:
        return EmailValidationResult(valid=False, error="At least one recipient required")

    all_recipients = to_list + cc_list + bcc_list

    if len(all_recipients) > 50:
        return EmailValidationResult(valid=False, error="Maximum 50 recipients allowed")

    for email in all_recipients:
        result = validate_email_address(email)
        if not result.valid:
            return EmailValidationResult(valid=False, error=f"Recipient {email}: {result.error}")

    return EmailValidationResult(valid=True)
```

### 4.2 Integrate validation into customer routes

Update the `create_email_integration` function in `services/ui_iot/routes/customer.py`:

```python
from utils.email_validator import validate_email_integration

# In create_email_integration, after name validation:
validation = validate_email_integration(
    smtp_host=data.smtp_config.smtp_host,
    smtp_port=data.smtp_config.smtp_port,
    from_address=data.smtp_config.from_address,
    recipients=data.recipients.model_dump(),
)
if not validation.valid:
    raise HTTPException(status_code=400, detail=f"Invalid email configuration: {validation.error}")
```

Update the `update_email_integration` function similarly when smtp_config or recipients are being updated.

### 4.3 Create unit tests

Create `tests/unit/test_email_validator.py`:

```python
"""Unit tests for email validator."""

import pytest
from services.ui_iot.utils.email_validator import (
    validate_email_address,
    validate_smtp_host,
    validate_email_integration,
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
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/utils/email_validator.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| CREATE | `tests/unit/test_email_validator.py` |

---

## Acceptance Criteria

- [ ] Email addresses validated for format
- [ ] SMTP hosts blocked for private/internal IPs
- [ ] Recipient count limited to 50
- [ ] At least one recipient required
- [ ] Validation integrated into create/update routes
- [ ] Unit tests pass

**Test**:
```bash
# Run unit tests
pytest tests/unit/test_email_validator.py -v

# Test API validation
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

# Should fail - private SMTP
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "Bad SMTP",
    "smtp_config": {"smtp_host": "192.168.1.1", "smtp_port": 587, "from_address": "a@b.com", "smtp_tls": true},
    "recipients": {"to": ["test@example.com"]}
  }' \
  http://localhost:8080/customer/integrations/email
# Expected: 400
```

---

## Commit

```
Add email validation

- Validate email address format
- Block private/internal SMTP hosts
- Limit recipient count to 50
- Integrated into customer routes
- Unit tests

Part of Phase 6: Email Delivery
```
