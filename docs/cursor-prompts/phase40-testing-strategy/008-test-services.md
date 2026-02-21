# 008: Unit Tests for Service Modules

## Why
Four critical service modules have ZERO tests:
- `services/ui_iot/services/keycloak_admin.py` (371 LOC) — Keycloak admin API client for user provisioning
- `services/ui_iot/services/subscription.py` (363 LOC) — Subscription entitlement management
- `services/ui_iot/services/alert_dispatcher.py` (199 LOC) — Routes alerts to integrations
- `services/ui_iot/services/snmp_sender.py` (227 LOC) — SNMP trap delivery

## Source Files
Read all four files listed above.

## Pattern to Follow
Read: `tests/unit/test_customer_route_handlers.py` (lines 1-80) for mocking pattern.
Read: `tests/unit/test_worker_logic.py` for delivery worker test patterns.

## Test Files to Create

### `tests/unit/test_keycloak_admin.py` (~15 tests)

Mock all HTTP calls to Keycloak admin REST API using `respx` or `AsyncMock` on the httpx client.

```
test_get_admin_token_success
  - Mock POST to /realms/master/protocol/openid-connect/token
  - Returns access_token
  - Verify token cached

test_get_admin_token_failure
  - Mock token endpoint returns 401
  - Raises appropriate error

test_get_users_returns_list
  - Mock GET /admin/realms/pulse/users
  - Returns parsed user list

test_get_users_with_search
  - Mock GET with search query parameter
  - Verify query string passed correctly

test_create_user_sends_correct_payload
  - Mock POST /admin/realms/pulse/users → 201
  - Verify JSON body includes username, email, enabled, attributes

test_create_user_with_tenant_attribute
  - Verify tenant_id set as user attribute
  - Verify role set as user attribute or realm role

test_delete_user_calls_correct_endpoint
  - Mock DELETE /admin/realms/pulse/users/{id} → 204

test_get_user_roles_returns_realm_roles
  - Mock GET /admin/realms/pulse/users/{id}/role-mappings/realm
  - Returns role list

test_assign_realm_role_sends_role_representation
  - Mock POST /admin/realms/pulse/users/{id}/role-mappings/realm
  - Verify role representation in body

test_remove_realm_role
  - Mock DELETE /admin/realms/pulse/users/{id}/role-mappings/realm
  - Verify role representation in body

test_get_realm_roles_returns_all
  - Mock GET /admin/realms/pulse/roles
  - Returns role list

test_update_user_attributes
  - Mock PUT /admin/realms/pulse/users/{id}
  - Verify attributes dict in body

test_admin_token_refresh_on_expiry
  - First call gets token, advance time past TTL
  - Second call fetches new token

test_http_error_raises_exception
  - Mock any endpoint to return 500
  - Verify exception raised with context

test_connection_error_handled
  - Mock httpx to raise ConnectionError
  - Verify appropriate error handling
```

### `tests/unit/test_subscription_service.py` (~12 tests)

```
test_check_subscription_limit_under_limit
  - subscription.active_device_count=5, device_limit=10
  - Returns (True, 5, 10)

test_check_subscription_limit_at_limit
  - active_device_count=10, device_limit=10
  - Returns (False, 10, 10)

test_create_subscription_inserts_record
  - Mock conn.fetchrow for INSERT
  - Verify correct SQL params (tenant_id, type, device_limit, term_start, term_end)

test_create_subscription_validates_type
  - Only MAIN, ADDON, TRIAL, TEMPORARY allowed
  - Invalid type → ValueError

test_assign_device_to_subscription
  - Mock UPDATE device_registry SET subscription_id
  - Verify active_device_count incremented

test_assign_device_at_limit_raises
  - Subscription at capacity
  - Raises ValueError "Subscription at limit"

test_reassign_device_decrements_old_subscription
  - Device moves from sub-A to sub-B
  - sub-A active_device_count decremented
  - sub-B active_device_count incremented

test_get_subscription_devices
  - Mock query for devices with subscription_id
  - Returns device list

test_update_subscription_status
  - Mock UPDATE subscriptions SET status
  - Verify audit trail entry created

test_subscription_status_transitions
  - TRIAL → ACTIVE (valid)
  - ACTIVE → SUSPENDED (valid)
  - EXPIRED → ACTIVE (valid — renewal)

test_check_device_access_active
  - Device with ACTIVE subscription → access granted

test_check_device_access_suspended
  - Device with SUSPENDED subscription → access denied
```

### `tests/unit/test_alert_dispatcher_service.py` (~10 tests)

```
test_dispatch_webhook_sends_post
  - Mock httpx POST
  - Alert + webhook integration → POST sent with correct JSON payload

test_dispatch_email_sends_smtp
  - Mock SMTP connection
  - Alert + email integration → email sent

test_dispatch_mqtt_publishes
  - Mock MQTT client
  - Alert + MQTT integration → message published to correct topic

test_dispatch_snmp_sends_trap
  - Mock SNMP sender
  - Alert + SNMP integration → trap sent

test_dispatch_parallel_multiple_integrations
  - Alert matches 3 routes → all 3 dispatched concurrently

test_dispatch_failure_returns_error
  - Webhook returns 500 → dispatch result shows failure

test_dispatch_timeout_handled
  - Webhook hangs → timeout error captured

test_dispatch_logs_attempt
  - After dispatch, verify delivery log entry

test_dispatch_with_no_matching_routes
  - Alert doesn't match any routes → no dispatch, no error

test_dispatch_respects_min_severity
  - Route has min_severity=3
  - Alert with severity=2 → not dispatched
  - Alert with severity=3 → dispatched
```

### `tests/unit/test_snmp_sender_service.py` (~10 tests)

```
test_send_v2c_trap
  - Config: version="2c", community="public", host, port
  - Mock pysnmp sendNotification
  - Verify correct OIDs and varbinds

test_send_v3_trap_with_auth
  - Config: version="3", username, auth_protocol="SHA", auth_password
  - Mock pysnmp with USM security model
  - Verify auth parameters

test_send_v3_trap_with_priv
  - Config: version="3", priv_protocol="AES", priv_password
  - Verify encryption parameters

test_send_v1_trap
  - Config: version="1"
  - Verify generic trap type and enterprise OID

test_custom_oid_prefix
  - Config: snmp_oid_prefix="1.3.6.1.4.1.99999"
  - Verify OIDs use custom prefix

test_alert_data_mapped_to_varbinds
  - Alert with severity, device_id, summary
  - Verify each mapped to correct OID + value

test_connection_error_handled
  - Mock transport to raise error
  - Verify error returned gracefully

test_timeout_handled
  - Mock slow response
  - Verify timeout error

test_invalid_host_rejected
  - Empty or invalid SNMP host
  - Returns error without attempting send

test_port_defaults_to_162
  - Config without port specified
  - Verify port 162 used
```

## Implementation Notes

### keycloak_admin.py (`services/ui_iot/services/keycloak_admin.py`, 371 LOC)
- Has `KeycloakAdminError(message, status_code)` exception class
- Internal helpers: `_get_admin_token() -> str` (caches with 60s buffer), `_admin_request(method, path, json?, params?) -> dict|list|None`
- User ops: `list_users`, `get_user`, `get_user_by_username`, `get_user_by_email`, `create_user`, `update_user`, `delete_user`, `set_user_password`, `enable_user`, `disable_user`
- Role ops: `get_realm_roles`, `get_user_roles`, `assign_realm_role`, `remove_realm_role`
- Org ops: `get_organizations`, `get_organization_members`, `add_user_to_organization`, `remove_user_from_organization`
- Utility: `format_user_response(user)` — extracts tenant_id from attributes
- Mock `httpx.AsyncClient` or use `respx` to intercept HTTP calls
- Token caching uses a lock for thread safety — test expiry/refresh behavior

### subscription.py (`services/ui_iot/services/subscription.py`, 363 LOC)
- Functions take `conn: asyncpg.Connection` as first arg
- Key functions: `create_subscription`, `get_subscription`, `get_tenant_subscriptions`, `assign_device_to_subscription`, `check_subscription_limit`, `check_device_access`, `create_device_on_subscription`
- `assign_device_to_subscription` validates: subscription exists, belongs to tenant, has capacity, not SUSPENDED/EXPIRED
- `check_device_access` returns `(allowed: bool, reason: str)` — reasons: DEVICE_NOT_FOUND, NO_SUBSCRIPTION, SUBSCRIPTION_SUSPENDED, SUBSCRIPTION_EXPIRED
- `create_subscription` — ADDON requires parent_subscription_id, parent must be MAIN type
- Mock asyncpg.Connection with FakeConn pattern

### alert_dispatcher.py (`services/ui_iot/services/alert_dispatcher.py`, 199 LOC)
- Dataclasses: `AlertPayload`, `DeliveryResult`, `DispatchResult`, `DeliveryType(Enum)`
- `dispatch_alert(alert: AlertPayload, integrations: list[dict]) -> DispatchResult` — runs deliveries in parallel via asyncio.gather
- `_deliver_webhook(alert, integration) -> DeliveryResult` — HTTP POST with 10s timeout, checks 2xx
- `_deliver_snmp(alert, integration) -> DeliveryResult` — delegates to snmp_sender.send_alert_trap
- Mock `httpx.AsyncClient` for webhooks, mock `snmp_sender.send_alert_trap` for SNMP

### snmp_sender.py (`services/ui_iot/services/snmp_sender.py`, 227 LOC)
- **NOTE:** There are ALREADY SNMP sender tests at `tests/unit/test_delivery_snmp_sender.py` and `tests/unit/test_snmp_sender.py`. Read both first to understand coverage gaps.
- Class `SNMPSender(timeout=5.0, retries=2)` with `send_trap(host, port, config, alert, oid_prefix)` method
- `_build_v3_auth(config) -> UsmUserData` — auth protocols: MD5, SHA; priv protocols: DES, AES
- `_build_alert_varbinds(alert, oid_prefix) -> list` — 6 varbinds: alert_id, device_id, tenant_id, severity_int, message, uptime
- Dataclasses: `SNMPTrapResult(success, error?, destination?, duration_ms?)`, `AlertTrapData`
- Existing tests mock pysnmp heavily with `monkeypatch.setattr` on `CommunityData`, `UsmUserData`, `sendNotification`, etc.
- Only add tests that cover gaps in existing test files

All test files should use: `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`

## Verify
```bash
pytest tests/unit/test_keycloak_admin.py tests/unit/test_subscription_service.py tests/unit/test_alert_dispatcher_service.py tests/unit/test_snmp_sender_service.py -v
```
