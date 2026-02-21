# Task 4: Consolidate Duplicated Auth Utilities

## Context

`frontend/src/services/api/client.ts` and `frontend/src/services/api/deadLetter.ts` both define `getCsrfToken()` and `getAuthHeaders()`. Two implementations of the same function means bugs in one aren't automatically fixed in the other.

## Actions

1. Read `frontend/src/services/api/client.ts` and `frontend/src/services/api/deadLetter.ts` in full.

2. In `client.ts`, ensure these functions are exported:
   ```typescript
   export function getCsrfToken(): string | null { ... }
   export function getAuthHeaders(): Record<string, string> { ... }
   ```
   (If `storeCsrfToken` was added in phase 194 Task 4, make sure it is exported from here too.)

3. In `deadLetter.ts`, remove the local definitions of `getCsrfToken()` and `getAuthHeaders()`. Replace them with imports from `client.ts`:
   ```typescript
   import { getCsrfToken, getAuthHeaders } from "./client";
   ```

4. Search for any other files in `frontend/src/services/api/` that define their own versions of these functions. Apply the same consolidation — import from `client.ts`, do not redefine.

5. Do not change any logic — only the source of the functions.

## Verification

```bash
# getCsrfToken defined only once
grep -rn 'function getCsrfToken\|const getCsrfToken\|getCsrfToken = ' frontend/src/services/
# Must appear exactly once (in client.ts)

# All other files import it
grep -rn 'getCsrfToken' frontend/src/services/api/deadLetter.ts
# Must show an import, not a definition
```
