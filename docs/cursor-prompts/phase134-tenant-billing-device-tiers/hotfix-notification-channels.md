# Hotfix -- Customer Notification Channels: RBAC + SMTP Form Fix

## Context

Customers cannot create notification channels. Three stacked bugs:

1. **RBAC**: `customer` Keycloak realm role bootstraps as "Viewer" system role, which has zero write permissions. `notifications.create` requires "Integration Manager" or "Full Admin".
2. **Frontend form binding**: `ChannelModal.tsx` email form reads `cfgValue("smtp_host")` (flat key) but the setter stores into `config.smtp.host` (nested object). Input appears to vanish.
3. **Missing form fields**: Email channel form only shows SMTP Host and Recipients. Missing: port, username, password, TLS toggle.

## Task

### Step 1: Fix RBAC Bootstrap — Customer Gets Full Admin

In `services/ui_iot/middleware/permissions.py`, line 52-55:

**Current:**
```python
            if "tenant-admin" in realm_roles:
                role_name = "Full Admin"
            elif "customer" in realm_roles:
                role_name = "Viewer"
```

**Replace with:**
```python
            if "tenant-admin" in realm_roles or "customer" in realm_roles:
                role_name = "Full Admin"
```

**Rationale**: Within an RLS-scoped tenant, customers should have full operational control by default. The tenant admin can restrict specific users to Viewer or custom roles through the IAM system. "Viewer" as default makes the platform non-functional for customers.

### Step 2: Fix Existing Users Already Bootstrapped as Viewer

Users who already logged in are stuck with "Viewer" because bootstrap only runs when no role assignment exists. Create a migration to re-bootstrap them.

Create `db/migrations/098_fix_customer_viewer_bootstrap.sql`:

```sql
-- Migration 098: Fix customer users incorrectly bootstrapped as Viewer
--
-- The bootstrap logic previously mapped 'customer' Keycloak realm role to
-- 'Viewer' system role, which has read-only permissions. Customers need
-- 'Full Admin' within their tenant to manage devices, alerts, channels, etc.
--
-- This upgrades all system-bootstrap Viewer assignments to Full Admin.

UPDATE user_role_assignments
SET role_id = (
    SELECT id FROM roles WHERE name = 'Full Admin' AND is_system = true AND tenant_id IS NULL
)
WHERE assigned_by = 'system-bootstrap'
  AND role_id = (
    SELECT id FROM roles WHERE name = 'Viewer' AND is_system = true AND tenant_id IS NULL
  );
```

### Step 3: Fix Email Channel Form in ChannelModal.tsx

In `frontend/src/features/notifications/ChannelModal.tsx`, replace the entire email channel section (lines 198-224):

**Current (broken):**
```tsx
{draft.channel_type === "email" && (
  <div className="space-y-2">
    <label className="text-xs text-muted-foreground">SMTP Host</label>
    <Input
      placeholder="smtp.example.com"
      value={cfgValue("smtp_host")}
      onChange={(e) =>
        setCfgObj("smtp", {
          ...(typeof draft.config.smtp === "object" && draft.config.smtp ? draft.config.smtp : {}),
          host: e.target.value,
        })
      }
    />
    <label className="text-xs text-muted-foreground">Recipients (comma separated)</label>
    <Input
      placeholder="ops@example.com, noc@example.com"
      value={cfgValue("to")}
      onChange={(e) => {
        const list = e.target.value
          .split(",")
          .map((entry) => entry.trim())
          .filter(Boolean);
        setCfgObj("recipients", { to: list });
        setCfg("to", e.target.value);
      }}
    />
  </div>
)}
```

**Replace with:**
```tsx
{draft.channel_type === "email" && (
  <div className="space-y-2">
    <div className="grid gap-2 md:grid-cols-2">
      <div className="md:col-span-2">
        <label className="text-xs text-muted-foreground">SMTP Host</label>
        <Input
          placeholder="smtp.example.com"
          value={
            typeof draft.config.smtp === "object" && draft.config.smtp
              ? (draft.config.smtp as Record<string, unknown>).host as string || ""
              : ""
          }
          onChange={(e) =>
            setCfgObj("smtp", {
              ...(typeof draft.config.smtp === "object" && draft.config.smtp
                ? (draft.config.smtp as Record<string, unknown>)
                : {}),
              host: e.target.value,
            })
          }
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground">SMTP Port</label>
        <Input
          type="number"
          placeholder="587"
          value={
            typeof draft.config.smtp === "object" && draft.config.smtp
              ? (draft.config.smtp as Record<string, unknown>).port as string || "587"
              : "587"
          }
          onChange={(e) =>
            setCfgObj("smtp", {
              ...(typeof draft.config.smtp === "object" && draft.config.smtp
                ? (draft.config.smtp as Record<string, unknown>)
                : {}),
              port: parseInt(e.target.value) || 587,
            })
          }
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground">Username</label>
        <Input
          placeholder="noreply@example.com"
          value={
            typeof draft.config.smtp === "object" && draft.config.smtp
              ? (draft.config.smtp as Record<string, unknown>).username as string || ""
              : ""
          }
          onChange={(e) =>
            setCfgObj("smtp", {
              ...(typeof draft.config.smtp === "object" && draft.config.smtp
                ? (draft.config.smtp as Record<string, unknown>)
                : {}),
              username: e.target.value,
            })
          }
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground">Password</label>
        <Input
          type="password"
          placeholder="••••••••"
          value={
            typeof draft.config.smtp === "object" && draft.config.smtp
              ? (draft.config.smtp as Record<string, unknown>).password as string || ""
              : ""
          }
          onChange={(e) =>
            setCfgObj("smtp", {
              ...(typeof draft.config.smtp === "object" && draft.config.smtp
                ? (draft.config.smtp as Record<string, unknown>)
                : {}),
              password: e.target.value,
            })
          }
        />
      </div>
      <div className="flex items-center gap-2 pt-4">
        <input
          type="checkbox"
          checked={
            typeof draft.config.smtp === "object" && draft.config.smtp
              ? (draft.config.smtp as Record<string, unknown>).use_tls !== false
              : true
          }
          onChange={(e) =>
            setCfgObj("smtp", {
              ...(typeof draft.config.smtp === "object" && draft.config.smtp
                ? (draft.config.smtp as Record<string, unknown>)
                : {}),
              use_tls: e.target.checked,
            })
          }
        />
        <label className="text-xs text-muted-foreground">Use TLS</label>
      </div>
    </div>
    <div>
      <label className="text-xs text-muted-foreground">Recipients (comma separated)</label>
      <Input
        placeholder="ops@example.com, noc@example.com"
        value={cfgValue("to")}
        onChange={(e) => {
          const list = e.target.value
            .split(",")
            .map((entry) => entry.trim())
            .filter(Boolean);
          setCfgObj("recipients", { to: list });
          setCfg("to", e.target.value);
        }}
      />
    </div>
  </div>
)}
```

### Step 4: Fix Submit Handler

The submit handler (lines 81-91) already properly reads from the nested `config.smtp` object and fills defaults. Verify it still works with the new form — the `smtp` object in config should now have `host`, `port`, `username`, `password`, `use_tls` populated from the form instead of mostly empty.

No code change needed here — the existing submit logic is correct:
```typescript
const smtp = (config.smtp as Record<string, unknown>) || {};
config.smtp = {
  host: smtp.host || "",
  port: smtp.port || 587,        // ← now from form instead of hardcoded
  username: smtp.username || "",  // ← now from form instead of empty
  password: smtp.password || "",  // ← now from form instead of empty
  use_tls: smtp.use_tls !== false,
};
```

Update it to preserve the port value from the form:
```typescript
const smtp = (config.smtp as Record<string, unknown>) || {};
config.smtp = {
  host: smtp.host || "",
  port: typeof smtp.port === "number" ? smtp.port : 587,
  username: smtp.username || "",
  password: smtp.password || "",
  use_tls: smtp.use_tls !== false,
};
```

## Verify

```bash
# 1. Run migration
docker compose -f compose/docker-compose.yml exec ui python -m scripts.migrate

# 2. Rebuild frontend
cd frontend && npm run build

# 3. Rebuild ui
docker compose -f compose/docker-compose.yml up -d --build ui

# 4. Log in as customer1 — should now have Full Admin permissions
# 5. Navigate to Notification Channels → Add Channel → Email (SMTP)
# 6. Verify form shows: SMTP Host, Port, Username, Password, TLS toggle, Recipients
# 7. Fill out and save — should succeed (no 403)

# 8. Verify role assignment was upgraded
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT ura.user_id, r.name FROM user_role_assignments ura JOIN roles r ON r.id = ura.role_id WHERE ura.assigned_by = 'system-bootstrap'"
```

## Commit

```
fix: upgrade customer bootstrap from Viewer to Full Admin, fix SMTP channel form

Change RBAC bootstrap so 'customer' Keycloak realm role maps to
'Full Admin' instead of 'Viewer'. Customers need write permissions
within their tenant to manage devices, alerts, and notification
channels. Migration 098 upgrades existing Viewer bootstrap assignments.

Fix ChannelModal email form: correct field binding bug where SMTP
host value was lost (read from flat key, stored in nested object).
Add missing SMTP fields: port, username, password, TLS toggle.
```
