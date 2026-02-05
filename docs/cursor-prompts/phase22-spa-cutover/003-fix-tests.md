# Task 003: Fix Tests for SPA Cutover

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-2 removed all Jinja template routes and files. Several tests now reference routes or functions that no longer exist. This task fixes the tests so all 395 tests pass again.

**Read first**:
- `tests/conftest.py` — lines 43-45 reference template paths
- `tests/unit/test_customer_route_handlers.py` — tests for removed routes and helpers
- `tests/unit/test_operator_route_handlers.py` — tests for removed routes and helpers
- `services/ui_iot/routes/customer.py` — verify what functions still exist after Task 1
- `services/ui_iot/routes/operator.py` — verify what functions still exist after Task 1
- `services/ui_iot/app.py` — verify what functions still exist after Task 1

---

## Task

### 3.1 Fix `tests/conftest.py`

Remove the template path setup lines (around lines 43-45):

```python
templates_path = os.path.join(ui_root, "templates")
customer_routes.templates.env.loader.searchpath = [templates_path]
operator_routes.templates.env.loader.searchpath = [templates_path]
```

These lines crash because `templates` no longer exists on the route modules. Delete all three lines.

### 3.2 Fix `tests/unit/test_customer_route_handlers.py`

#### Delete tests for removed routes

Delete these test functions entirely (the routes they test no longer exist):

1. `test_dashboard_returns_html` — `GET /customer/dashboard` removed
2. `test_devices_page_returns_html` — `GET /customer/devices` now returns JSON, not HTML
3. `test_alerts_page_returns_html` — `GET /customer/alerts` now returns JSON, not HTML
4. `test_webhooks_page_returns_html` — `GET /customer/webhooks` removed
5. `test_snmp_page_returns_html` — `GET /customer/snmp-integrations` removed
6. `test_email_page_returns_html` — `GET /customer/email-integrations` removed
7. `test_device_detail_deprecated` — `GET /device/{device_id}` removed
8. `test_admin_create_device_success` — `POST /admin/create-device` removed
9. `test_admin_activate_device_failure` — `POST /admin/activate-device` removed

#### Update tests for JSON-only routes

**`test_devices_json_format`**: Remove `?format=json` from the URL — the route now always returns JSON:

```python
async def test_devices_json_format(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_devices", AsyncMock(return_value=[]))

    resp = await client.get("/customer/devices", headers=_auth_header())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
```

**`test_alerts_json_format`**: Remove `?format=json`:

```python
async def test_alerts_json_format(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_alerts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
```

**`test_get_device_detail_json`**: Remove `?format=json`:

```python
async def test_get_device_detail_json(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(customer_routes, "fetch_device_events_influx", AsyncMock(return_value=[]))
    monkeypatch.setattr(customer_routes, "fetch_device_telemetry_influx", AsyncMock(return_value=[]))

    resp = await client.get("/customer/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"
```

#### Update helper tests

**`test_helpers_and_normalizers`**: Remove the assertions for `to_float`, `to_int`, `sparkline_points`, and `redact_url` — these functions were deleted from customer.py. Keep the remaining assertions for `_validate_name`, `_normalize_list`, `_normalize_json`, and `generate_test_payload`:

```python
async def test_helpers_and_normalizers():
    assert customer_routes._validate_name(" Valid ") == "Valid"
    with pytest.raises(HTTPException):
        customer_routes._validate_name(" ")
    with pytest.raises(HTTPException):
        customer_routes._validate_name("Bad@Name")

    normalized = customer_routes._normalize_list([" CRITICAL ", "CRITICAL"], customer_routes.SEVERITIES, "severities")
    assert normalized == ["CRITICAL"]
    with pytest.raises(HTTPException):
        customer_routes._normalize_list(["BAD"], customer_routes.SEVERITIES, "severities")

    assert customer_routes._normalize_json({"a": 1}) == {"a": 1}
    assert customer_routes._normalize_json(b'{"a":1}') == {"a": 1}
    assert customer_routes._normalize_json("not json") == {}

    payload = customer_routes.generate_test_payload("tenant-a", "Webhook")
    assert payload["_test"] is True
    assert payload["integration_name"] == "Webhook"
```

**`test_app_helpers`**: Remove the `redact_url` assertion (function deleted from app.py):

```python
async def test_app_helpers(monkeypatch):
    monkeypatch.setenv("SECURE_COOKIES", "true")
    assert app_module._secure_cookies_enabled() is True
    monkeypatch.setenv("UI_BASE_URL", "http://localhost:8080/")
    assert app_module.get_ui_base_url() == "http://localhost:8080"
    verifier, challenge = app_module.generate_pkce_pair()
    assert verifier and challenge
    assert app_module.generate_state()
```

#### Update redirect tests

**`test_callback_success_customer`**: Callback now redirects to `/app/` not `/customer/dashboard`:

```python
async def test_callback_success_customer(client, monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"}))

    resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"
```

**`test_root_no_session`**: Root now always redirects to `/app/` (no session check):

```python
async def test_root_no_session(client):
    resp = await client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"
```

**`test_root_operator_session`**: Root now always redirects to `/app/`:

```python
async def test_root_operator_session(client, monkeypatch):
    resp = await client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"
```

Note: This test can be simplified since root no longer checks the session. The monkeypatch for `validate_token` and cookies are no longer needed. But keeping the test with simpler assertions is fine too — just verify the redirect.

### 3.3 Fix `tests/unit/test_operator_route_handlers.py`

#### Delete tests for removed routes

1. `test_operator_dashboard_returns_html` — `GET /operator/dashboard` removed
2. `test_operator_admin_settings` — `GET /operator/settings` (HTML) removed
3. `test_operator_regular_no_settings` — `GET /operator/settings` removed. (The POST still requires admin but has its own test path. Delete this test.)
4. `test_operator_view_device_html` — HTML branch of view_device removed
5. `test_load_dashboard_context` — `_load_dashboard_context` function removed

#### Update `test_operator_view_device_json`

The route now always returns JSON (no `format` param). The current test expects an `AttributeError` (because of template rendering issues in test). After the template removal, it should return JSON directly. Update:

```python
async def test_operator_view_device_json(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(operator_routes, "fetch_device_events_influx", AsyncMock(return_value=[]))
    monkeypatch.setattr(operator_routes, "fetch_device_telemetry_influx", AsyncMock(return_value=[]))

    resp = await client.get("/operator/tenants/tenant-a/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"
```

Remove `?format=json` and the `pytest.raises(AttributeError)` wrapper.

#### Update `test_operator_helpers`

Remove `to_float`, `to_int`, and `sparkline_points` assertions. Keep `get_request_metadata` test:

```python
async def test_operator_helpers():
    req = Request({"type": "http", "headers": []})
    ip, user_agent = operator_routes.get_request_metadata(req)
    assert ip is None
    assert user_agent is None
```

#### Update or delete `test_get_settings_mode_normalization`

If `get_settings` was removed from operator.py (because it was only used by `_load_dashboard_context`), delete this test. If `get_settings` was kept (because it's used elsewhere), keep the test.

Check: read `services/ui_iot/routes/operator.py` to see if `get_settings` still exists. If Task 1 removed it, delete this test. If Task 1 kept it (perhaps it's used by `update_settings` POST), keep the test.

Most likely `get_settings` should be removed since it was only called by `_load_dashboard_context`. Delete `test_get_settings_mode_normalization`.

#### Clean up imports

If `Request` import from starlette is no longer used in the test file after removing tests, keep it only if `test_operator_helpers` still uses it (it does — for `get_request_metadata` test).

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `tests/conftest.py` | Remove template path setup (3 lines) |
| MODIFY | `tests/unit/test_customer_route_handlers.py` | Delete 9 tests, update 7 tests |
| MODIFY | `tests/unit/test_operator_route_handlers.py` | Delete 5 tests, update 3 tests |

---

## Test

### Step 1: Run all backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All tests must pass. The total count will be lower than 395 because we deleted tests for removed routes. Expected: approximately 375-385 tests.

### Step 2: Verify no broken test references

```bash
grep -n "sparkline_points\|redact_url\|to_float\|to_int" /home/opsconductor/simcloud/tests/unit/test_customer_route_handlers.py /home/opsconductor/simcloud/tests/unit/test_operator_route_handlers.py || echo "No dead references"
```

Should show "No dead references".

### Step 3: Verify no template references in tests

```bash
grep -n "text/html\|TemplateResponse\|templates\." /home/opsconductor/simcloud/tests/unit/test_customer_route_handlers.py /home/opsconductor/simcloud/tests/unit/test_operator_route_handlers.py /home/opsconductor/simcloud/tests/conftest.py || echo "No template references"
```

Should show "No template references".

---

## Acceptance Criteria

- [ ] All backend tests pass (no failures)
- [ ] conftest.py no longer references templates
- [ ] No test asserts `text/html` content-type from routes
- [ ] Tests for removed routes are deleted
- [ ] Tests for JSON-only routes updated (no `?format=json` param)
- [ ] Redirect tests updated for `/app/` target
- [ ] Helper tests updated for removed functions
- [ ] No dead references to `sparkline_points`, `redact_url`, `to_float`, `to_int` in tests

---

## Commit

```
Fix tests for SPA cutover — remove template assertions

Delete tests for removed Jinja routes (dashboard, integration
pages, admin forms). Update dual-format tests to JSON-only.
Update redirect assertions to /app/. Remove dead helper
function references.

Phase 22 Task 3: Fix Tests
```
