# Phase 28.9: Fix Create Tenant UX Issues

## Problems

1. Error messages from API not displaying properly (shows generic "Error" instead of "tenant_id must be...")
2. User confusion between Tenant ID (URL slug) and Display Name fields
3. Tenant ID regex requires minimum 3 chars (too strict for some use cases)

## Fix 1: Display API Error Details

**File:** `frontend/src/features/operator/CreateTenantDialog.tsx`

The Axios error detail is in `error.response?.data?.detail`, not `error.message`. Fix the error display:

```typescript
const mutation = useMutation({
  mutationFn: createTenant,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
    onOpenChange(false);
    setTenantId("");
    setName("");
    setEmail("");
  },
  onError: (error: any) => {
    // Log for debugging
    console.error("Create tenant error:", error.response?.data);
  },
});

// Update error display section at bottom of form:
{mutation.isError && (
  <p className="text-sm text-destructive">
    {(mutation.error as any)?.response?.data?.detail ||
     (mutation.error as Error).message ||
     "Failed to create tenant"}
  </p>
)}
```

## Fix 2: Better UX for Tenant ID Field

Add auto-slug generation and clearer labeling:

```typescript
// Add function to generate slug from name
const generateSlug = (text: string): string => {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .substring(0, 64);
};

// Update state handling - when name changes, suggest a slug if tenant_id is empty
const handleNameChange = (value: string) => {
  setName(value);
  if (!tenantId || tenantId === generateSlug(name)) {
    setTenantId(generateSlug(value));
  }
};
```

Update the form fields:

```tsx
<div>
  <Label htmlFor="name">Display Name</Label>
  <Input
    id="name"
    value={name}
    onChange={(e) => handleNameChange(e.target.value)}
    placeholder="My Company Inc."
    required
  />
  <p className="text-xs text-muted-foreground mt-1">
    Human-readable name (spaces allowed)
  </p>
</div>

<div>
  <Label htmlFor="tenant_id">Tenant ID (URL Slug)</Label>
  <Input
    id="tenant_id"
    value={tenantId}
    onChange={(e) => setTenantId(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
    placeholder="my-company"
    pattern="[a-z0-9][a-z0-9\-]*[a-z0-9]|[a-z0-9]{1,2}"
    required
  />
  <p className="text-xs text-muted-foreground mt-1">
    Lowercase letters, numbers, hyphens only. Used in URLs.
  </p>
</div>
```

**Note:** Reorder fields so Display Name comes first (user types name, slug auto-generates).

## Fix 3: Relax Backend Validation (Optional)

**File:** `services/ui_iot/routes/operator.py`

If you want to allow 1-2 character tenant IDs:

```python
# Line ~392 - update regex
if not re.match(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$', tenant.tenant_id):
    raise HTTPException(
        400,
        "tenant_id must be lowercase alphanumeric with hyphens, cannot start/end with hyphen",
    )

if len(tenant.tenant_id) > 64:
    raise HTTPException(400, "tenant_id must be 64 characters or less")
```

This allows:
- Single char: `a`, `1`
- Two chars: `ab`, `a1`
- Multiple with hyphens: `my-company`, `test-tenant-1`
- Still rejects: `-bad`, `bad-`, `BAD`, `has space`

## Rebuild and Test

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

Test scenarios:
1. Enter "My New Company" in Display Name - should auto-populate "my-new-company" as Tenant ID
2. Try submitting with invalid tenant_id - error message should show exactly why it failed
3. Create tenant with 2-character ID like "ab" - should work if backend relaxed

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/features/operator/CreateTenantDialog.tsx` |
| MODIFY | `services/ui_iot/routes/operator.py` (optional - backend validation) |
