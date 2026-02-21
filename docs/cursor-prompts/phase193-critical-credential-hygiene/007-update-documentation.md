# Task 7: Update Documentation

## Context

Phase 193 removed all hardcoded credential defaults from every microservice. Services now fail fast at startup if required environment variables are absent. Operators and developers need to know which variables are mandatory.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/operations/deployment.md` | Add section noting all credential env vars are now required (no defaults) |
| `docs/development/getting-started.md` | Ensure local dev setup instructions list all required vars with example values |

## For Each File

1. Read the current content.
2. Update the relevant sections:
   - In `deployment.md`: add or update an "Environment Variables" section that marks credential vars as required (no default). Link to `compose/.env.example` if it exists.
   - In `getting-started.md`: ensure the local setup section instructs developers to copy `.env.example` to `.env` and fill in all required values before starting services.
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `193` to the `phases` array
4. Verify no stale information remains (e.g., old instructions saying defaults are fine).

## Additional Action

If `compose/.env.example` does not exist, create it as a copy of `compose/.env` with all secret values replaced by descriptive placeholders, e.g.:
```
PG_PASS=<required: postgresql password>
ADMIN_KEY=<required: hex secret, generate with: openssl rand -hex 32>
STRIPE_SECRET_KEY=<required: from Stripe dashboard>
```
This gives developers a clear template without committing real secrets.
