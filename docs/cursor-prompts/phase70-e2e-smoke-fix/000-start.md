# Phase 70: E2E Smoke Test — Fix xfails + Full Run

## What Exists

- `tests/e2e/test_smoke.py` — 10 smoke tests, 2 marked xfail:
  1. `test_integrations_page_loads` — route `/app/integrations` marked `xfail(reason="integrations index route not implemented")`
  2. `test_alert_rule_create_form_loads` — route `/app/alert-rules/new` marked `xfail(reason="alert rule create route not implemented")`
- Playwright conftest in `tests/e2e/conftest.py`
- E2E tests require `RUN_E2E=true` env var

## What This Phase Does

1. **Fix xfail 1** — Verify `/app/integrations` route exists (it likely does after Phase 55). If so, remove the xfail marker and confirm the page loads in Playwright.
2. **Fix xfail 2** — Verify `/app/alert-rules/new` route exists (Phase 53 added rule templates; the create form should exist). If so, remove the xfail marker.
3. **Run full smoke suite** against the running compose stack
4. **Add missing assertions** — if tests pass collection but fail on assertions, tighten the selectors to match actual page content
5. **Document smoke run results** in a brief report

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Investigate xfail routes + fix markers |
| 002 | Run smoke suite + fix assertion failures |
| 003 | Verify all 10 tests pass |

## Key Files

- `tests/e2e/test_smoke.py` — prompts 001, 002
- `frontend/src/app/router.tsx` — confirm routes exist
