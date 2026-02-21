# Task 5: Update Documentation

## Files to update
- `docs/development/testing.md`

## For each file

1. Read the current content
2. Add a section on the fake DB pool pattern:
   - Explain that `FakePool` / `FakeConn` are used when no live DB is available
   - Show how to use `mock_conn` fixture + `set_response()` in tests
   - Show how to use factories from `tests/factories.py`
   - Note the `FakeRecord` wrapper that supports both dict and attribute access
3. Update YAML frontmatter:
   - Set `last-verified: 2026-02-20`
   - Add `208` to the `phases` array
4. Verify no stale information remains about the old `AsyncMock` approach
