# Prompt 003 — Unit Tests

Read a passing test in `tests/unit/` to understand the FakeConn/FakePool pattern.

Create `tests/unit/test_bulk_device_import.py` with `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_import_valid_csv` — 2 valid rows → 2 ok results, inserted into DB
2. `test_import_invalid_row_missing_name` — row missing name → status=error, 1 failed
3. `test_import_exceeds_row_limit` — 501 rows → 400 response
4. `test_import_file_too_large` — mock file.read() returns 1.1 MB bytes → 413 response
5. `test_import_partial_success` — 3 rows, 1 invalid device_type → 2 ok, 1 error in results

All tests must pass under `pytest -m unit -v`.
