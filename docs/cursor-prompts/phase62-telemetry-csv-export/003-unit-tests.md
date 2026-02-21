# Prompt 003 — Unit Tests

## File: `tests/unit/test_telemetry_export.py`

Read a passing test in `tests/unit/` for FakeConn/FakePool pattern.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_export_csv_returns_streaming_response` — fetch returns rows → response Content-Type is text/csv
2. `test_export_csv_has_content_disposition` — Content-Disposition header contains filename
3. `test_export_csv_metric_keys_as_columns` — metrics JSONB with keys temperature/humidity → CSV headers include those keys
4. `test_export_csv_empty_returns_headers` — no rows → CSV with headers only, no error
5. `test_export_csv_invalid_range` — range="99y" → 400
6. `test_export_csv_limit_param` — limit=100 → query uses LIMIT 100
7. `test_export_csv_tenant_isolation` — WHERE clause includes tenant_id=$1

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 7 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
