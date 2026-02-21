# Phase 90 — Frontend: Reports Page

## New files
- `frontend/src/features/reports/ReportsPage.tsx`
- `frontend/src/services/api/reports.ts`

## API service: reports.ts

```typescript
export interface SLASummary {
  period_days: number;
  total_devices: number;
  online_devices: number;
  online_pct: number;
  total_alerts: number;
  unresolved_alerts: number;
  mttr_minutes: number | null;
  top_alerting_devices: Array<{ device_id: string; count: number }>;
}

export interface ReportRun {
  run_id: number;
  report_type: string;
  status: string;
  triggered_by: string;
  row_count: number | null;
  created_at: string;
  completed_at: string | null;
}

// Trigger a CSV download with auth header
export async function exportDevicesCSV(): Promise<void>
export async function exportAlertsCSV(days: number): Promise<void>
export async function getSLASummary(days?: number): Promise<SLASummary>
export async function listReportRuns(): Promise<{ runs: ReportRun[] }>
```

For CSV exports, fetch with the auth header, get a Blob, create a temporary
`<a download>` and click it programmatically.

## ReportsPage layout

### Section 1 — Quick Exports (Card)

Title: "Export Data"

Two buttons in a row:
- **Export Devices (CSV)** → calls `exportDevicesCSV()`, shows spinner while loading
- **Export Alerts — Last 30 days (CSV)** → calls `exportAlertsCSV(30)`

### Section 2 — SLA Summary (Card)

Title: "SLA Summary — Last 30 days"  [Refresh button]

Grid of 4 metric tiles:
| Online % | Total Alerts | Unresolved | MTTR |
|----------|-------------|------------|------|
| 94.2%    | 142         | 12         | 45m  |

Color coding for Online %:
- ≥ 95% → green text
- 80–95% → yellow text
- < 80% → red text

Below: "Top Alerting Devices" table (device_id | alert count)

Data from: `useQuery(['sla-summary'], () => getSLASummary(30), { staleTime: 60000 })`

### Section 3 — Report History (Card)

Title: "Recent Reports"

Table columns: Type | Status | Triggered By | Rows | Started | Duration

Duration = `completed_at - created_at` formatted as "Xs" or "Xm Xs".

Data from: `useQuery(['report-runs'], listReportRuns, { refetchInterval: 10000 })`

## Route + Sidebar

- Add to `frontend/src/app/router.tsx`:
  ```tsx
  { path: '/reports', element: <ReportsPage /> }
  ```
- Add "Reports" link under Data & Integrations group in `AppSidebar.tsx`
