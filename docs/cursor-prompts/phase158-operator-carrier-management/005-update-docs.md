# Task 5: Update Documentation

## Files to Update

### 1. `docs/api/customer-endpoints.md`

**What changed:** New operator carrier endpoints added.

Add a new subsection under a "## Operator — Carrier Management" heading (or add to an existing operator section if one exists). Document:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/operator/carrier-integrations` | Operator | List all integrations cross-tenant. Query: `tenant_id`, `carrier_name`, `limit`, `offset` |
| POST | `/api/v1/operator/carrier-integrations` | Operator Admin | Create integration for a tenant. Body requires `tenant_id` |
| PUT | `/api/v1/operator/carrier-integrations/{id}` | Operator Admin | Update any integration |
| DELETE | `/api/v1/operator/carrier-integrations/{id}` | Operator Admin | Delete integration + unlink devices |

Note that these use `operator_connection()` (RLS bypass) and `log_operator_access()` for audit.

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `158` to the `phases` array

### 2. `docs/services/ui-iot.md`

**What changed:** Operator carrier management capabilities added.

In the existing "Carrier Integration" section, add a paragraph or subsection noting:
- Operators can manage carrier integrations across all tenants via `/api/v1/operator/carrier-integrations`
- These endpoints bypass RLS using `operator_connection()` and audit all access via `log_operator_access()`
- The operator UI is at `/operator/carriers` (frontend route)
- Write operations (create, update, delete) require `require_operator_admin`

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `158` to the `phases` array

### 3. `docs/features/device-management.md`

**What changed:** Operators now have a dedicated carrier management path.

In the "Carrier SIM provisioning" section, add a note:
- Operators can manage carrier integrations for any tenant from the Operator panel (`/operator/carriers`)
- This provides cross-tenant visibility into all carrier integrations with optional filtering by tenant or carrier name
- Operators can create, edit, and delete integrations across tenants without needing to impersonate

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `158` to the `phases` array

## Process for Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 158 changes
3. Update the YAML frontmatter:
   - Set `last-verified: 2026-02-19`
   - Add `158` to the `phases` array
   - Add `services/ui_iot/routes/operator.py` to `sources` if not already present
4. Verify no stale information remains
