# Task 004: User Profile & Preferences Page

## Commit message
```
feat: add user profile preferences page with timezone support
```

## Overview
Full-stack feature: DB migration for `user_preferences` table, FastAPI backend routes for GET/PUT preferences, and a new frontend ProfilePage at `/settings/profile` with display name, timezone selector, and notification preferences. Add "Profile" link to the sidebar Settings group.

---

## Part A: Database Migration

### Create `db/migrations/081_user_preferences.sql`

Follow the existing migration pattern (see `db/migrations/080_iam_permissions.sql` for reference). The migration number is 081 (next in sequence after 080).

```sql
-- Migration 081: User preferences (timezone, display name, notification prefs)
-- Date: 2026-02-16

CREATE TABLE IF NOT EXISTS user_preferences (
    tenant_id       TEXT NOT NULL,
    user_id         TEXT NOT NULL,       -- Keycloak sub claim
    display_name    VARCHAR(100),
    timezone        VARCHAR(50) NOT NULL DEFAULT 'UTC',
    notification_prefs JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, user_id)
);

-- Enable RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences FORCE ROW LEVEL SECURITY;

-- Tenant isolation policy (same pattern as user_role_assignments)
DROP POLICY IF EXISTS user_preferences_tenant_isolation ON user_preferences;
CREATE POLICY user_preferences_tenant_isolation
    ON user_preferences
    FOR ALL
    TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Index for fast lookup by user
CREATE INDEX IF NOT EXISTS idx_user_preferences_user
    ON user_preferences (tenant_id, user_id);

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO pulse_operator;
```

---

## Part B: Backend Route

### Create `services/ui_iot/routes/preferences.py`

Follow the exact pattern from `services/ui_iot/routes/roles.py`:
- Use `APIRouter` with `tags=["preferences"]`
- Use `JWTBearer()` dependency for auth
- Use `inject_tenant_context` to set tenant context
- Use `get_tenant_id()` and `get_user()` from `middleware.tenant`
- Use `tenant_connection(pool, tenant_id)` for DB access with RLS
- Use Pydantic `BaseModel` for request validation

```python
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import get_tenant_id, get_user, inject_tenant_context
from db.pool import tenant_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["preferences"])


class UserPreferencesResponse(BaseModel):
    tenant_id: str
    user_id: str
    display_name: Optional[str] = None
    timezone: str = "UTC"
    notification_prefs: dict = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    notification_prefs: Optional[dict] = None


VALID_TIMEZONES = [
    "UTC",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Toronto", "America/Vancouver", "America/Sao_Paulo", "America/Mexico_City",
    "Europe/London", "Europe/Berlin", "Europe/Paris", "Europe/Madrid", "Europe/Rome",
    "Europe/Amsterdam", "Europe/Stockholm", "Europe/Warsaw", "Europe/Moscow",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Singapore",
    "Asia/Seoul", "Asia/Kolkata", "Asia/Dubai", "Asia/Bangkok",
    "Australia/Sydney", "Australia/Melbourne", "Australia/Perth",
    "Pacific/Auckland", "Pacific/Honolulu",
    "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos",
]


@router.get(
    "/customer/preferences",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def get_preferences(request: Request):
    """Get current user's preferences. Returns defaults if no row exists."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user identity")

    pool = request.app.state.pool
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, user_id, display_name, timezone,
                   notification_prefs, created_at, updated_at
            FROM user_preferences
            WHERE tenant_id = $1 AND user_id = $2
            """,
            tenant_id,
            user_id,
        )

    if row:
        return {
            "tenant_id": row["tenant_id"],
            "user_id": row["user_id"],
            "display_name": row["display_name"],
            "timezone": row["timezone"],
            "notification_prefs": dict(row["notification_prefs"]) if row["notification_prefs"] else {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    # Return defaults if no row exists
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "display_name": None,
        "timezone": "UTC",
        "notification_prefs": {},
        "created_at": None,
        "updated_at": None,
    }


@router.put(
    "/customer/preferences",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def update_preferences(payload: UpdatePreferencesRequest, request: Request):
    """Upsert the current user's preferences."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user identity")

    # Validate timezone if provided
    if payload.timezone is not None and payload.timezone not in VALID_TIMEZONES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timezone: {payload.timezone}. Must be one of the supported IANA timezones.",
        )

    # Validate display_name length
    if payload.display_name is not None and len(payload.display_name.strip()) == 0:
        # Allow clearing display_name by setting to None/empty
        pass

    pool = request.app.state.pool
    import json

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_preferences (tenant_id, user_id, display_name, timezone, notification_prefs)
            VALUES ($1, $2, $3, COALESCE($4, 'UTC'), COALESCE($5::jsonb, '{}'::jsonb))
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET
                display_name = COALESCE($3, user_preferences.display_name),
                timezone = COALESCE($4, user_preferences.timezone),
                notification_prefs = COALESCE($5::jsonb, user_preferences.notification_prefs),
                updated_at = NOW()
            RETURNING tenant_id, user_id, display_name, timezone, notification_prefs, created_at, updated_at
            """,
            tenant_id,
            user_id,
            payload.display_name.strip() if payload.display_name else None,
            payload.timezone,
            json.dumps(payload.notification_prefs) if payload.notification_prefs is not None else None,
        )

    return {
        "tenant_id": row["tenant_id"],
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "timezone": row["timezone"],
        "notification_prefs": dict(row["notification_prefs"]) if row["notification_prefs"] else {},
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "message": "Preferences saved",
    }
```

### Register the router in `services/ui_iot/app.py`

Add the import and include the router. Follow the existing pattern:

```python
# At the top with other route imports (around line 44):
from routes.preferences import router as preferences_router

# In the router registration block (around line 186, after roles_router):
app.include_router(preferences_router)
```

---

## Part C: Frontend API Service

### Create `frontend/src/services/api/preferences.ts`

```typescript
import { apiGet, apiPut } from "./client";

export interface UserPreferences {
  tenant_id: string;
  user_id: string;
  display_name: string | null;
  timezone: string;
  notification_prefs: {
    email_digest_frequency?: "daily" | "weekly" | "disabled";
    [key: string]: unknown;
  };
  created_at: string | null;
  updated_at: string | null;
}

export interface UpdatePreferencesPayload {
  display_name?: string | null;
  timezone?: string;
  notification_prefs?: Record<string, unknown>;
}

export async function fetchPreferences(): Promise<UserPreferences> {
  return apiGet("/customer/preferences");
}

export async function updatePreferences(
  payload: UpdatePreferencesPayload
): Promise<UserPreferences & { message: string }> {
  return apiPut("/customer/preferences", payload);
}

export const TIMEZONE_OPTIONS = [
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
  { value: "America/New_York", label: "Eastern Time (New York)" },
  { value: "America/Chicago", label: "Central Time (Chicago)" },
  { value: "America/Denver", label: "Mountain Time (Denver)" },
  { value: "America/Los_Angeles", label: "Pacific Time (Los Angeles)" },
  { value: "America/Toronto", label: "Eastern Time (Toronto)" },
  { value: "America/Vancouver", label: "Pacific Time (Vancouver)" },
  { value: "America/Sao_Paulo", label: "Brasilia Time (Sao Paulo)" },
  { value: "America/Mexico_City", label: "Central Time (Mexico City)" },
  { value: "Europe/London", label: "GMT (London)" },
  { value: "Europe/Berlin", label: "CET (Berlin)" },
  { value: "Europe/Paris", label: "CET (Paris)" },
  { value: "Europe/Madrid", label: "CET (Madrid)" },
  { value: "Europe/Rome", label: "CET (Rome)" },
  { value: "Europe/Amsterdam", label: "CET (Amsterdam)" },
  { value: "Europe/Stockholm", label: "CET (Stockholm)" },
  { value: "Europe/Warsaw", label: "CET (Warsaw)" },
  { value: "Europe/Moscow", label: "MSK (Moscow)" },
  { value: "Asia/Tokyo", label: "JST (Tokyo)" },
  { value: "Asia/Shanghai", label: "CST (Shanghai)" },
  { value: "Asia/Hong_Kong", label: "HKT (Hong Kong)" },
  { value: "Asia/Singapore", label: "SGT (Singapore)" },
  { value: "Asia/Seoul", label: "KST (Seoul)" },
  { value: "Asia/Kolkata", label: "IST (Kolkata)" },
  { value: "Asia/Dubai", label: "GST (Dubai)" },
  { value: "Asia/Bangkok", label: "ICT (Bangkok)" },
  { value: "Australia/Sydney", label: "AEST (Sydney)" },
  { value: "Australia/Melbourne", label: "AEST (Melbourne)" },
  { value: "Australia/Perth", label: "AWST (Perth)" },
  { value: "Pacific/Auckland", label: "NZST (Auckland)" },
  { value: "Pacific/Honolulu", label: "HST (Honolulu)" },
  { value: "Africa/Cairo", label: "EET (Cairo)" },
  { value: "Africa/Johannesburg", label: "SAST (Johannesburg)" },
  { value: "Africa/Lagos", label: "WAT (Lagos)" },
] as const;
```

---

## Part D: Frontend Hook

### Create `frontend/src/hooks/use-preferences.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPreferences,
  updatePreferences,
  type UpdatePreferencesPayload,
} from "@/services/api/preferences";

export function usePreferences() {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: fetchPreferences,
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdatePreferencesPayload) => updatePreferences(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
    },
  });
}
```

---

## Part E: Frontend ProfilePage

### Create `frontend/src/features/settings/ProfilePage.tsx`

The page displays a form with:
1. **Display name** -- text input, pre-filled from preferences
2. **Email** -- read-only, from Keycloak token (`useAuth().user.email`)
3. **Timezone** -- select dropdown using `TIMEZONE_OPTIONS`
4. **Notification preferences** -- email digest frequency radio group (daily / weekly / disabled)
5. **Save button** -- calls `useUpdatePreferences` mutation, shows toast on success

```typescript
import { useState, useEffect } from "react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useAuth } from "@/services/auth/AuthProvider";
import { usePreferences, useUpdatePreferences } from "@/hooks/use-preferences";
import { TIMEZONE_OPTIONS } from "@/services/api/preferences";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Save, User } from "lucide-react";

export default function ProfilePage() {
  const { user } = useAuth();
  const { data: preferences, isLoading } = usePreferences();
  const updateMutation = useUpdatePreferences();
  const { toast } = useToast();

  const [displayName, setDisplayName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [digestFrequency, setDigestFrequency] = useState<"daily" | "weekly" | "disabled">("disabled");

  // Sync form state when preferences load
  useEffect(() => {
    if (preferences) {
      setDisplayName(preferences.display_name ?? "");
      setTimezone(preferences.timezone ?? "UTC");
      setDigestFrequency(
        (preferences.notification_prefs?.email_digest_frequency as "daily" | "weekly" | "disabled") ?? "disabled"
      );
    }
  }, [preferences]);

  const handleSave = () => {
    updateMutation.mutate(
      {
        display_name: displayName || null,
        timezone,
        notification_prefs: {
          email_digest_frequency: digestFrequency,
        },
      },
      {
        onSuccess: () => {
          toast({
            title: "Preferences saved",
            description: "Your profile settings have been updated.",
          });
        },
        onError: () => {
          toast({
            title: "Error",
            description: "Failed to save preferences. Please try again.",
            variant: "destructive",
          });
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Profile"
        description="Manage your display name, timezone, and notification preferences."
      />

      <div className="grid gap-6 max-w-2xl">
        {/* Personal Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <User className="h-4 w-4" />
              Personal Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="display-name">Display Name</Label>
              <Input
                id="display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Enter your display name"
                maxLength={100}
              />
              <p className="text-xs text-muted-foreground">
                This name will be shown in team views and activity logs.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                value={user?.email ?? ""}
                disabled
                readOnly
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">
                Email is managed by your identity provider and cannot be changed here.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Timezone Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Timezone</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="timezone">Display timezone</Label>
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger id="timezone" className="w-full">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONE_OPTIONS.map((tz) => (
                  <SelectItem key={tz.value} value={tz.value}>
                    {tz.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Timestamps across the application will be displayed in this timezone.
            </p>
          </CardContent>
        </Card>

        {/* Notification Preferences Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Notification Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Label>Email Digest Frequency</Label>
              <RadioGroup
                value={digestFrequency}
                onValueChange={(v) => setDigestFrequency(v as "daily" | "weekly" | "disabled")}
                className="space-y-2"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="daily" id="digest-daily" />
                  <Label htmlFor="digest-daily" className="font-normal">
                    Daily summary
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="weekly" id="digest-weekly" />
                  <Label htmlFor="digest-weekly" className="font-normal">
                    Weekly summary
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="disabled" id="digest-disabled" />
                  <Label htmlFor="digest-disabled" className="font-normal">
                    Disabled (no email digests)
                  </Label>
                </div>
              </RadioGroup>
              <p className="text-xs text-muted-foreground">
                Receive a periodic summary of fleet activity and alerts to your email.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Preferences
          </Button>
        </div>
      </div>
    </div>
  );
}
```

### Important notes on Shadcn components used

- **Select**: Uses `@/components/ui/select` (should already exist as a Shadcn component). If it does not exist yet, you need to create it. Check `frontend/src/components/ui/` for `select.tsx`. If missing, generate it using the Shadcn pattern with `@radix-ui/react-select`.
- **RadioGroup**: Uses `@/components/ui/radio-group`. The project already has `@radix-ui/react-radio-group` in `package.json`. If `radio-group.tsx` does not exist in `components/ui/`, create the standard Shadcn wrapper.
- **Toast**: Uses `useToast` from `@/hooks/use-toast`. If this hook does not exist yet (Phase 119 should have added it), create it or use whatever toast system Phase 119 established.
- **Label**: Uses `@/components/ui/label`. Should already exist.

---

## Part F: Add Route to Router

### Edit `frontend/src/app/router.tsx`

Add the import at the top:
```typescript
import ProfilePage from "@/features/settings/ProfilePage";
```

Add the route inside the `RequireCustomer` children array (around line 109, after the `subscription/renew` route):
```typescript
{ path: "settings/profile", element: <ProfilePage /> },
```

Full context:
```typescript
// Inside RequireCustomer children:
{ path: "subscription", element: <SubscriptionPage /> },
{ path: "subscription/renew", element: <RenewalPage /> },
{ path: "settings/profile", element: <ProfilePage /> },  // NEW
```

---

## Part G: Add "Profile" to Sidebar Settings Group

### Edit `frontend/src/components/layout/AppSidebar.tsx`

Add `UserCircle` (or `User`) to the lucide-react imports:
```typescript
import { ..., UserCircle } from "lucide-react";
```

Update the `settingsNav` array inside the `AppSidebar` component to include Profile as the first item:
```typescript
const settingsNav: NavItem[] = [
  { label: "Profile", href: "/settings/profile", icon: UserCircle },
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
  ...(canManageRoles ? [{ label: "Roles", href: "/roles", icon: Shield }] : []),
];
```

Note: This assumes task 002 has already removed the "Notification Prefs" broken link. If executing out of order, make sure "Notification Prefs" is not in the array.

---

## Verification

### Backend
1. Apply migration: `psql -f db/migrations/081_user_preferences.sql` (or through migration runner).
2. Start the backend. Verify no import errors.
3. Call `GET /customer/preferences` with a valid Bearer token. Should return default JSON with timezone "UTC".
4. Call `PUT /customer/preferences` with body `{ "display_name": "Test User", "timezone": "America/New_York" }`. Should return updated preferences.
5. Call `GET /customer/preferences` again. Should return the saved values.
6. Call `PUT /customer/preferences` with invalid timezone `{ "timezone": "Invalid/Zone" }`. Should return 400 error.

### Frontend
1. `cd frontend && npm run build` -- zero errors.
2. Navigate to `/settings/profile` (or click "Profile" in sidebar Settings group).
3. Page shows display name, read-only email, timezone dropdown, notification radio group.
4. Enter display name "Jane Doe", select "Eastern Time (New York)", select "Daily summary".
5. Click "Save Preferences". Toast appears "Preferences saved".
6. Refresh the page. Values persist (display name, timezone, digest frequency loaded from backend).
7. Email field is grayed out and not editable.
8. Sidebar Settings group shows "Profile" as the first item.

---

## Files Created/Modified

| Action | File |
|--------|------|
| CREATE | `db/migrations/081_user_preferences.sql` |
| CREATE | `services/ui_iot/routes/preferences.py` |
| MODIFY | `services/ui_iot/app.py` (add preferences_router import and include) |
| CREATE | `frontend/src/services/api/preferences.ts` |
| CREATE | `frontend/src/hooks/use-preferences.ts` |
| CREATE | `frontend/src/features/settings/ProfilePage.tsx` |
| MODIFY | `frontend/src/app/router.tsx` (add settings/profile route) |
| MODIFY | `frontend/src/components/layout/AppSidebar.tsx` (add Profile to settings nav) |
