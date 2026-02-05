# Task 005: Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 21 Tasks 1-4 added: API client layer (types, functions, hooks), alert rules CRUD page, four integration CRUD pages, and four operator pages. This task verifies everything builds and adds Phase 21 to the documentation.

**Read first**:
- `docs/cursor-prompts/README.md` — Phase 20 section exists, need to add Phase 21
- `frontend/src/services/api/` — verify API files exist
- `frontend/src/hooks/` — verify hook files exist
- `frontend/src/features/alerts/` — verify alert rules page
- `frontend/src/features/integrations/` — verify integration pages
- `frontend/src/features/operator/` — verify operator pages

---

## Task

### 5.1 Verify all Phase 21 files exist

Run these checks. If any file is missing, the corresponding task was not completed — go back and complete it.

```bash
# API client (Task 1)
ls frontend/src/services/api/alert-rules.ts
ls frontend/src/services/api/integrations.ts
ls frontend/src/services/api/operator.ts

# Hooks (Task 1)
ls frontend/src/hooks/use-alert-rules.ts
ls frontend/src/hooks/use-integrations.ts
ls frontend/src/hooks/use-operator.ts

# shadcn components (Task 1)
ls frontend/src/components/ui/switch.tsx
ls frontend/src/components/ui/label.tsx
ls frontend/src/components/ui/textarea.tsx

# Alert rules (Task 2)
ls frontend/src/features/alerts/AlertRulesPage.tsx
ls frontend/src/features/alerts/AlertRuleDialog.tsx

# Integrations (Task 3)
ls frontend/src/features/integrations/DeleteIntegrationDialog.tsx
ls frontend/src/features/integrations/TestDeliveryButton.tsx
ls frontend/src/features/integrations/WebhookPage.tsx
ls frontend/src/features/integrations/SnmpPage.tsx
ls frontend/src/features/integrations/EmailPage.tsx
ls frontend/src/features/integrations/MqttPage.tsx

# Operator (Task 4)
ls frontend/src/features/operator/OperatorDashboard.tsx
ls frontend/src/features/operator/OperatorDevices.tsx
ls frontend/src/features/operator/AuditLogPage.tsx
ls frontend/src/features/operator/SettingsPage.tsx
```

### 5.2 Update Phase 21 documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 21 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 20. The Phase 20 section should already exist — add Phase 21 right after it.

```markdown
## Phase 21: CRUD Pages + Operator Views

**Goal**: Implement all remaining page stubs — alert rules CRUD, integration management for all 4 types, and operator cross-tenant views.

**Directory**: `phase21-crud-pages/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-api-client-layer.md` | Types, API functions, hooks for all CRUD endpoints | `[x]` | None |
| 2 | `002-alert-rules-page.md` | Alert rules list + create/edit dialog | `[x]` | #1 |
| 3 | `003-integration-pages.md` | Webhook, SNMP, Email, MQTT pages | `[x]` | #1 |
| 4 | `004-operator-pages.md` | Operator dashboard, devices, audit log, settings | `[x]` | #1 |
| 5 | `005-tests-and-documentation.md` | Verification and documentation | `[x]` | #1-#4 |

**Exit Criteria**:
- [x] API client layer for alert rules, 4 integration types, and operator endpoints
- [x] TanStack Query hooks with mutations and cache invalidation
- [x] Alert rules CRUD page with create/edit dialog and severity display
- [x] Webhook integration page with card layout, test delivery
- [x] SNMP integration page with v2c/v3 config forms
- [x] Email integration page with SMTP config and recipient management
- [x] MQTT integration page with topic and QoS settings
- [x] All integration pages: create/edit/delete/test/toggle enabled
- [x] Operator dashboard with cross-tenant stats and tables
- [x] Operator devices with tenant filter and pagination
- [x] Audit log with role-gated access (operator_admin only)
- [x] Settings page for system mode and reject policies
- [x] Role-based access control (customer_admin for CRUD, operator_admin for audit/settings)
- [x] npm run build succeeds
- [x] All backend tests pass

**Architecture decisions**:
- **Customer CRUD via /customer/ endpoints**: The React SPA calls customer endpoints with Bearer auth. These endpoints support both cookie and Bearer token authentication, so the SPA works without changes.
- **Operator composed dashboard**: Instead of using the monolithic HTML-returning operator dashboard endpoint, the SPA calls individual JSON endpoints (/operator/devices, /operator/alerts, /operator/quarantine) and composes the dashboard from them.
- **Mutation + invalidation pattern**: All create/update/delete operations use TanStack Query mutations that invalidate the list query cache on success. This triggers an automatic refetch of the list.
- **Settings form encoding**: The backend settings POST expects `application/x-www-form-urlencoded` (not JSON), so the settings page uses a custom fetch with URLSearchParams.
- **No page stubs remaining**: All 14 routes in the router now have fully implemented pages.
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 21 section |

---

## Test

### Step 1: Verify frontend build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Run ALL backend unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

ALL tests must pass. No regressions from Phase 21.

### Step 4: Verify frontend file count

```bash
find /home/opsconductor/simcloud/frontend/src -name "*.ts" -o -name "*.tsx" | wc -l
```

Should be higher than Phase 20 count (Phase 20 had 84 files, Phase 21 adds ~18 more files).

### Step 5: Verify no page stubs remain

```bash
grep -r "will be implemented" /home/opsconductor/simcloud/frontend/src/features/ || echo "No stubs found - all pages implemented"
```

Should show "No stubs found" — all placeholder text should be replaced.

---

## Acceptance Criteria

- [ ] All Phase 21 files exist (API client, hooks, pages)
- [ ] `npm run build` succeeds
- [ ] `npx tsc --noEmit` succeeds
- [ ] All backend tests pass (395 tests)
- [ ] Phase 21 section added to cursor-prompts/README.md
- [ ] No page stubs remain in features/
- [ ] No regressions from Phase 21

---

## Commit

```
Update documentation for Phase 21 completion

Add Phase 21 section to cursor-prompts README. Verify all
CRUD pages, integration management, and operator views
are in place. No page stubs remain.

Phase 21 Task 5: Tests and Documentation
```
