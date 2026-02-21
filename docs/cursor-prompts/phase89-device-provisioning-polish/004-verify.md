# Phase 89 — Verify, Commit, Push

## Step 1: Build
```bash
cd frontend && npm run build 2>&1 | tail -20
```
Must exit 0 with no TypeScript errors.

## Step 2: Manual smoke checks

### Wizard
- Navigate to `/devices/wizard`
- Step 1 renders with Device ID, Name, Model, Site fields
- Invalid Device ID (e.g. "MY DEVICE") shows inline error
- Back/Next navigation works; step indicator updates
- Cancel on step 2+ shows confirm dialog

### Bulk Import
- Navigate to `/devices/import`
- "Download CSV Template" button downloads `device-import-template.csv`
- After selecting a CSV file, preview table appears within 1 second
- Invalid device_id cells highlighted in red

### Credential Rotation
- Open any device → Credentials tab
- Token age chip shows correct color
- "Create Token" → confirmation dialog appears
- After confirming → new token shown in masked one-time display
- "Reveal" toggles mask, "Copy" copies to clipboard

## Step 3: Commit and push
```bash
git add -A
git commit -m "feat: phase 89 - provisioning polish (wizard, CSV preview, credential rotation)"
git push origin main
git log --oneline -5
```
