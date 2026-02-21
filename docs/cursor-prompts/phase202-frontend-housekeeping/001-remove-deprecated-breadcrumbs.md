# Task 1: Remove Deprecated `breadcrumbs` Prop from PageHeader

## Context

`frontend/src/components/shared/PageHeader.tsx:12-13` has a `breadcrumbs?: BreadcrumbItem[]` prop that was deprecated in Phase 175 when breadcrumbs moved to `AppHeader`. The prop is still in the TypeScript interface but is ignored at runtime. Removing it eliminates dead code and prevents future developers from passing data to it expecting it to work.

## Actions

1. Read `frontend/src/components/shared/PageHeader.tsx` in full.

2. Remove the `breadcrumbs` prop from the `PageHeaderProps` interface and from the component's destructured parameters.

3. Remove the `BreadcrumbItem` type import if it is only used by this prop (check for other usages first).

4. Search for all usages of `<PageHeader` across the frontend:
   ```bash
   grep -rn '<PageHeader' frontend/src/ --include="*.tsx"
   ```

5. For each call site, remove the `breadcrumbs={...}` prop if it is being passed. The call sites are passing data to a prop that is already ignored — removing them is safe.

6. Do not change any other PageHeader functionality.

## Verification

```bash
grep -n 'breadcrumbs' frontend/src/components/shared/PageHeader.tsx
# Must return zero results

# No call sites still passing breadcrumbs
grep -rn 'breadcrumbs=' frontend/src/ --include="*.tsx"
# Must return zero results
```
