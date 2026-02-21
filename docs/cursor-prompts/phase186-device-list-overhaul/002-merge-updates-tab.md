# Task 2: Merge Campaigns + Firmware into "Updates" Tab

## File

`frontend/src/features/devices/DevicesHubPage.tsx`

## Current State (5 tabs from Phase 185)

```tsx
<TabsTrigger value="list">Devices</TabsTrigger>
<TabsTrigger value="templates">Templates</TabsTrigger>
<TabsTrigger value="map">Map</TabsTrigger>
<TabsTrigger value="campaigns">Campaigns</TabsTrigger>   // MERGE
<TabsTrigger value="firmware">Firmware</TabsTrigger>      // MERGE
```

## Goal

Merge "Campaigns" and "Firmware" into a single **"Updates"** tab. Campaigns (active rollouts) is the primary view. Firmware (binary inventory) is secondary, shown below.

**Result: 4 tabs** — Devices, Templates, Map, Updates

## Changes

### A. Update valid tabs and triggers

Replace the `validTabs` array and tab triggers:

```tsx
const validTabs = ["list", "templates", "map", "updates"];
```

Replace the TabsList:
```tsx
<TabsList variant="line">
  <TabsTrigger value="list">Devices</TabsTrigger>
  <TabsTrigger value="templates">Templates</TabsTrigger>
  <TabsTrigger value="map">Map</TabsTrigger>
  <TabsTrigger value="updates">Updates</TabsTrigger>
</TabsList>
```

### B. Replace two TabsContent blocks with one combined "Updates" tab

Remove:
```tsx
<TabsContent value="campaigns" className="mt-4">
  <OtaCampaignsPage embedded />
</TabsContent>
<TabsContent value="firmware" className="mt-4">
  <FirmwareListPage embedded />
</TabsContent>
```

Replace with:
```tsx
<TabsContent value="updates" className="mt-4">
  <div className="space-y-8">
    <section>
      <h3 className="text-lg font-semibold mb-3">OTA Campaigns</h3>
      <OtaCampaignsPage embedded />
    </section>
    <section>
      <h3 className="text-lg font-semibold mb-3">Firmware Library</h3>
      <FirmwareListPage embedded />
    </section>
  </div>
</TabsContent>
```

### C. Update route redirects

In `frontend/src/app/router.tsx`, update existing redirect routes:

```tsx
// OLD:
{ path: "updates", element: <Navigate to="/devices?tab=campaigns" replace /> },
{ path: "ota/campaigns", element: <Navigate to="/devices?tab=campaigns" replace /> },
{ path: "ota/firmware", element: <Navigate to="/devices?tab=firmware" replace /> },

// NEW:
{ path: "updates", element: <Navigate to="/devices?tab=updates" replace /> },
{ path: "ota/campaigns", element: <Navigate to="/devices?tab=updates" replace /> },
{ path: "ota/firmware", element: <Navigate to="/devices?tab=updates" replace /> },
```

### D. Update CommandPalette

In `frontend/src/components/shared/CommandPalette.tsx`, update the pages array:

```tsx
// OLD:
{ label: "Campaigns", href: "/devices?tab=campaigns", icon: Activity },
{ label: "Firmware", href: "/devices?tab=firmware", icon: Activity },

// NEW:
{ label: "OTA Updates", href: "/devices?tab=updates", icon: Activity },
```

Remove the separate Firmware entry — it's now part of the Updates tab. Replace the two entries with one "OTA Updates" entry.

### Expected Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ Devices              [Devices] [Templates] [Map] [Updates]          │
│ Manage your device fleet                                            │
│                                                                     │
│ ── Updates tab ──                                                   │
│                                                                     │
│ OTA Campaigns                                    [Add Campaign]     │
│ ┌──────┬──────────┬──────────┬───────┬──────────┬─────────┬───────┐│
│ │ Name │ Status   │ Firmware │ Total │ Progress │ Created │ Acts  ││
│ ├──────┼──────────┼──────────┼───────┼──────────┼─────────┼───────┤│
│ │ v2.1 │ RUNNING  │ 2.1.0    │ 50    │ ████░ 30 │ Feb 19  │ Abort ││
│ └──────┴──────────┴──────────┴───────┴──────────┴─────────┴───────┘│
│                                                                     │
│ Firmware Library                                 [Add Firmware]     │
│ ┌─────────┬──────────────┬───────────┬──────┬──────────┬──────────┐│
│ │ Version │ Description  │ Dev Type  │ Size │ Checksum │ Created  ││
│ ├─────────┼──────────────┼───────────┼──────┼──────────┼──────────┤│
│ │ 2.1.0   │ Bug fixes... │ sensor-v2 │ 1 MB │ abc12... │ Feb 18  ││
│ │ 2.0.0   │ Initial rel  │ sensor-v2 │ 980K │ def45... │ Jan 30  ││
│ └─────────┴──────────────┴───────────┴──────┴──────────┴──────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Hub shows 4 tabs: Devices, Templates, Map, Updates
- Updates tab shows Campaigns table on top, Firmware table below
- "Add Campaign" and "Add Firmware" buttons both work
- `/ota/campaigns` and `/ota/firmware` redirect to `/devices?tab=updates`
- `/updates` redirects to `/devices?tab=updates`
- Old `?tab=campaigns` and `?tab=firmware` fall back to Devices tab (via validTabs guard)
- CommandPalette shows single "OTA Updates" entry
