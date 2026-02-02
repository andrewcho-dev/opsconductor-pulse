# Task 004: SNMP Address Validation

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Just like webhook URLs, SNMP destination addresses need validation to prevent customers from sending traps to internal infrastructure. This is the SNMP equivalent of SSRF prevention.

**Read first**:
- `services/ui_iot/utils/url_validator.py` (webhook URL validation)
- Task 003 (customer routes that will use this validation)

**Depends on**: Task 003

## Task

### 4.1 Create SNMP address validator

Create `services/ui_iot/utils/snmp_validator.py`:

```python
"""SNMP destination address validation to prevent internal network access."""

import socket
import ipaddress
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Blocked IP ranges (same as webhook validator)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),      # Private
    ipaddress.ip_network("172.16.0.0/12"),   # Private
    ipaddress.ip_network("192.168.0.0/16"),  # Private
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),       # Invalid
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),    # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),    # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"), # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
    ipaddress.ip_network("240.0.0.0/4"),     # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),         # Loopback
    ipaddress.ip_network("fc00::/7"),        # Unique local
    ipaddress.ip_network("fe80::/10"),       # Link-local
    ipaddress.ip_network("ff00::/8"),        # Multicast
]

# Blocked hostnames
BLOCKED_HOSTNAMES = [
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
]

# Cloud metadata endpoints (common hostnames)
BLOCKED_METADATA_HOSTS = [
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",  # AWS/GCP/Azure metadata
]


@dataclass
class SNMPValidationResult:
    """Result of SNMP address validation."""
    valid: bool
    error: Optional[str] = None
    resolved_ip: Optional[str] = None


def validate_snmp_host(host: str, port: int = 162) -> SNMPValidationResult:
    """
    Validate SNMP destination host.

    Args:
        host: Hostname or IP address
        port: SNMP port (validated for range)

    Returns:
        SNMPValidationResult with validation status
    """
    # Port validation
    if not 1 <= port <= 65535:
        return SNMPValidationResult(
            valid=False,
            error=f"Invalid port: {port}. Must be 1-65535."
        )

    # Check for blocked hostnames
    host_lower = host.lower().strip()
    if host_lower in BLOCKED_HOSTNAMES:
        return SNMPValidationResult(
            valid=False,
            error=f"Blocked hostname: {host}"
        )

    if host_lower in BLOCKED_METADATA_HOSTS:
        return SNMPValidationResult(
            valid=False,
            error=f"Blocked metadata endpoint: {host}"
        )

    # Try to parse as IP address first
    try:
        ip = ipaddress.ip_address(host)
        return _validate_ip(ip, host)
    except ValueError:
        pass  # Not an IP, try DNS resolution

    # DNS resolution
    try:
        # Resolve hostname to IP
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_DGRAM)
        if not addr_info:
            return SNMPValidationResult(
                valid=False,
                error=f"Could not resolve hostname: {host}"
            )

        # Check all resolved IPs
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                result = _validate_ip(ip, host)
                if not result.valid:
                    return result
            except ValueError:
                continue

        # All IPs passed validation
        first_ip = addr_info[0][4][0]
        return SNMPValidationResult(
            valid=True,
            resolved_ip=first_ip
        )

    except socket.gaierror as e:
        return SNMPValidationResult(
            valid=False,
            error=f"DNS resolution failed for {host}: {e}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error validating SNMP host {host}")
        return SNMPValidationResult(
            valid=False,
            error=f"Validation error: {str(e)}"
        )


def _validate_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, original_host: str) -> SNMPValidationResult:
    """Validate a resolved IP address."""
    # Check against blocked networks
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return SNMPValidationResult(
                valid=False,
                error=f"IP {ip} (from {original_host}) is in blocked network {network}"
            )

    # Check if private
    if ip.is_private:
        return SNMPValidationResult(
            valid=False,
            error=f"IP {ip} (from {original_host}) is a private address"
        )

    # Check if reserved
    if ip.is_reserved:
        return SNMPValidationResult(
            valid=False,
            error=f"IP {ip} (from {original_host}) is a reserved address"
        )

    # Check if loopback
    if ip.is_loopback:
        return SNMPValidationResult(
            valid=False,
            error=f"IP {ip} (from {original_host}) is a loopback address"
        )

    # Check if link-local
    if ip.is_link_local:
        return SNMPValidationResult(
            valid=False,
            error=f"IP {ip} (from {original_host}) is a link-local address"
        )

    # Check if multicast
    if ip.is_multicast:
        return SNMPValidationResult(
            valid=False,
            error=f"IP {ip} (from {original_host}) is a multicast address"
        )

    return SNMPValidationResult(
        valid=True,
        resolved_ip=str(ip)
    )


def is_snmp_host_allowed(host: str, port: int = 162) -> bool:
    """
    Simple boolean check if SNMP host is allowed.

    Args:
        host: Hostname or IP address
        port: SNMP port

    Returns:
        True if allowed, False otherwise
    """
    result = validate_snmp_host(host, port)
    return result.valid
```

### 4.2 Integrate validation into customer routes

Update `services/ui_iot/routes/customer.py` to use SNMP validation:

```python
from services.ui_iot.utils.snmp_validator import validate_snmp_host

# In create_snmp_integration:
async def create_snmp_integration(...):
    # ... existing code ...

    # Validate SNMP destination
    validation = validate_snmp_host(data.snmp_host, data.snmp_port)
    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid SNMP destination: {validation.error}"
        )

    # ... rest of function ...


# In update_snmp_integration:
async def update_snmp_integration(...):
    # ... existing code ...

    if data.snmp_host is not None:
        # Validate new SNMP destination
        port = data.snmp_port if data.snmp_port is not None else existing["snmp_port"]
        validation = validate_snmp_host(data.snmp_host, port)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SNMP destination: {validation.error}"
            )

    # ... rest of function ...
```

### 4.3 Create unit tests

Create `tests/unit/test_snmp_validator.py`:

```python
"""Unit tests for SNMP address validator."""

import pytest
from services.ui_iot.utils.snmp_validator import (
    validate_snmp_host,
    is_snmp_host_allowed,
    SNMPValidationResult,
)

pytestmark = pytest.mark.unit


class TestSNMPAddressValidation:
    """Test SNMP address validation."""

    def test_localhost_blocked(self):
        """localhost is blocked."""
        result = validate_snmp_host("localhost")
        assert not result.valid
        assert "Blocked hostname" in result.error

    def test_loopback_ip_blocked(self):
        """127.0.0.1 is blocked."""
        result = validate_snmp_host("127.0.0.1")
        assert not result.valid
        assert "loopback" in result.error.lower()

    def test_private_10_blocked(self):
        """10.x.x.x is blocked."""
        result = validate_snmp_host("10.0.0.1")
        assert not result.valid

    def test_private_172_blocked(self):
        """172.16.x.x is blocked."""
        result = validate_snmp_host("172.16.0.1")
        assert not result.valid

    def test_private_192_blocked(self):
        """192.168.x.x is blocked."""
        result = validate_snmp_host("192.168.1.1")
        assert not result.valid

    def test_metadata_ip_blocked(self):
        """AWS/GCP metadata IP is blocked."""
        result = validate_snmp_host("169.254.169.254")
        assert not result.valid

    def test_metadata_hostname_blocked(self):
        """GCP metadata hostname is blocked."""
        result = validate_snmp_host("metadata.google.internal")
        assert not result.valid

    def test_multicast_blocked(self):
        """Multicast addresses are blocked."""
        result = validate_snmp_host("224.0.0.1")
        assert not result.valid

    def test_invalid_port_rejected(self):
        """Invalid port is rejected."""
        result = validate_snmp_host("8.8.8.8", port=0)
        assert not result.valid
        assert "Invalid port" in result.error

        result = validate_snmp_host("8.8.8.8", port=70000)
        assert not result.valid
        assert "Invalid port" in result.error

    def test_public_ip_allowed(self):
        """Public IP is allowed."""
        result = validate_snmp_host("8.8.8.8")
        assert result.valid
        assert result.resolved_ip == "8.8.8.8"

    def test_valid_port_accepted(self):
        """Valid port is accepted."""
        result = validate_snmp_host("8.8.8.8", port=162)
        assert result.valid

        result = validate_snmp_host("8.8.8.8", port=1162)
        assert result.valid

    def test_is_snmp_host_allowed_helper(self):
        """Test boolean helper function."""
        assert not is_snmp_host_allowed("localhost")
        assert not is_snmp_host_allowed("192.168.1.1")
        assert is_snmp_host_allowed("8.8.8.8")


class TestDNSResolution:
    """Test DNS resolution validation."""

    def test_nonexistent_hostname_rejected(self):
        """Nonexistent hostname is rejected."""
        result = validate_snmp_host("this-host-does-not-exist-12345.invalid")
        assert not result.valid
        assert "DNS resolution failed" in result.error or "Could not resolve" in result.error

    # Note: Can't easily test DNS to private IP without mock
    # Real DNS tests would require a controlled DNS server
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/utils/snmp_validator.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| CREATE | `tests/unit/test_snmp_validator.py` |

## Acceptance Criteria

- [ ] Private IPs (10.x, 172.16.x, 192.168.x) rejected
- [ ] Loopback (127.x) rejected
- [ ] localhost hostname rejected
- [ ] Cloud metadata IPs/hostnames rejected
- [ ] Multicast addresses rejected
- [ ] Public IPs allowed
- [ ] DNS resolution performed for hostnames
- [ ] Integration routes validate on create/update
- [ ] Unit tests pass

**Test**:
```bash
# Run unit tests
pytest tests/unit/test_snmp_validator.py -v

# Test via API (should fail)
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Bad SNMP","snmp_host":"192.168.1.100","snmp_config":{"version":"2c","community":"public"}}' \
  http://localhost:8080/customer/integrations/snmp
# Expected: 400 Bad Request with "Invalid SNMP destination"
```

## Commit

```
Add SNMP address validation

- Block private IPs (10.x, 172.16.x, 192.168.x)
- Block loopback and localhost
- Block cloud metadata endpoints
- Block multicast/reserved addresses
- DNS resolution validation
- Integrated into customer routes
- Unit tests for validation

Part of Phase 4: SNMP and Alternative Outputs
```
