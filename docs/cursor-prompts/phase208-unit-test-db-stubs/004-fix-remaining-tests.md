# Task 4: Fix Remaining Failing Unit Tests

## What to do

### Step 1 — Get the full failure list

```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/ -q --tb=line 2>&1 | grep "FAILED" | head -50
```

### Step 2 — Group failures by root cause

Read the output. Group failing tests by which DB method they hit and which table.
Common patterns to look for:
- `fetchrow returned None` → route raised 404 or KeyError on None
- `fetch returned []` → route returned empty list but test expected data

### Step 3 — Fix in batches by test file

For each failing test file (work through them one at a time):

1. Read the test file
2. Read the corresponding route file to understand DB query shapes
3. Add `mock_conn` fixture + `set_response` calls to configure per-test DB responses
4. Use factories from `tests/factories.py` to build realistic records
5. Run just that test file to verify fixes:
   ```bash
   python -m pytest tests/unit/<test_file>.py -v --tb=short 2>&1 | tail -20
   ```

### Step 4 — Handle tests that need multiple DB calls

For tests where the route makes multiple different `fetchrow` calls in sequence, use
`AsyncMock(side_effect=[...])` to return different values per call:

```python
from unittest.mock import AsyncMock
mock_conn.fetchrow = AsyncMock(side_effect=[
    fake_tenant(),
    None,           # second call expected to return nothing (e.g. resource not found)
])
```

### Step 5 — Do NOT fix tests that fail for non-DB reasons

If a test fails because of a logic bug, missing feature, or incorrect assertion in
the test itself — DO NOT change the assertion. Leave it failing and note it in the
completion report with the test name and the actual vs expected values.

### Step 6 — Final count

```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/ -q --tb=no 2>&1 | tail -5
```

Target: reduce failures from 192 to under 20. Report the exact before/after numbers.
