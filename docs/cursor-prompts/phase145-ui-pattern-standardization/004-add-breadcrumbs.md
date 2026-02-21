# Task 4: Add Breadcrumbs to All Detail Pages

## Context

Only 2 of 8 detail pages have breadcrumbs. ALL detail pages must have breadcrumbs via the PageHeader `breadcrumbs` prop. No standalone "Back" buttons.

## Pattern

```tsx
<PageHeader
  title={itemName}
  description={itemDescription}
  breadcrumbs={[
    { label: "Parent List Page", href: "/parent-list-route" },
    { label: itemName || "..." },
  ]}
/>
```

## Pages to Fix

### 1. OtaCampaignDetailPage.tsx

```tsx
<PageHeader
  title={campaign.name}
  description={description}
  breadcrumbs={[
    { label: "OTA Campaigns", href: "/ota/campaigns" },
    { label: campaign.name || "..." },
  ]}
  action={/* keep existing action buttons */}
/>
```

### 2. OperatorTenantDetailPage.tsx

```tsx
<PageHeader
  title={data.name}
  description={`Tenant ID: ${data.tenant_id}`}
  breadcrumbs={[
    { label: "Tenants", href: "/operator/tenants" },
    { label: data.name || "..." },
  ]}
/>
```

Also remove the separate `<div className="flex items-center gap-2">` block below the header that has the status Badge and "Edit Tenant" button. Move the Edit Tenant button into the PageHeader `action` prop:
```tsx
action={
  <div className="flex items-center gap-2">
    <Badge variant={data.status === "ACTIVE" ? "default" : "destructive"}>
      {data.status}
    </Badge>
    <Button variant="outline" size="sm" onClick={() => setShowEdit(true)}>
      <Pencil className="mr-1 h-4 w-4" />
      Edit
    </Button>
  </div>
}
```

### 3. OperatorSubscriptionDetailPage.tsx

Remove the standalone "Back to Subscriptions" button and add breadcrumbs:
```tsx
<PageHeader
  title={sub.subscription_id}
  description={sub.description || `${sub.subscription_type} subscription for ${sub.tenant_name}`}
  breadcrumbs={[
    { label: "Subscriptions", href: "/operator/subscriptions" },
    { label: sub.subscription_id || "..." },
  ]}
/>
```

Delete the separate `<Button>` with `<ArrowLeft>` icon that currently serves as the back button.

### 4. UserDetailPage.tsx

```tsx
<PageHeader
  title={user.display_name || user.email}
  description={user.email}
  breadcrumbs={[
    { label: "Users", href: "/operator/users" },
    { label: user.display_name || user.email || "..." },
  ]}
/>
```

### 5. OperatorTenantDetailPage subscription sub-sections

If the tenant detail page links to subscription detail, ensure the breadcrumb chain is:
`Tenants > {Tenant Name} > Subscription {ID}` or just `Subscriptions > {ID}`.

### 6. JobsPage (if it has a detail view)

If JobsPage has an inline detail section, add breadcrumbs when viewing a specific job.

## Verify

After changes, navigate to each detail page and confirm:
- Breadcrumbs appear above the title
- Clicking the parent label navigates back to the list
- No standalone "Back" buttons remain

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
