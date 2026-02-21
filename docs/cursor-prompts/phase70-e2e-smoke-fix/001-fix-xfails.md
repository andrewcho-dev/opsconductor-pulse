# Prompt 001 — Fix xfail Markers

## Step 1: Confirm Routes Exist

Read `frontend/src/app/router.tsx` (or wherever routes are defined).

Check:
- Does `/app/integrations` (or `/integrations`) route exist? If yes → remove xfail.
- Does `/app/alert-rules/new` (or `/alert-rules/new`) route exist? If yes → remove xfail.

Note the actual route paths — they may be `/integrations` without the `/app` prefix depending on the router structure.

## Step 2: Update test_smoke.py

For each confirmed route:
1. Remove the `@pytest.mark.xfail(...)` decorator
2. Update the navigation URL to match the actual route path
3. Update the assertion selector to match actual page content (heading text, form element, etc.)

Read the existing passing tests (e.g., `test_devices_page_loads`) to understand the assertion pattern.

**For integrations page** — the page likely shows "Integrations" heading or a table. Update assertion accordingly.

**For alert rules create form** — Phase 53 added a template selector and Phase 65 added a multi-condition toggle. The form should have `input`, `select`, or a `form` element. Use a broad selector like `"form, input, select, [data-testid]"` first, then tighten if needed.

## Step 3: Also check for route path consistency

Verify that all other passing tests use the correct route prefix. If the app uses `/app/` prefix, check that each passing test's URL includes it.

## Acceptance Criteria

- [ ] `/app/integrations` xfail removed (or kept if route truly doesn't exist)
- [ ] `/app/alert-rules/new` xfail removed (or kept if route truly doesn't exist)
- [ ] Test selectors updated to match actual rendered content
- [ ] File has no Python syntax errors: `python -m py_compile tests/e2e/test_smoke.py`
