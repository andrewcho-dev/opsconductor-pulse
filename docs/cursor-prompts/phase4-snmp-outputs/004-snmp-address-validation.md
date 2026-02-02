# Task 004: SNMP Address Validation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

SNMP destination addresses need validation to prevent customers from sending traps to internal infrastructure. This is the SNMP equivalent of SSRF prevention for webhooks.

**Read first**:
- `services/ui_iot/utils/url_validator.py` (webhook URL validation)
- Task 003 (customer routes that will use this validation)

**Depends on**: Task 003

---

## Task

### 4.1 Create SNMP address validator

Create `services/ui_iot/utils/snmp_validator.py`:

```python
"""SNMP destination address validation."""

import socket
import ipaddress
from typing import Optional
from dataclasses import dataclass

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
BLOCKED_METADATA_HOSTS = ["metadata.google.internal", "169.254.169.254"]


@dataclass
class SNMPValidationResult:
    """Result of SNMP address validation."""
    valid: bool
    error: Optional[str] = None
    resolved_ip: Optional[str] = None


def validate_snmp_host(host: str, port: int = 162) -> SNMPValidationResult:
    """Validate SNMP destination host."""
    if not 1 <= port <= 65535:
        return SNMPValidationResult(valid=False, error=f"Invalid port: {port}")

    host_lower = host.lower().strip()
    if host_lower in BLOCKED_HOSTNAMES:
        return SNMPValidationResult(valid=False, error=f"Blocked hostname: {host}")

    if host_lower in BLOCKED_METADATA_HOSTS:
        return SNMPValidationResult(valid=False, error=f"Blocked metadata endpoint: {host}")

    try:
        ip = ipaddress.ip_address(host)
        return _validate_ip(ip, host)
    except ValueError:
        pass

    try:
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_DGRAM)
        if not addr_info:
            return SNMPValidationResult(valid=False, error=f"Could not resolve: {host}")

        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                result = _validate_ip(ip, host)
                if not result.valid:
                    return result
            except ValueError:
                continue

        return SNMPValidationResult(valid=True, resolved_ip=addr_info[0][4][0])

    except socket.gaierror as e:
        return SNMPValidationResult(valid=False, error=f"DNS resolution failed: {e}")
    except Exception as e:
        return SNMPValidationResult(valid=False, error=str(e))


def _validate_ip(ip, original_host: str) -> SNMPValidationResult:
    """Validate a resolved IP address."""
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return SNMPValidationResult(
                valid=False,
                error=f"IP {ip} is in blocked network {network}"
            )

    if ip.is_private:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is private")
    if ip.is_loopback:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is loopback")
    if ip.is_link_local:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is link-local")
    if ip.is_multicast:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is multicast")

    return SNMPValidationResult(valid=True, resolved_ip=str(ip))


def is_snmp_host_allowed(host: str, port: int = 162) -> bool:
    """Simple boolean check if SNMP host is allowed."""
    return validate_snmp_host(host, port).valid
```

### 4.2 Integrate validation into customer routes

Update `services/ui_iot/routes/customer.py` create and update functions:

```python
from services.ui_iot.utils.snmp_validator import validate_snmp_host

# In create_snmp_integration, after role check:
validation = validate_snmp_host(data.snmp_host, data.snmp_port)
if not validation.valid:
    raise HTTPException(status_code=400, detail=f"Invalid SNMP destination: {validation.error}")

# In update_snmp_integration, when snmp_host is being updated:
if data.snmp_host is not None:
    port = data.snmp_port if data.snmp_port is not None else 162
    validation = validate_snmp_host(data.snmp_host, port)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid SNMP destination: {validation.error}")
```

### 4.3 Create unit tests

Create `tests/unit/test_snmp_validator.py`:

```python
"""Unit tests for SNMP address validator."""

import pytest
from services.ui_iot.utils.snmp_validator import validate_snmp_host, is_snmp_host_allowed

pytestmark = pytest.mark.unit


class TestSNMPAddressValidation:
    """Test SNMP address validation."""

    def test_localhost_blocked(self):
        result = validate_snmp_host("localhost")
        assert not result.valid

    def test_loopback_blocked(self):
        result = validate_snmp_host("127.0.0.1")
        assert not result.valid

    def test_private_10_blocked(self):
        result = validate_snmp_host("10.0.0.1")
        assert not result.valid

    def test_private_172_blocked(self):
        result = validate_snmp_host("172.16.0.1")
        assert not result.valid

    def test_private_192_blocked(self):
        result = validate_snmp_host("192.168.1.1")
        assert not result.valid

    def test_metadata_blocked(self):
        result = validate_snmp_host("169.254.169.254")
        assert not result.valid

    def test_invalid_port(self):
        result = validate_snmp_host("8.8.8.8", port=0)
        assert not result.valid

    def test_public_ip_allowed(self):
        result = validate_snmp_host("8.8.8.8")
        assert result.valid

    def test_is_snmp_host_allowed_helper(self):
        assert not is_snmp_host_allowed("localhost")
        assert is_snmp_host_allowed("8.8.8.8")
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/utils/snmp_validator.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| CREATE | `tests/unit/test_snmp_validator.py` |

---

## Acceptance Criteria

- [ ] Private IPs (10.x, 172.16.x, 192.168.x) rejected
- [ ] Loopback (127.x) rejected
- [ ] localhost hostname rejected
- [ ] Cloud metadata IPs rejected
- [ ] Public IPs allowed
- [ ] Integration routes validate on create/update
- [ ] Unit tests pass

**Test**:
```bash
pytest tests/unit/test_snmp_validator.py -v

TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Bad","snmp_host":"192.168.1.100","snmp_config":{"version":"2c","community":"public"}}' \
  http://localhost:8080/customer/integrations/snmp
# Expected: 400
```

---

## Commit

```
Add SNMP address validation

- Block private IPs and localhost
- Block cloud metadata endpoints
- DNS resolution validation
- Integrated into customer routes
- Unit tests

Part of Phase 4: SNMP and Alternative Outputs
```
