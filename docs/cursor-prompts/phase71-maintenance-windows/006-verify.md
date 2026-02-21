# Prompt 006 — Verify Phase 71

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Migration
- [ ] `062_maintenance_windows.sql` exists
- [ ] `alert_maintenance_windows` table with RLS
- [ ] `idx_maint_windows_active` index

### Backend
- [ ] GET/POST/PATCH/DELETE /customer/maintenance-windows

### Evaluator
- [ ] `is_in_maintenance()` in evaluator.py
- [ ] Called before every open_or_update_alert()
- [ ] Recurring schedule logic correct

### Frontend
- [ ] MaintenanceWindowsPage at /maintenance-windows
- [ ] Create/edit modal with recurring fields
- [ ] Nav link registered

### Unit Tests
- [ ] test_maintenance_windows.py with 9 tests

## Report

Output PASS / FAIL per criterion.
