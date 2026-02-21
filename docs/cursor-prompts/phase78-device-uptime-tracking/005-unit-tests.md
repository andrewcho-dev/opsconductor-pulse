# Prompt 005 — Unit Tests

Read a passing test in `tests/unit/` to understand the FakeConn/FakePool pattern.

Create `tests/unit/test_device_uptime.py` with `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_uptime_no_offline_alerts` — fetchrow returns no NO_TELEMETRY alerts -> uptime_pct = 100.0
2. `test_uptime_with_offline_period` — fetchrow returns 1 alert with 1800 offline seconds in 24h range -> uptime_pct ~= 97.9
3. `test_uptime_device_currently_offline` — open NO_TELEMETRY alert with no closed_at -> status = "offline"
4. `test_uptime_range_7d` — range=7d -> range_seconds = 604800 in calculation
5. `test_fleet_uptime_summary_counts` — 3 devices: 2 online, 1 offline -> response has online=2, offline=1
6. `test_fleet_uptime_avg_calculation` — verify avg_uptime_pct rounds correctly

All tests must pass under `pytest -m unit -v`.
