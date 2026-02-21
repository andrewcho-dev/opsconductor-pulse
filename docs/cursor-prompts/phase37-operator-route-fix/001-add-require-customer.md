# Add RequireCustomer Route Guard

Add a `RequireCustomer` component to prevent operators from accessing customer routes.

## File to Modify

`frontend/src/app/router.tsx`

## Changes

### 1. Add RequireCustomer component (after RequireOperator)

```tsx
function RequireCustomer() {
  const { isCustomer, isOperator } = useAuth();
  // Operators redirect to operator dashboard
  if (isOperator && !isCustomer) return <Navigate to="/operator" replace />;
  // Non-customers redirect to login (shouldn't happen with login-required)
  if (!isCustomer) return <Navigate to="/" replace />;
  return <Outlet />;
}
```

### 2. Restructure routes to wrap customer pages

Change the router from flat structure to nested, wrapping customer routes with `RequireCustomer`:

```tsx
export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <HomeRedirect /> },
        // Customer routes (protected)
        {
          element: <RequireCustomer />,
          children: [
            { path: "dashboard", element: <DashboardPage /> },
            { path: "devices", element: <DeviceListPage /> },
            { path: "devices/:deviceId", element: <DeviceDetailPage /> },
            { path: "alerts", element: <AlertListPage /> },
            { path: "alert-rules", element: <AlertRulesPage /> },
            { path: "activity-log", element: <ActivityLogPage /> },
            { path: "metrics", element: <MetricsPage /> },
            { path: "integrations/webhooks", element: <WebhookPage /> },
            { path: "integrations/snmp", element: <SnmpPage /> },
            { path: "integrations/email", element: <EmailPage /> },
            { path: "integrations/mqtt", element: <MqttPage /> },
            { path: "subscription", element: <SubscriptionPage /> },
            { path: "subscription/renew", element: <RenewalPage /> },
          ],
        },
        // Operator routes (existing)
        {
          path: "operator",
          element: <RequireOperator />,
          children: [
            { index: true, element: <OperatorDashboard /> },
            { path: "devices", element: <OperatorDevices /> },
            { path: "tenants", element: <OperatorTenantsPage /> },
            { path: "tenants/:tenantId", element: <OperatorTenantDetailPage /> },
            { path: "subscriptions", element: <SubscriptionsPage /> },
            { path: "subscriptions/:subscriptionId", element: <SubscriptionDetailPage /> },
            { path: "system", element: <SystemDashboard /> },
            { path: "audit-log", element: <AuditLogPage /> },
            { path: "settings", element: <SettingsPage /> },
          ],
        },
      ],
    },
  ],
  { basename: "/app" }
);
```

## Key Points

- `RequireCustomer` checks both `isOperator` and `isCustomer` flags
- Operators are redirected to `/operator` instead of seeing 401 errors
- Customer routes are now protected from operator access
- The index route (`HomeRedirect`) remains outside the guards since it handles routing logic itself

## Verification

1. Build frontend: `cd frontend && npm run build`
2. Restart UI service: `docker compose restart ui`
3. Login as operator user
4. Should land on `/operator` dashboard without any 401 errors
5. Manually try `/app/dashboard` → should redirect back to `/operator`
