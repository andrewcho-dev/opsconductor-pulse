# Task 3: Strengthen Integration Test Assertions

## Context

Integration tests in `tests/integration/` use patterns like:
```python
assert resp.status_code in (200, 403, 404)
assert desired_resp.status_code in (200, 201, 403)
```

These test that routes are reachable. They do not test that routes work correctly. A bug that returns 404 instead of 200 would pass these assertions.

## Actions

1. Read all files in `tests/integration/` (likely: `test_alert_pipeline.py`, `test_device_lifecycle.py`, `test_user_lifecycle.py`, and others).

2. For each test that uses `assert status_code in (...)`:

   **Pattern A** — "Accept any outcome because permissions might not be set up":
   - Identify why the test accepts 403. Usually it's because the test setup doesn't guarantee the right role/permissions.
   - Fix the test setup (fixtures) to create a user with the correct role, so the expected 200 is always returned.
   - Change `assert status_code in (200, 403)` to `assert status_code == 200`.

   **Pattern B** — "Genuinely uncertain outcome":
   - If the test intentionally tests an ambiguous state (e.g., "create device — might already exist"), document the ambiguity with a comment and accept the narrow set.
   - But still narrow it: `assert status_code in (200, 409)` is acceptable. `in (200, 403, 404)` is not.

3. After fixing assertions, also add at least one response body assertion for the most important test in each file:
   ```python
   assert resp.status_code == 200
   data = resp.json()
   assert "device_id" in data
   assert data["device_id"] == expected_device_id
   ```

4. Focus on `test_alert_pipeline.py` and `test_device_lifecycle.py` first — these cover the most critical business flows.

5. Do not add new test cases — only strengthen existing ones.

## Verification

```bash
grep -rn 'status_code in (' tests/integration/
# Should return far fewer results after this task, and no 3-tuple options
```
