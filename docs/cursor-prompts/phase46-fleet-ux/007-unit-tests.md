# Prompt 007 — Unit Tests for Backend Filters + Frontend Components

## Backend Tests

Add to `tests/unit/test_customer_route_handlers.py` or a new file `tests/unit/test_device_filters.py`.

Follow existing FakeConn/FakePool/AsyncMock patterns. `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`

### Tests for `fetch_devices_v2()` filter logic

```python
async def test_fetch_devices_v2_returns_total():
    """Result includes a 'total' key alongside 'devices'."""
    conn = FakeConn()
    conn.fetchval_result = 5   # total count
    conn.fetch_result = [...]  # 5 device rows
    result = await fetch_devices_v2(conn, "tenant-a", limit=10, offset=0)
    assert "total" in result
    assert "devices" in result
    assert result["total"] == 5

async def test_fetch_devices_v2_status_filter_adds_where_clause():
    """When status='ONLINE' is passed, the SQL WHERE includes status condition."""
    conn = FakeConn()
    conn.fetchval_result = 0
    conn.fetch_result = []
    await fetch_devices_v2(conn, "tenant-a", status="ONLINE")
    # Assert the fetch query contains ONLINE filter
    assert any("ONLINE" in str(call) for call in conn.fetch_calls)

async def test_fetch_devices_v2_no_filter_returns_all():
    """No filters = no extra WHERE clauses beyond tenant_id."""
    conn = FakeConn()
    conn.fetchval_result = 3
    conn.fetch_result = [{...}, {...}, {...}]
    result = await fetch_devices_v2(conn, "tenant-a")
    assert result["total"] == 3

async def test_fetch_devices_v2_tag_filter():
    """Tags filter passed to query as array parameter."""
    conn = FakeConn()
    conn.fetchval_result = 1
    conn.fetch_result = [...]
    await fetch_devices_v2(conn, "tenant-a", tags=["rack-a", "rack-b"])
    # Assert tag array appears in a fetch call
    assert any(["rack-a", "rack-b"] in str(call) or "rack-a" in str(call)
               for call in conn.fetch_calls)

async def test_fetch_fleet_summary_returns_correct_shape():
    """Fleet summary returns ONLINE/STALE/OFFLINE/total."""
    conn = FakeConn()
    conn.fetch_result = [
        {"status": "ONLINE", "count": 10},
        {"status": "STALE", "count": 3},
    ]
    summary = await fetch_fleet_summary(conn, "tenant-a")
    assert summary["ONLINE"] == 10
    assert summary["STALE"] == 3
    assert summary["OFFLINE"] == 0   # default zero fill
    assert summary["total"] == 13
```

### Tests for the endpoint

```python
async def test_list_devices_endpoint_returns_total():
    """GET /devices response includes total count."""
    # Mock fetch_devices_v2 to return {"devices": [], "total": 42}
    # Assert response JSON has "total": 42

async def test_list_devices_invalid_status_returns_400():
    """GET /devices?status=INVALID returns 400."""

async def test_fleet_summary_endpoint():
    """GET /devices/summary returns ONLINE/STALE/OFFLINE/total."""
```

## Frontend Tests

Add to `frontend/src/features/devices/DeviceListPage.test.tsx`.

Follow existing Vitest/testing-library patterns in the project.

```typescript
it("passes search query to fetchDevices", async () => {
  // mock fetchDevices
  // render DeviceListPage
  // type "sensor-01" in search input
  // wait for debounce
  // assert fetchDevices called with { q: "sensor-01" }
});

it("clicking status card filters to that status", async () => {
  // mock useFleetSummary to return {ONLINE:5, STALE:2, OFFLINE:1, total:8}
  // render page
  // click "Online" card
  // assert fetchDevices called with { status: "ONLINE" }
});

it("shows total count in pagination", async () => {
  // mock fetchDevices to return { devices: [], total: 847, ... }
  // render page
  // assert "847" appears in the pagination display
});
```

## Acceptance Criteria

- [ ] Backend: 5+ tests for `fetch_devices_v2` filter logic
- [ ] Backend: 3+ tests for the endpoint (total, invalid status, summary)
- [ ] Frontend: 3+ tests covering search, status filter, total display
- [ ] `pytest -m unit -v` passes — 0 failures
- [ ] `cd frontend && npm run test -- --run` passes
