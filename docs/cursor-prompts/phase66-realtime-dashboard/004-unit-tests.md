# Prompt 004 — Unit Tests

## File: `tests/unit/test_fleet_ws.py`

Read `services/ui_iot/ws_manager.py` and `services/ui_iot/routes/api_v2.py`.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_subscribe_fleet_sets_flag` — `manager.subscribe_fleet(ws_id)` → `conn.fleet_subscription == True`
2. `test_unsubscribe_fleet_clears_flag` — subscribe then unsubscribe → `conn.fleet_subscription == False`
3. `test_broadcast_fleet_summary_sends_to_subscribed` — two connections, only one subscribed to fleet → only subscribed one receives message
4. `test_broadcast_fleet_summary_tenant_isolation` — two connections different tenants, same fleet subscription → only matching tenant receives
5. `test_fetch_fleet_summary_for_tenant` — mock DB fetch → returns correct summary dict with online/stale/offline/total/active_alerts
6. `test_broadcast_ignores_stale_connection` — send_json raises exception → no crash, continues

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 6 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
