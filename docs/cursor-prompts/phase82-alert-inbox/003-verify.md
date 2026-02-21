# Prompt 003 — Verify Phase 82

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] Severity tabs with counts (All / Critical / High / Medium / Low / Ack'd / Closed)
- [ ] Bulk checkbox selection with Ack/Close bulk actions
- [ ] Search/filter input
- [ ] ··· action menu with Ack/Close/Silence/View Device per row
- [ ] Inline expandable detail row (▶ chevron)
- [ ] Detail panel shows all alert fields + action buttons
- [ ] DigestSettingsCard removed from alert page
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 82: Redesign alert list as professional inbox with severity tabs and bulk actions

- Severity-filtered tabs with counts (All/Critical/High/Medium/Low/Ack'd/Closed)
- Bulk checkbox selection with Ack All / Close All actions
- Search/filter by device name or alert type
- Per-row action menu: Ack, Close, Silence, View Device
- Inline expandable detail row (no navigation/modal)
- DigestSettingsCard moved out of alert page"
git push origin main
git log --oneline -3
```
