# Task 3: Update Documentation

## Files to update
- `docs/operations/security.md`
- `docs/features/billing.md`

## For each file

1. Read the current content
2. Find the Stripe webhook security section added in phase 205
3. Update the idempotency description to reflect the atomic INSERT...RETURNING pattern:
   - Remove any mention of a separate SELECT check
   - Document that idempotency is enforced atomically via `INSERT ... ON CONFLICT DO NOTHING RETURNING event_id`
   - Note that `None` return from RETURNING means duplicate — no race window
4. Update YAML frontmatter:
   - Set `last-verified: 2026-02-20`
   - Add `209` to the `phases` array
