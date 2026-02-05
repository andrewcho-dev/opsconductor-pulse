# Task 005: Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 17 Tasks 001-004 added: Chart.js CDN, dynamic device charts, WebSocket live dashboard, and enhanced device list. This task verifies all existing tests still pass, adds any needed test fixes, and updates documentation.

**Read first**:
- `tests/unit/test_customer_route_handlers.py` — existing route handler tests. Task 4 changed the query function from `fetch_devices` to `fetch_devices_v2` in two route handlers. If any tests mock `fetch_devices` for those routes, they need to be updated to mock `fetch_devices_v2` instead.
- `services/ui_iot/db/queries.py` — verify `fetch_devices_v2` exists (added in Phase 16)
- `docs/cursor-prompts/README.md` — Phase 16 section exists, need to add Phase 17

---

## Task

### 5.1 Fix any broken tests from query function change

**File**: `tests/unit/test_customer_route_handlers.py` (MODIFY if needed)

Task 4 changed `customer_dashboard` and `list_devices` to call `fetch_devices_v2` instead of `fetch_devices`. If any existing unit tests mock `fetch_devices` for these routes, they will break because the code now calls a different function.

**How to check**: Search the test file for references to `fetch_devices` in the context of mocking the dashboard or device list routes. If found, update them to mock `fetch_devices_v2` instead.

The `fetch_devices_v2` function returns the same shape as `fetch_devices` but with an additional `state` field (dict) instead of individual `battery_pct`, `temp_c`, `rssi_dbm`, `snr_db` fields. Update mock return values accordingly:

Old format (fetch_devices):
```python
{"tenant_id": "t1", "device_id": "d1", "site_id": "s1", "status": "ONLINE",
 "last_seen_at": None, "battery_pct": "87.5", "temp_c": "24.2", "rssi_dbm": "-95", "snr_db": "8.5"}
```

New format (fetch_devices_v2):
```python
{"tenant_id": "t1", "device_id": "d1", "site_id": "s1", "status": "ONLINE",
 "last_seen_at": None, "last_heartbeat_at": None, "last_telemetry_at": None,
 "state": {"battery_pct": 87.5, "temp_c": 24.2, "rssi_dbm": -95, "snr_db": 8.5}}
```

**Important**: Only update mocks that are actually broken. Run the tests first to see which (if any) fail, then fix them. If all tests pass with no changes, skip this sub-task.

### 5.2 Update Phase 17 documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 17 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 16:

```markdown
## Phase 17: Modern Visualization Dashboard

**Goal**: Interactive Chart.js visualizations, WebSocket live updates, dynamic metric discovery.

**Directory**: `phase17-modern-dashboard/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-chartjs-setup.md` | Chart.js CDN, chart CSS classes | `[x]` | None |
| 2 | `002-dynamic-device-charts.md` | Replace sparklines with dynamic Chart.js charts | `[x]` | #1 |
| 3 | `003-websocket-live-dashboard.md` | WebSocket live alerts + stat refresh | `[x]` | #1 |
| 4 | `004-time-range-controls.md` | Enhanced device list with metric summary | `[x]` | #2 |
| 5 | `005-tests-and-documentation.md` | Test fixes and documentation | `[x]` | #1-#4 |

**Exit Criteria**:
- [x] Chart.js 4 loaded via CDN on all customer pages
- [x] Device detail page auto-discovers ALL metrics and creates Chart.js charts
- [x] Time-range buttons (1h, 6h, 24h, 7d) for historical telemetry
- [x] Dashboard alerts update in real-time via WebSocket
- [x] WebSocket connection indicator (Live/Offline)
- [x] Stat cards refresh every 30s via API v2
- [x] Device list shows metric count per device
- [x] Battery column handles both v1 and v2 data formats
- [x] XSS prevention in all dynamic content
- [x] All unit tests pass

**Visualization features**:
- **Dynamic metric charts**: Auto-discovers all metrics from API v2 telemetry data
- **Interactive Chart.js**: Tooltips, hover, responsive sizing
- **Time-range selection**: 1h, 6h, 24h, 7d buttons reload chart data
- **WebSocket live alerts**: Alert table updates without page reload
- **Connection status**: Visual indicator for WebSocket connectivity
- **Progressive enhancement**: Server renders initial data, JS enhances

**Architecture note**: No build step required. Chart.js loaded from jsDelivr CDN. WebSocket token passed from server via data attribute (httpOnly cookie not accessible to JS). Falls back to 60s meta-refresh if WebSocket or JS fails.
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `tests/unit/test_customer_route_handlers.py` | Fix mocks for fetch_devices_v2 if any tests break |
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 17 section |

---

## Test

### Step 1: Run ALL unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

ALL tests must pass. If any test fails due to the `fetch_devices` → `fetch_devices_v2` change in Task 4, fix it as described in 5.1.

### Step 2: Verify test counts

Check that the total test count is the same or higher than before Phase 17. No tests should have been removed.

---

## Acceptance Criteria

- [ ] All existing unit tests pass (fix any broken mocks)
- [ ] Phase 17 section added to cursor-prompts/README.md
- [ ] No regressions from query function change

---

## Commit

```
Update tests and documentation for Phase 17

Fix any test mocks affected by fetch_devices_v2 switch. Add
Phase 17 section to cursor-prompts README.

Phase 17 Task 5: Tests and Documentation
```
