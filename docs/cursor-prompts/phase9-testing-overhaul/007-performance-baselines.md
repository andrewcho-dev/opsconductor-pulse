# Task 007: Performance Baselines and Benchmarks

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Performance tests establish baselines so regressions can be detected.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

There are no performance measurements anywhere in the project. No response time assertions, no throughput benchmarks, no baseline numbers. When the system slows down, nobody will know until users complain.

We need three categories of performance tests:
1. **API response time benchmarks** — how long each endpoint takes under normal conditions
2. **Database query benchmarks** — how long tenant-scoped queries take with realistic data volumes
3. **Page load time assertions** — how long browser page loads take

**Dependencies**: `pytest-benchmark` (added in task 001 via `requirements-test.txt`)

**Read first**:
- `services/ui_iot/routes/customer.py` (key endpoints to benchmark)
- `services/ui_iot/db/queries.py` (query functions to benchmark)
- `tests/e2e/conftest.py` (Playwright setup for page load timing)

---

## Task

### 7.1 Create `tests/benchmarks/test_api_performance.py`

Benchmark key API endpoints using pytest-benchmark with the FastAPI TestClient.

```python
pytestmark = [pytest.mark.benchmark, pytest.mark.asyncio]
```

These tests use the ASGI test client (same as integration tests) but measure response time. They require Keycloak + Postgres.

**Benchmarks**:

- `test_benchmark_list_devices`:
  - Endpoint: GET /customer/devices?format=json
  - Measure: response time for listing devices
  - Assert: p95 < 200ms
  - Rounds: 20

- `test_benchmark_get_device_detail`:
  - Endpoint: GET /customer/devices/{device_id}?format=json
  - Measure: response time for single device lookup
  - Assert: p95 < 150ms
  - Rounds: 20

- `test_benchmark_list_alerts`:
  - Endpoint: GET /customer/alerts?format=json
  - Measure: response time
  - Assert: p95 < 200ms
  - Rounds: 20

- `test_benchmark_list_integrations`:
  - Endpoint: GET /customer/integrations
  - Measure: response time
  - Assert: p95 < 150ms
  - Rounds: 20

- `test_benchmark_auth_status`:
  - Endpoint: GET /api/auth/status
  - Measure: response time (includes JWT validation)
  - Assert: p95 < 100ms
  - Rounds: 50

- `test_benchmark_debug_auth`:
  - Endpoint: GET /debug/auth
  - Measure: response time (includes Keycloak health check)
  - Assert: p95 < 2000ms (external call)
  - Rounds: 10

- `test_benchmark_operator_list_all_devices`:
  - Endpoint: GET /operator/devices
  - Measure: response time (cross-tenant query)
  - Assert: p95 < 300ms
  - Rounds: 20

**Implementation notes**:
- Use `pytest-benchmark` fixture: `def test_benchmark_list_devices(benchmark, client, customer_a_token):`
- Benchmark the async call: `benchmark.pedantic(coroutine, rounds=20, warmup_rounds=3)`
- For async functions with pytest-benchmark, you may need a wrapper:
  ```python
  import asyncio
  def run_async(coro):
      loop = asyncio.get_event_loop()
      return loop.run_until_complete(coro)
  ```
- Or use `benchmark(lambda: asyncio.get_event_loop().run_until_complete(client.get(...)))`

### 7.2 Create `tests/benchmarks/test_query_performance.py`

Benchmark database queries directly.

```python
pytestmark = [pytest.mark.benchmark, pytest.mark.asyncio]
```

**Setup**: Seed the test database with realistic data volumes before benchmarking:
- 100 devices across 5 tenants (20 per tenant)
- 500 alerts across the devices
- 50 integrations across the tenants
- 200 delivery jobs

**Benchmarks**:

- `test_benchmark_query_devices_by_tenant`:
  - Query: SELECT from device_state WHERE tenant_id = $1
  - Assert: p95 < 50ms (indexed query)
  - Rounds: 50

- `test_benchmark_query_alerts_by_tenant`:
  - Query: SELECT from fleet_alert WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 50
  - Assert: p95 < 100ms
  - Rounds: 50

- `test_benchmark_query_integrations_by_tenant`:
  - Query: SELECT from integrations WHERE tenant_id = $1
  - Assert: p95 < 50ms
  - Rounds: 50

- `test_benchmark_query_delivery_jobs_pending`:
  - Query: SELECT from delivery_jobs WHERE status = 'pending' ORDER BY created_at LIMIT 10
  - Assert: p95 < 100ms
  - Rounds: 50

- `test_benchmark_query_cross_tenant_devices`:
  - Query: SELECT from device_state (no tenant filter — operator view)
  - Assert: p95 < 200ms
  - Rounds: 20

- `test_benchmark_rls_overhead`:
  - Compare query time with SET LOCAL app.tenant_id vs without
  - Measure: RLS overhead per query
  - Document the overhead (don't assert — just establish baseline)

**Cleanup**: Remove seeded data after benchmarks.

### 7.3 Create `tests/e2e/test_page_load_performance.py`

Measure page load times in a real browser.

```python
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]
```

**Page load benchmarks** (use `authenticated_customer_page` fixture):

- `test_page_load_dashboard`:
  - Navigate to /customer/dashboard
  - Measure time from navigation start to DOMContentLoaded
  - Assert: < 3000ms

- `test_page_load_devices`:
  - Navigate to /customer/devices
  - Measure time until device table is visible
  - Assert: < 3000ms

- `test_page_load_webhooks`:
  - Navigate to /customer/webhooks
  - Measure time until integration list is visible
  - Assert: < 3000ms

- `test_page_load_snmp`:
  - Navigate to /customer/snmp-integrations
  - Assert: < 3000ms

- `test_page_load_email`:
  - Navigate to /customer/email-integrations
  - Assert: < 3000ms

**Implementation**:
Use Playwright's performance timing:
```python
async def measure_page_load(page, url):
    start = time.monotonic()
    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")
    return time.monotonic() - start
```

Or use the browser's Performance API:
```python
timing = await page.evaluate("JSON.stringify(performance.timing)")
```

### 7.4 Document baseline numbers

Create `tests/benchmarks/BASELINES.md` documenting the initial baseline measurements:

```markdown
# Performance Baselines

Generated: [date]
Environment: [machine specs, Docker, etc.]

## API Response Times (p95)
| Endpoint | Baseline | Threshold |
|----------|----------|-----------|
| GET /customer/devices | Xms | 200ms |
| GET /customer/alerts | Xms | 200ms |
| GET /api/auth/status | Xms | 100ms |
| GET /operator/devices | Xms | 300ms |

## Database Query Times (p95)
| Query | Baseline | Threshold |
|-------|----------|-----------|
| devices by tenant | Xms | 50ms |
| alerts by tenant | Xms | 100ms |
| cross-tenant devices | Xms | 200ms |

## Page Load Times
| Page | Baseline | Threshold |
|------|----------|-----------|
| Customer Dashboard | Xms | 3000ms |
| Customer Devices | Xms | 3000ms |

Update baselines by running:
pytest -m benchmark -v --benchmark-json=benchmark_results.json
```

Fill in the actual baseline numbers after running the benchmarks.

---

## Files to Create

| Action | Path |
|--------|------|
| CREATE | `tests/benchmarks/test_api_performance.py` |
| CREATE | `tests/benchmarks/test_query_performance.py` |
| CREATE | `tests/e2e/test_page_load_performance.py` |
| CREATE | `tests/benchmarks/BASELINES.md` |

---

## Test

```bash
# 1. Install pytest-benchmark if not already installed
pip install pytest-benchmark

# 2. Run API benchmarks
source compose/.env
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest tests/benchmarks/test_api_performance.py -v --benchmark-enable

# 3. Run query benchmarks
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest tests/benchmarks/test_query_performance.py -v --benchmark-enable

# 4. Run page load tests
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/test_page_load_performance.py -v

# 5. Generate JSON report for tracking
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest tests/benchmarks/ -v --benchmark-json=benchmark_results.json

# 6. Update BASELINES.md with actual numbers
```

---

## Acceptance Criteria

- [ ] `test_api_performance.py` benchmarks 7 key API endpoints
- [ ] `test_query_performance.py` benchmarks 6 database queries
- [ ] `test_page_load_performance.py` measures 5 page load times
- [ ] All benchmarks pass their threshold assertions
- [ ] `BASELINES.md` documents actual baseline numbers
- [ ] Benchmark results can be exported to JSON for tracking
- [ ] All existing tests still pass

---

## Commit

```
Add performance baselines and benchmarks

- API response time benchmarks for 7 key endpoints
- Database query benchmarks for 6 query patterns
- Browser page load time assertions for 5 pages
- Baseline numbers documented in BASELINES.md
- JSON export for tracking performance over time

Part of Phase 9: Testing Overhaul
```
