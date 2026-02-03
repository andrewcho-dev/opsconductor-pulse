# Task 004: Unit Tests — Routes and Utilities

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> All tests in this task must be UNIT tests — no database, no Keycloak, no network calls.
> Mock all external dependencies. Tests must run in < 10 seconds total.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The route handlers (`customer.py` at 44%, `operator.py` at 40%) and utility modules (`url_validator.py` at 70%, `snmp_validator.py` at 59%) have significant untested code paths. The route tests need mocked database connections and auth, while utility tests are pure logic.

**Read first**:
- `services/ui_iot/routes/customer.py` (all route handlers)
- `services/ui_iot/routes/operator.py` (all route handlers)
- `services/ui_iot/utils/url_validator.py` (SSRF prevention)
- `services/ui_iot/utils/snmp_validator.py` (address validation)
- `services/ui_iot/db/queries.py` (database query helpers)
- `services/ui_iot/db/audit.py` (audit logging)

---

## Task

### 4.1 Create `tests/unit/test_url_validator.py`

Test `services/ui_iot/utils/url_validator.py` — fill gaps not covered by existing tests.

```python
pytestmark = [pytest.mark.unit]
```

**Test cases for SSRF prevention**:
- `test_block_127_0_0_1` — loopback → blocked
- `test_block_10_x_x_x` — 10.0.0.0/8 → blocked
- `test_block_172_16_x_x` — 172.16.0.0/12 → blocked
- `test_block_192_168_x_x` — 192.168.0.0/16 → blocked
- `test_block_169_254_metadata` — AWS metadata 169.254.169.254 → blocked
- `test_block_0_0_0_0` — 0.0.0.0 → blocked
- `test_block_localhost` — hostname "localhost" → blocked
- `test_allow_public_ip` — 8.8.8.8 → allowed
- `test_allow_public_domain` — example.com → allowed
- `test_block_scheme_file` — file:// URL → blocked
- `test_block_scheme_ftp` — ftp:// URL → blocked
- `test_reject_empty_url` — empty string → error
- `test_reject_no_hostname` — malformed URL → error
- `test_block_dns_rebinding` — hostname that resolves to private IP → blocked (mock DNS)
- `test_block_ipv6_loopback` — ::1 → blocked (if supported)
- `test_reject_url_too_long` — extremely long URL → error

### 4.2 Create `tests/unit/test_snmp_validator_extended.py`

Extend SNMP validator tests for untested branches.

```python
pytestmark = [pytest.mark.unit]
```

**Test cases**:
- `test_block_link_local` — 169.254.x.x → blocked
- `test_block_multicast` — 224.0.0.0/4 → blocked
- `test_port_below_range` — port 0 → error
- `test_port_above_range` — port 65536 → error
- `test_valid_port_162` — standard SNMP trap port → allowed
- `test_hostname_resolves_to_private` — mock DNS → blocked
- `test_empty_host` — empty string → error

### 4.3 Create `tests/unit/test_customer_route_handlers.py`

Test customer route handler logic. Mock the database pool and auth dependencies.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

Use `httpx.ASGITransport` with the FastAPI app. Mock `asyncpg` pool, `validate_token`, and `get_pool`.

**Test cases for HTML page routes**:
- `test_dashboard_returns_html` — GET /customer/dashboard → 200, content-type text/html
- `test_devices_page_returns_html` — GET /customer/devices → 200, content-type text/html
- `test_devices_json_format` — GET /customer/devices?format=json → 200, content-type application/json
- `test_alerts_page_returns_html` — GET /customer/alerts → 200, content-type text/html
- `test_alerts_json_format` — GET /customer/alerts?format=json → 200, content-type application/json
- `test_webhooks_page_returns_html` — GET /customer/webhooks → 200, text/html
- `test_snmp_page_returns_html` — GET /customer/snmp-integrations → 200, text/html
- `test_email_page_returns_html` — GET /customer/email-integrations → 200, text/html

**Test cases for webhook CRUD**:
- `test_create_integration_valid` — valid webhook data → 200
- `test_create_integration_missing_url` — no webhook_url → 400/422
- `test_create_integration_ssrf_url` — private IP → 400
- `test_list_integrations_empty` — no integrations → empty list
- `test_delete_integration_not_found` — wrong ID → 404
- `test_delete_integration_wrong_tenant` — other tenant's integration → 404

**Test cases for SNMP CRUD**:
- `test_create_snmp_v2c` — valid v2c config → 200
- `test_create_snmp_v3` — valid v3 config → 200
- `test_create_snmp_invalid_host` — private IP → 400
- `test_create_snmp_invalid_port` — port out of range → 400/422

**Test cases for email CRUD**:
- `test_create_email_valid` — valid email config → 200
- `test_create_email_no_recipients` — empty recipients → 400
- `test_create_email_invalid_smtp_host` — private IP → 400
- `test_create_email_invalid_email_address` — bad format → 400

**Test cases for test delivery endpoints**:
- `test_test_webhook_delivery` — mock httpx → success response
- `test_test_snmp_delivery` — mock SNMP sender → success response
- `test_test_email_delivery` — mock email sender → success response
- `test_test_delivery_rate_limited` — exceed limit → 429

**Test cases for RBAC**:
- `test_viewer_cannot_create_integration` — customer_viewer role → 403
- `test_viewer_cannot_delete_integration` — customer_viewer role → 403
- `test_viewer_can_list_integrations` — customer_viewer role → 200
- `test_unauthenticated_rejected` — no token → 401

### 4.4 Create `tests/unit/test_operator_route_handlers.py`

Test operator route handler logic.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases**:
- `test_operator_dashboard_returns_html` — GET /operator/dashboard → 200, text/html
- `test_operator_list_all_devices` — returns devices from all tenants
- `test_operator_filter_by_tenant` — tenant_id param → only that tenant's devices
- `test_operator_audit_logged` — accessing tenant data → audit entry created
- `test_operator_admin_settings` — operator_admin role → 200
- `test_operator_regular_no_settings` — operator role → 403
- `test_operator_audit_log_requires_admin` — operator role → 403
- `test_customer_cannot_access_operator` — customer role → 403

### 4.5 Create `tests/unit/test_db_queries.py`

Test database query builder logic from `services/ui_iot/db/queries.py`.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

Mock `asyncpg.Connection` to verify correct SQL and parameters.

**Test cases**:
- `test_list_devices_query_includes_tenant` — verify tenant_id in WHERE clause
- `test_list_devices_query_with_status_filter` — status param → in WHERE clause
- `test_list_devices_query_with_limit` — limit param → LIMIT in query
- `test_get_device_query_includes_both_keys` — verify both tenant_id AND device_id
- `test_list_alerts_query_ordering` — verify ORDER BY created_at DESC
- `test_list_integrations_query_tenant_scoped` — verify tenant_id filter

---

## Files to Create

| Action | Path |
|--------|------|
| CREATE | `tests/unit/test_url_validator.py` |
| CREATE | `tests/unit/test_snmp_validator_extended.py` |
| CREATE | `tests/unit/test_customer_route_handlers.py` |
| CREATE | `tests/unit/test_operator_route_handlers.py` |
| CREATE | `tests/unit/test_db_queries.py` |

---

## Test

```bash
# 1. Run only the new unit tests
pytest tests/unit/test_url_validator.py tests/unit/test_snmp_validator_extended.py tests/unit/test_customer_route_handlers.py tests/unit/test_operator_route_handlers.py tests/unit/test_db_queries.py -v --tb=short

# 2. Verify speed
time pytest -m unit -q

# 3. Run full unit suite
pytest -m unit -v

# 4. Check coverage
pytest -m unit --cov=services/ui_iot --cov-report=term-missing -q
```

---

## Acceptance Criteria

- [ ] `test_url_validator.py` has 16+ test cases covering all SSRF vectors
- [ ] `test_snmp_validator_extended.py` has 7+ test cases covering edge cases
- [ ] `test_customer_route_handlers.py` has 25+ test cases covering all CRUD operations and RBAC
- [ ] `test_operator_route_handlers.py` has 8+ test cases covering dashboard, audit, settings
- [ ] `test_db_queries.py` has 6+ test cases covering query construction
- [ ] ALL tests pass with `pytest -m unit`
- [ ] ALL unit tests run in < 10 seconds total
- [ ] No test requires database, Keycloak, or network access
- [ ] `customer.py` coverage improves from 44% to > 65%
- [ ] `operator.py` coverage improves from 40% to > 60%
- [ ] `url_validator.py` coverage improves from 70% to > 90%
- [ ] `snmp_validator.py` coverage improves from 59% to > 80%

---

## Commit

```
Add unit tests for routes, validators, and query builders

- 60+ unit tests for customer routes, operator routes, URL/SNMP
  validation, and database query construction
- All CRUD operations tested with mocked DB and auth
- SSRF prevention tested for all private IP ranges and edge cases
- RBAC enforcement verified for all protected endpoints

Part of Phase 9: Testing Overhaul
```
