# Task 3: Enhance PageHeader with Status Context

## File

`frontend/src/features/devices/DeviceDetailPage.tsx`

## Current Problem

The PageHeader just shows `device_id` as the title and `model` as the description. The device status is buried inside the DeviceInfoCard. There's no visual indicator at the page level that this device is ONLINE, OFFLINE, or STALE.

## Changes

### A. Add status dot to the page title

Change the PageHeader title to include a status indicator:

```tsx
<PageHeader
  title={
    <span className="flex items-center gap-2">
      {device && (
        <span className={`h-3 w-3 rounded-full ${statusDot(device.status)}`} />
      )}
      {device?.device_id ?? "Device"}
    </span>
  }
  description={
    device
      ? [device.model, device.site_id ? `Site: ${device.site_id}` : null]
          .filter(Boolean)
          .join(" · ") || undefined
      : undefined
  }
  breadcrumbs={[
    { label: "Devices", href: "/devices" },
    { label: device?.device_id ?? "..." },
  ]}
  action={
    <div className="flex items-center gap-2">
      {device?.template ? (
        <Badge variant="outline">
          <Link to={`/templates/${device.template.id}`}>{device.template.name}</Link>
        </Badge>
      ) : null}
      <Button size="sm" variant="outline" onClick={() => setEditModalOpen(true)}>
        Edit
      </Button>
      <Button size="sm" variant="outline" onClick={() => setCreateJobOpen(true)}>
        Create Job
      </Button>
    </div>
  }
/>
```

Note: Check if `PageHeader`'s `title` prop accepts `ReactNode`. If it only accepts `string`, wrap the status dot differently — either use the `description` prop or add the status dot as part of the `action` area. Read the PageHeader component to verify.

### B. Verify PageHeader accepts ReactNode for title

Read `frontend/src/components/shared/PageHeader.tsx` (or wherever it's defined). If `title` is typed as `string`, change it to `React.ReactNode` to allow JSX content.

If changing the PageHeader type isn't feasible (it may be used in many places with string), an alternative approach:

```tsx
<PageHeader
  title={device?.device_id ?? "Device"}
  description={
    device
      ? [device.model, device.site_id ? `Site: ${device.site_id}` : null]
          .filter(Boolean)
          .join(" · ") || undefined
      : undefined
  }
  breadcrumbs={[
    { label: "Devices", href: "/devices" },
    { label: device?.device_id ?? "..." },
  ]}
  action={
    <div className="flex items-center gap-2">
      {device && (
        <Badge
          variant="outline"
          className={
            device.status === "ONLINE"
              ? "border-green-500 text-green-600"
              : device.status === "STALE"
                ? "border-yellow-500 text-yellow-600"
                : "border-red-500 text-red-600"
          }
        >
          <span className={`mr-1.5 h-2 w-2 rounded-full inline-block ${statusDot(device.status)}`} />
          {device.status} · {relativeTime(device.last_seen_at)}
        </Badge>
      )}
      {device?.template ? (
        <Badge variant="outline">
          <Link to={`/templates/${device.template.id}`}>{device.template.name}</Link>
        </Badge>
      ) : null}
      <Button size="sm" variant="outline" onClick={() => setEditModalOpen(true)}>
        Edit
      </Button>
      <Button size="sm" variant="outline" onClick={() => setCreateJobOpen(true)}>
        Create Job
      </Button>
    </div>
  }
/>
```

This puts the status as a colored Badge in the action area — visible, prominent, and doesn't require changing the PageHeader component.

### C. Update the description to be more informative

Instead of just `device.model`, combine useful context:

```tsx
description={
  device
    ? [
        device.model,
        device.manufacturer,
        device.site_id ? `Site: ${device.site_id}` : null,
      ]
        .filter(Boolean)
        .join(" · ") || undefined
    : undefined
}
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Device status is visually prominent in the header area (colored badge with dot)
- Last seen time shown next to status
- Description includes model, manufacturer, and site
- Template badge still links to template detail
- Edit and Create Job buttons still work
