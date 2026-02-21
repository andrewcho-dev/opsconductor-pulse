# Prompt 002 — Live Alert Count Badge on Monitoring Section

Read `frontend/src/components/layout/AppSidebar.tsx` after Prompt 001 changes.

## Add open alert count badge

Fetch the open alert count to display on the Monitoring group header and on
the Alerts nav item.

### Add API call in sidebar

```typescript
import { useQuery } from '@tanstack/react-query';
import { fetchAlerts } from '@/services/api/alerts';  // or apiFetch directly

const { data: alertData } = useQuery({
  queryKey: ['sidebar-alert-count'],
  queryFn: () => apiFetch('/customer/alerts?status=OPEN&limit=1'),
  refetchInterval: 30000,  // refresh every 30s
  enabled: isCustomer,
});
const openAlertCount = alertData?.total ?? alertData?.count ?? 0;
```

### Display badge

On the Alerts nav item:
```typescript
<div className="flex items-center justify-between w-full">
  <div className="flex items-center gap-2">
    <Bell className="h-4 w-4" />
    <span>Alerts</span>
  </div>
  {openAlertCount > 0 && (
    <Badge variant="destructive" className="h-5 min-w-5 text-xs px-1">
      {openAlertCount > 99 ? '99+' : openAlertCount}
    </Badge>
  )}
</div>
```

Also show a smaller dot badge on the Monitoring group label when collapsed:
```typescript
{!monitoringOpen && openAlertCount > 0 && (
  <span className="h-2 w-2 rounded-full bg-destructive inline-block ml-1" />
)}
```

## Acceptance Criteria
- [ ] Alert count badge visible on Alerts nav item when > 0
- [ ] Collapsed group shows red dot indicator when alerts exist
- [ ] Badge refreshes every 30s
- [ ] Badge shows 99+ when count exceeds 99
- [ ] `npm run build` passes
