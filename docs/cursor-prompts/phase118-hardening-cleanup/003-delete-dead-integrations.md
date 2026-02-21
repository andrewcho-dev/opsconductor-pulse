# 003 — Delete Dead Frontend Integrations

## Context

`frontend/src/features/integrations/` contains 6 orphaned files. No component in the app imports from them. The router already has 4 redirect entries at lines 99-102 of `frontend/src/app/router.tsx` that redirect `/integrations/*` → `/notifications`. The pages are never rendered.

## Files to Delete

Delete the entire directory:

```
frontend/src/features/integrations/DeleteIntegrationDialog.tsx
frontend/src/features/integrations/EmailPage.tsx
frontend/src/features/integrations/MqttPage.tsx
frontend/src/features/integrations/SnmpPage.tsx
frontend/src/features/integrations/TestDeliveryButton.tsx
frontend/src/features/integrations/WebhookPage.tsx
```

```bash
rm -rf frontend/src/features/integrations/
```

## Keep the Redirect Routes

**DO NOT** remove the redirect routes in `frontend/src/app/router.tsx` (lines 99-102). They provide backward compatibility for bookmarked URLs:

```tsx
{ path: "integrations", element: <Navigate to="/notifications" replace /> },
{ path: "integrations/*", element: <Navigate to="/notifications" replace /> },
{ path: "customer/integrations", element: <Navigate to="/notifications" replace /> },
{ path: "customer/integrations/*", element: <Navigate to="/notifications" replace /> },
```

## Update README

In `README.md`, remove the `integrations/` row from the Frontend Feature Modules table (line 170):

```
# REMOVE this line:
| `integrations/` | Legacy webhook/SNMP/email/MQTT integrations |
```

## Rebuild Frontend

```bash
cd frontend && npm run build
```

Ensure the build succeeds with no errors.

## Commit

```bash
git add -A frontend/src/features/integrations/ README.md
git commit -m "chore: delete dead integrations feature module (redirects preserved)"
```

## Verification

```bash
# Directory is gone
ls frontend/src/features/integrations/
# Should error: No such file or directory

# No imports remain
grep -r "features/integrations" frontend/src/
# Should return nothing (except possibly the router redirects which don't import)

# Frontend builds clean
cd frontend && npm run build
```
