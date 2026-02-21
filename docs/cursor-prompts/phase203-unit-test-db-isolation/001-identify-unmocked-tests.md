Hey Cursor — first thing to do here is figure out exactly which test files are making real DB connections instead of using the mock.

Run this to get the full list of files with DB errors:

```bash
cd /home/opsconductor/simcloud && pytest -m unit -q 2>&1 | grep 'InvalidPasswordError' | sed 's/ERROR //' | cut -d: -f1 | sort -u
```

That gives you every test file that's hitting the real database. Read `tests/conftest.py` and look at the `patch_route_connection_contexts` fixture — understand exactly what it patches and why some test files are falling through it.

For each failing test file, determine which of these applies:

- **Needs mock fix**: The test is genuinely a unit test (no external deps, no integration logic) but it's just missing the DB patch. Fix: extend the autouse fixture or add a module-level mock.
- **Should be reclassified**: The test legitimately requires a real database. Fix: change its marker from `@pytest.mark.unit` to `@pytest.mark.integration`.

Write your findings into `docs/cursor-prompts/phase203-unit-test-db-isolation/001-findings.md` — one row per file, which category it falls into, and why. Don't fix anything yet. Just diagnose.
