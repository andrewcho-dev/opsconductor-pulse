# Prompt 003 — Nav + Route Wiring

Read `frontend/src/app/router.tsx`.
Read `frontend/src/components/layout/AppSidebar.tsx`.
Read `frontend/src/features/devices/DeviceListPage.tsx` — find the "Add Device" button.

## Add Route

In the customer routes section:
- `/devices/wizard` → DeviceOnboardingWizard

## Update DeviceListPage

Change (or add alongside) the "Add Device" button behavior:
- Keep existing "Add Device" button that opens AddDeviceModal for quick add
- Add a secondary "Guided Setup" link/button → navigates to `/devices/wizard`

Use a subtle secondary button style (outline or text link) so the quick-add modal remains the primary action.

## Acceptance Criteria

- [ ] `/devices/wizard` route registered
- [ ] "Guided Setup" link in DeviceListPage
- [ ] `npm run build` passes
