# Prompt 004 — Frontend: Maintenance Windows Page

Read `frontend/src/features/alerts/AlertListPage.tsx` for layout patterns.

## Create `frontend/src/features/alerts/MaintenanceWindowsPage.tsx`

Route: `/maintenance-windows`

List view:
- Table with columns: Name, Starts At, Ends At (or "Indefinite"), Recurring (Yes/No badge), Sites, Device Types, Enabled (toggle)
- "Add Window" button → opens CreateWindowModal
- "Edit" and "Delete" per row

## Create Window Modal

Fields:
- Name (required)
- Start Date/Time (datetime-local input, required)
- End Date/Time (optional — leave blank for indefinite)
- Recurring: checkbox → if checked shows:
  - Days of week (checkboxes: Sun/Mon/Tue/Wed/Thu/Fri/Sat)
  - Start Hour (0–23)
  - End Hour (1–24)
- Site IDs (multi-select or comma-separated, optional)
- Device Types (multi-select from known types, optional)
- Enabled toggle

## Add API Functions in `frontend/src/services/api/alerts.ts` (or a new maintenanceWindows.ts)

```typescript
export interface MaintenanceWindow {
  window_id: string;
  name: string;
  starts_at: string;
  ends_at: string | null;
  recurring: { dow: number[]; start_hour: number; end_hour: number } | null;
  site_ids: string[] | null;
  device_types: string[] | null;
  enabled: boolean;
  created_at: string;
}

export async function fetchMaintenanceWindows() { ... }
export async function createMaintenanceWindow(data: Partial<MaintenanceWindow>) { ... }
export async function updateMaintenanceWindow(id: string, data: Partial<MaintenanceWindow>) { ... }
export async function deleteMaintenanceWindow(id: string) { ... }
```

## Navigation

Add "Maintenance" link under Alerts in sidebar nav.
Register `/maintenance-windows` route.

## Acceptance Criteria

- [ ] MaintenanceWindowsPage.tsx at /maintenance-windows
- [ ] Create/edit/delete modals
- [ ] Recurring schedule fields shown conditionally
- [ ] Nav link + route registered
- [ ] `npm run build` passes
