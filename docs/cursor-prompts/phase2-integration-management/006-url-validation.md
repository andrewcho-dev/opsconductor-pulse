# Task 006: URL Validation

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Customers provide webhook URLs when creating integrations. Malicious or misconfigured URLs could trigger Server-Side Request Forgery (SSRF) attacks, allowing attackers to probe internal networks or cloud metadata endpoints. All customer-supplied URLs must be validated.

**Read first**:
- `services/ui_iot/routes/customer.py` (integration create/update routes)
- OWASP SSRF Prevention Cheat Sheet

**Depends on**: Task 003

## Task

### 6.1 Create URL validator module

Create `services/ui_iot/utils/__init__.py` (empty file for package).

Create `services/ui_iot/utils/url_validator.py`:

**Main function**:
```
def validate_webhook_url(url: str, allow_http: bool = False) -> tuple[bool, str | None]
```
- Returns `(True, None)` if valid
- Returns `(False, "error message")` if invalid

### 6.2 Validation rules

**Rule 1: Valid URL format**
- Parse with urllib.parse
- Must have scheme and netloc
- Invalid format: return `(False, "Invalid URL format")`

**Rule 2: Scheme check**
- If `allow_http=False`: only `https` allowed
- If `allow_http=True`: `http` or `https` allowed
- Other schemes (ftp, file, etc.): return `(False, "Only HTTPS URLs are allowed")`

**Rule 3: Block private IP ranges**

Block these CIDR ranges:
- `10.0.0.0/8` — Private Class A
- `172.16.0.0/12` — Private Class B
- `192.168.0.0/16` — Private Class C
- `127.0.0.0/8` — Loopback
- `169.254.0.0/16` — Link-local
- `0.0.0.0/8` — Current network
- `::1/128` — IPv6 loopback
- `fc00::/7` — IPv6 private
- `fe80::/10` — IPv6 link-local

Return: `(False, "Private IP addresses are not allowed")`

**Rule 4: Block cloud metadata endpoints**
- `169.254.169.254` — AWS/GCP/Azure metadata
- `metadata.google.internal`
- `169.254.170.2` — AWS ECS metadata

Return: `(False, "Cloud metadata endpoints are not allowed")`

**Rule 5: Block internal hostnames**
- `localhost`
- `*.local`
- `*.internal`
- `*.localhost`

Return: `(False, "Internal hostnames are not allowed")`

**Rule 6: DNS resolution check**
- Resolve hostname to IP address
- Check resolved IP against blocklist (Rules 3, 4)
- This catches DNS rebinding attacks

Return: `(False, "Hostname resolves to blocked IP address")`

### 6.3 Environment variable

Add support for development mode:

**Variable**: `ALLOW_HTTP_WEBHOOKS`
- Default: `false`
- If `true`: allow http:// URLs (for local testing only)

Read in validator:
```python
allow_http = os.getenv("ALLOW_HTTP_WEBHOOKS", "false").lower() == "true"
```

### 6.4 Integrate into routes

**In `POST /customer/integrations`**:
```python
from utils.url_validator import validate_webhook_url

valid, error = validate_webhook_url(body.webhook_url)
if not valid:
    raise HTTPException(400, f"Invalid webhook URL: {error}")
```

**In `PATCH /customer/integrations/{id}`**:
- Only validate if `webhook_url` is being updated
- Same validation as POST

**In test delivery endpoint**:
- Validate URL before making request
- Even though URL was validated on save, re-validate in case of:
  - DNS changes
  - Bypassed validation (bug)

### 6.5 Helper function for IP check

```python
import ipaddress

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in BLOCKED_NETWORKS)
    except ValueError:
        return False
```

### 6.6 DNS resolution with per-call timeout

**IMPORTANT**: Do NOT use `socket.setdefaulttimeout()` as it is process-global and affects all network calls in the application. Use per-call timeout instead.

**Option A: Use asyncio with timeout (recommended for async code)**:
```python
import asyncio
import socket

async def resolve_hostname(hostname: str, timeout: float = 5.0) -> list[str]:
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.getaddrinfo(hostname, None),
            timeout=timeout
        )
        return [info[4][0] for info in result]
    except (asyncio.TimeoutError, socket.gaierror):
        return []
```

**Option B: Use socket.create_connection for sync code**:
```python
import socket

def resolve_hostname_sync(hostname: str, timeout: float = 5.0) -> list[str]:
    try:
        # getaddrinfo doesn't support timeout directly, but we can use
        # a thread with timeout for isolation
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(socket.getaddrinfo, hostname, None)
            result = future.result(timeout=timeout)
            return [info[4][0] for info in result]
    except (concurrent.futures.TimeoutError, socket.gaierror):
        return []
```

Use Option A for the async FastAPI routes.

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/utils/__init__.py` |
| CREATE | `services/ui_iot/utils/url_validator.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |

## Acceptance Criteria

- [ ] `http://` URLs rejected when ALLOW_HTTP_WEBHOOKS is false
- [ ] `http://` URLs allowed when ALLOW_HTTP_WEBHOOKS is true
- [ ] `https://10.0.0.1/hook` rejected (private IP)
- [ ] `https://192.168.1.1/hook` rejected (private IP)
- [ ] `https://127.0.0.1/hook` rejected (loopback)
- [ ] `https://localhost/hook` rejected (internal hostname)
- [ ] `https://169.254.169.254/` rejected (metadata)
- [ ] `https://metadata.google.internal/` rejected
- [ ] DNS rebinding blocked (hostname resolving to private IP)
- [ ] `https://example.com/webhook` accepted (valid public URL)
- [ ] Clear error messages returned to user
- [ ] Validation applied to create, update, and test delivery

**Test scenario**:
```
1. Login as customer1
2. POST /customer/integrations with url="http://example.com" (no HTTPS)
3. Confirm 400: "Only HTTPS URLs are allowed"
4. POST with url="https://10.0.0.1/hook"
5. Confirm 400: "Private IP addresses are not allowed"
6. POST with url="https://localhost/hook"
7. Confirm 400: "Internal hostnames are not allowed"
8. POST with url="https://webhook.site/valid-uuid"
9. Confirm 201: integration created
```

## Commit

```
Add URL validation to prevent SSRF in webhook integrations

- Block private IP ranges (10.x, 172.16.x, 192.168.x, 127.x)
- Block cloud metadata endpoints (169.254.169.254)
- Block internal hostnames (localhost, *.local, *.internal)
- DNS resolution check against blocklist
- ALLOW_HTTP_WEBHOOKS env var for development
- Applied to create, update, and test delivery

Part of Phase 2: Customer Integration Management
```
