# Task 5: Update Documentation

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/operations/security.md` | Add Stripe webhook security section: signature verification required, idempotency via stripe_events table, event allowlist, data re-fetch pattern |
| `docs/features/billing.md` | Update webhook handling description if this file exists |

## For Each File

1. Read the current content.
2. Update relevant sections.
3. Update YAML frontmatter: `last-verified: 2026-02-20`, add `205` to `phases` array.
4. Verify no stale information remains.
