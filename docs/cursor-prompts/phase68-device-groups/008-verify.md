# Prompt 008 — Verify Phase 68

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
- [ ] `061_device_groups.sql` exists
- [ ] `device_groups` table with RLS
- [ ] `device_group_members` junction table with RLS
- [ ] `group_ids TEXT[]` on alert_rules

### Backend
- [ ] GET/POST/PATCH/DELETE /customer/device-groups
- [ ] GET/PUT/DELETE /customer/device-groups/{id}/devices/{device_id}
- [ ] group_ids on AlertRuleCreate/Update
- [ ] Evaluator skips rules for non-member devices

### Frontend
- [ ] DeviceGroupsPage at /device-groups
- [ ] Create/edit/delete groups
- [ ] Add/remove members
- [ ] Group selector in AlertRuleDialog
- [ ] Nav link + routes

### Unit Tests
- [ ] test_device_groups.py with 11 tests

## Report

Output PASS / FAIL per criterion.
