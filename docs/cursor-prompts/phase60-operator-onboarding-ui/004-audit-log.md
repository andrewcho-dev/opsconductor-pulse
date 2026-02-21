# Prompt 004 — Frontend: Audit Log Page

Read `frontend/src/features/alerts/AlertListPage.tsx` for table + filter patterns.

## Create `frontend/src/features/operator/AuditLogPage.tsx`

Route: `/operator/audit-log`

Table columns:
- Timestamp (formatted)
- Tenant ID
- Category
- Severity (badge)
- Entity Type + Entity ID
- Message

Filters (top bar):
- Tenant ID (text input)
- Category (dropdown — populated from distinct values or: system/user/security/data)
- Severity (dropdown: info/warning/error)

Pagination: limit 50, offset.

## Acceptance Criteria

- [ ] AuditLogPage.tsx at /operator/audit-log
- [ ] Table with all columns
- [ ] Tenant/category/severity filters work
- [ ] Pagination
- [ ] `npm run build` passes
