# Task 000: Fix Test Infrastructure (Migration + Token Issuer)

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tests are failing due to two issues:

1. **Migration 011 CHECK constraint error**: `operator does not exist: integration_type = text`. Migration `011_snmp_integrations.sql` converts the `type` column from TEXT to an `integration_type` enum, then tries to create a CHECK constraint comparing the enum to text literals (`type = 'webhook'`). PostgreSQL requires explicit casts for enum-to-text comparisons.

2. **Token issuer mismatch**: The test conftest now defaults `KEYCLOAK_URL` to `http://localhost:8180`, but the running Keycloak may have `KC_HOSTNAME_URL` set to `http://192.168.10.53:8180`. The token's `iss` claim uses Keycloak's hostname, and `auth.py` validates against `KEYCLOAK_PUBLIC_URL`. If these differ, every token validation returns 401.

**Read first**:
- `db/migrations/011_snmp_integrations.sql` (lines 57-70: the failing CHECK constraint)
- `db/migrations/001_webhook_delivery_v1.sql` (line 11: original TEXT type column)
- `db/migrations/013_email_integrations.sql` (lines 20-22: drops and recreates type check)
- `tests/conftest.py` (lines 61-88: migration runner, line 17: KEYCLOAK_URL)
- `services/ui_iot/middleware/auth.py` (lines 14-17: KEYCLOAK_PUBLIC_URL, line 80: issuer check)

---

## Task

### 0.1 Fix the CHECK constraint in `011_snmp_integrations.sql`

The CHECK constraint on lines 64-68 compares an enum column to text literals. PostgreSQL needs explicit casts.

Change lines 64-68 from:

```sql
        ALTER TABLE integrations
        ADD CONSTRAINT integration_type_config_check CHECK (
            (type = 'webhook' AND (config_json->>'url') IS NOT NULL) OR
            (type = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL)
        );
```

To:

```sql
        ALTER TABLE integrations
        ADD CONSTRAINT integration_type_config_check CHECK (
            (type::text = 'webhook' AND (config_json->>'url') IS NOT NULL) OR
            (type::text = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL)
        );
```

The `::text` cast makes the comparison valid for both TEXT and enum column types.

### 0.2 Fix the conftest `KEYCLOAK_URL` to read from environment without hardcoding

The test conftest must use the same hostname that Keycloak uses for its `iss` claim. This must come from the environment — never hardcoded to any specific IP or hostname.

In `tests/conftest.py`, line 17, keep the default as `localhost` (this is fine — it's the generic dev default). The key fix is to also propagate `KEYCLOAK_PUBLIC_URL` so `auth.py` validates the token issuer against the same URL the tests use to acquire tokens.

Leave line 17 as:

```python
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
```

Add after line 18 (`os.environ.setdefault("KEYCLOAK_URL", KEYCLOAK_URL)`):

```python
os.environ.setdefault("KEYCLOAK_PUBLIC_URL", KEYCLOAK_URL)
```

This ensures `auth.py`'s issuer validation matches whatever `KEYCLOAK_URL` the tests are using. When running tests, pass the environment variable to match your Keycloak instance:

```bash
KEYCLOAK_URL=http://192.168.10.53:8180 pytest tests/ -v
```

No IP address should ever be hardcoded in source code.

### 0.3 Drop the broken constraint from the test database

The test database likely has the migration partially applied (type converted to enum but CHECK constraint failed). The conftest's `setup_delivery_tables` needs to clean up the broken state.

In `tests/conftest.py`, in the `setup_delivery_tables` fixture, add a cleanup step BEFORE running migrations. After line 64 (`async with db_pool.acquire() as conn:`), add:

```python
        # Clean up potentially broken constraints from previous runs
        await conn.execute("ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integration_type_config_check")
        await conn.execute("ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integrations_type_check")
```

This ensures migrations run on a clean slate.

### 0.4 Also check `013_email_integrations.sql` for the same issue

Check if migration 013 has similar enum-to-text comparison issues in its CHECK constraint. If the constraint on lines 20-22 compares enum to text:

```sql
ALTER TABLE integrations ADD CONSTRAINT integrations_type_check
    CHECK (type IN ('webhook', 'snmp', 'email'));
```

Change to:

```sql
ALTER TABLE integrations ADD CONSTRAINT integrations_type_check
    CHECK (type::text IN ('webhook', 'snmp', 'email'));
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `db/migrations/011_snmp_integrations.sql` (fix CHECK constraint casts) |
| MODIFY | `db/migrations/013_email_integrations.sql` (fix CHECK constraint cast if needed) |
| MODIFY | `tests/conftest.py` (add KEYCLOAK_PUBLIC_URL propagation, add constraint cleanup) |

---

## Test

```bash
# 1. Drop and recreate test database to start clean
psql -U iot -h localhost -d postgres -c "DROP DATABASE IF EXISTS iotcloud_test"
psql -U iot -h localhost -d postgres -c "CREATE DATABASE iotcloud_test"

# 2. Create base tables in test database (device_state, fleet_alert, app_settings, rate_limits)
# These are needed before migrations run. Check if there's a base schema file.
# If not, the test fixtures should create them. Run a quick check:
psql -U iot -h localhost -d iotcloud_test -c "\dt"

# 3. Run the test suite (pass KEYCLOAK_URL from environment — never hardcode)
KEYCLOAK_URL=${KEYCLOAK_URL:-http://192.168.10.53:8180} pytest tests/ -v --ignore=tests/e2e -x

# 4. If tests pass, run E2E (same — pass from environment)
KEYCLOAK_URL=${KEYCLOAK_URL:-http://192.168.10.53:8180} UI_BASE_URL=${UI_BASE_URL:-http://192.168.10.53:8080} RUN_E2E=1 pytest tests/e2e/ -v -x
```

**ALL tests must pass. Do not proceed to Task 001 until this is green.**

---

## Acceptance Criteria

- [ ] Migration 011 runs without `operator does not exist` error
- [ ] Migration 013 runs without type comparison errors
- [ ] No IP addresses hardcoded anywhere in source code or test code
- [ ] `KEYCLOAK_PUBLIC_URL` propagated from `KEYCLOAK_URL` in conftest
- [ ] `setup_delivery_tables` cleans up broken constraints before running migrations
- [ ] `KEYCLOAK_URL=http://192.168.10.53:8180 pytest tests/ -v --ignore=tests/e2e -x` all pass
- [ ] `RUN_E2E=1` E2E tests all pass (NOT skipped)

---

## Commit

```
Fix test infrastructure: migration type cast and issuer propagation

Migration 011 CHECK constraint failed because PostgreSQL cannot
compare an enum column to text literals without explicit cast.
Test conftest did not propagate KEYCLOAK_PUBLIC_URL, causing
auth.py issuer validation to reject tokens.

- Add ::text casts to enum comparisons in migrations 011 and 013
- Propagate KEYCLOAK_PUBLIC_URL from KEYCLOAK_URL in test conftest
- Add constraint cleanup before migration re-runs
- No hardcoded IP addresses in any source file

Part of Phase 8: Customer UI Fix
```
