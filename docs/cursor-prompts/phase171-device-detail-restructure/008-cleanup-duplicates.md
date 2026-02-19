# Task 8: Remove Deprecated Components and Fix Imports

## Components to Remove

After verifying all tabs work correctly, remove the following deprecated files:

### 1. `EditDeviceModal.tsx` — REMOVE

This is the simpler duplicate of `DeviceEditModal.tsx`. Check all imports across the codebase:

```bash
grep -r "EditDeviceModal" frontend/src/ --include="*.tsx" --include="*.ts"
```

Update any file that imports `EditDeviceModal` to use `DeviceEditModal` instead. Then delete `frontend/src/features/devices/EditDeviceModal.tsx`.

### 2. `DeviceConnectionPanel.tsx` — REMOVE

Consolidated into the Transport tab. Check imports:

```bash
grep -r "DeviceConnectionPanel" frontend/src/ --include="*.tsx" --include="*.ts"
```

Remove all imports and usages (should only have been in `DeviceDetailPage.tsx` which was already restructured). Then delete the file.

### 3. `DeviceCarrierPanel.tsx` — REMOVE

Consolidated into the Transport tab. Same process — check imports, remove usages, delete file.

### 4. `DeviceConnectivityPanel.tsx` — REMOVE

Consolidated into the Transport tab. Same process.

### 5. `DeviceDetailPane.tsx` — REVIEW

Check if `DeviceDetailPane.tsx` is still used elsewhere (it was an alternative detail pane for split layouts). If it's not referenced anywhere besides as a secondary view, it can be removed. If it IS used (e.g., in a side panel or drawer), update it to use the new tab structure or simplify it.

```bash
grep -r "DeviceDetailPane" frontend/src/ --include="*.tsx" --include="*.ts"
```

## Import Cleanup

After removing files, ensure no broken imports remain:

```bash
cd frontend && npx tsc --noEmit
```

Fix any TypeScript errors from missing imports.

## Update DeviceDetailPage test

Check if `DeviceDetailPage.test.tsx` exists and update it to account for the new tab structure. At minimum, ensure it doesn't reference removed components.

## Verification

```bash
# No broken imports
cd frontend && npx tsc --noEmit

# No references to removed components
grep -r "DeviceConnectionPanel\|DeviceCarrierPanel\|DeviceConnectivityPanel\|EditDeviceModal" frontend/src/ --include="*.tsx" --include="*.ts"
# Should return no results (except the import in the new Transport tab if reusing)

# Build succeeds
cd frontend && npm run build
```
