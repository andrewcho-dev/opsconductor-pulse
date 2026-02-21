# Prompt 004 — Frontend: Delivery Log Page

Read `frontend/src/features/alerts/AlertListPage.tsx` for table/pagination patterns.

## Create `frontend/src/features/delivery/DeliveryLogPage.tsx`

A page at route `/delivery-log` showing delivery job history.

Table columns:
- Job ID
- Alert ID (link to alert if possible)
- Integration (name/id)
- Status (badge: COMPLETED=green, FAILED=red, PENDING=yellow, PROCESSING=blue)
- Attempts
- Last Error (truncated, expandable)
- Event (OPEN/CLOSED)
- Created At

Features:
- Status filter dropdown (ALL / PENDING / COMPLETED / FAILED)
- Pagination (limit 50, offset)
- Expandable row: clicking a row loads and shows attempt history (GET /delivery-jobs/{id}/attempts)

## Add API Functions

```typescript
export interface DeliveryJob {
  job_id: number;
  alert_id: number;
  integration_id: string;
  route_id: string;
  status: string;
  attempts: number;
  last_error: string | null;
  deliver_on_event: string;
  created_at: string;
  updated_at: string;
}

export async function fetchDeliveryJobs(params: {
  status?: string; integration_id?: string; limit?: number; offset?: number;
}): Promise<{ jobs: DeliveryJob[]; total: number }> {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.integration_id) qs.set('integration_id', params.integration_id);
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.offset) qs.set('offset', String(params.offset));
  return apiFetch(`/customer/delivery-jobs?${qs}`);
}

export async function fetchDeliveryJobAttempts(jobId: number) {
  return apiFetch(`/customer/delivery-jobs/${jobId}/attempts`);
}
```

## Navigation

Add "Delivery Log" link to nav menu under Integrations.

## Acceptance Criteria

- [ ] DeliveryLogPage.tsx at `/delivery-log`
- [ ] Table with all columns listed above
- [ ] Status filter works
- [ ] Expandable row shows attempt history
- [ ] "Delivery Log" in nav
- [ ] `npm run build` passes
