# Task 4: Fix localStorage Boolean Serialization

## Context

`frontend/src/components/layout/AppSidebar.tsx:83-87` reads sidebar state from localStorage using string comparison:
```typescript
return stored !== "false";
```

This is fragile: `"false "` (trailing space), `"FALSE"`, or `"0"` would all be treated as `true`. The correct approach is to use `JSON.parse`/`JSON.stringify` for boolean storage.

## Actions

1. Read `frontend/src/components/layout/AppSidebar.tsx` in full.

2. Find `readSidebarOpen()` and the corresponding `writeSidebarOpen()` (or wherever `localStorage.setItem` is called for sidebar state).

3. Fix the read function:
   ```typescript
   function readSidebarOpen(key: string, defaultValue: boolean): boolean {
     const stored = localStorage.getItem(key);
     if (stored === null) return defaultValue;
     try {
       return JSON.parse(stored) === true;
     } catch {
       return defaultValue;
     }
   }
   ```

4. Fix the write function (wherever `localStorage.setItem` is called for this value):
   ```typescript
   localStorage.setItem(key, JSON.stringify(value));  // Stores "true" or "false"
   ```

5. Search for other `localStorage.getItem` usages in the sidebar file and in the codebase. Apply the same JSON parse pattern wherever a non-string value is stored.

6. Do not change any sidebar layout logic.

## Verification

```bash
grep -n "!== \"false\"\|=== \"false\"\|=== \"true\"" frontend/src/components/layout/AppSidebar.tsx
# Must return zero results — all boolean localStorage reads use JSON.parse
```
