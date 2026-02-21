Now that you have the findings from task 1, apply the fixes.

For every test file categorized as "needs mock fix":

Read the test file. Find where it acquires a DB connection — it's probably calling a route function or dependency directly that internally calls `get_db()` or `get_pool()`. The fix is to ensure the autouse mock in `conftest.py` covers that path.

The cleanest approach: add a `pytest.fixture(autouse=True)` at the module level in each failing test file that patches the specific DB acquisition path used by that module. Example pattern:

```python
@pytest.fixture(autouse=True)
def mock_db_pool(mocker):
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.execute = AsyncMock(return_value="OK")
    mock_conn.fetchval = AsyncMock(return_value=None)
    mocker.patch("routes.<module>.get_db", return_value=mock_conn)
    mocker.patch("routes.<module>.get_pool", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn)))
    return mock_conn
```

Adjust the patch target to match the actual import path used in each test file.

For every test file categorized as "should be reclassified": change `@pytest.mark.unit` to `@pytest.mark.integration` on those tests. Don't change any test logic.

After all fixes, run:

```bash
cd /home/opsconductor/simcloud && pytest -m unit -q 2>&1 | tail -5
```

Errors must be zero. If any remain, go back and fix them before moving on.
