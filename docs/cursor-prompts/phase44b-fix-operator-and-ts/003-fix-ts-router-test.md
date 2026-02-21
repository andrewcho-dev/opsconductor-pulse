# Prompt 003 — Fix TypeScript Error in `router.test.tsx`

## Context

`npm run build` fails due to a pre-existing TypeScript error in `frontend/src/app/router.test.tsx`. This file is a test file — it should not block the production build.

## Your Task

### Step 1: Read the exact error

```bash
cd frontend && npm run build 2>&1 | grep -A5 "router.test"
```

Report the exact error message and line number.

### Step 2: Read `frontend/src/app/router.test.tsx`

Understand what the test is doing and what the TS error is.

### Step 3: Fix the error

Common causes and fixes:

**A) Test file is included in the build (tsconfig.json includes test files)**
- Check `frontend/tsconfig.json` — if it does not exclude `**/*.test.{ts,tsx}`, add the exclusion:
  ```json
  {
    "exclude": ["**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx"]
  }
  ```
  This is the most common cause — test files should never be compiled as part of the production build.

**B) The test file itself has a genuine TS error**
- Fix the specific type error in the test file (wrong mock type, missing import, etc.)
- Do NOT change production code — only the test file

**C) A type imported by the test no longer exists**
- Update the import to the current location/name of the type

Apply whichever fix matches the actual error. Prefer option A if the tsconfig simply doesn't exclude test files — that is the correct architectural fix.

### Step 4: Verify

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: clean build, no errors.

Also confirm tests still run:

```bash
cd frontend && npm run test -- --run 2>&1 | tail -5
```

## Acceptance Criteria

- [ ] `npm run build` completes with no TypeScript errors
- [ ] `npm run test -- --run` still passes
- [ ] The fix is minimal — only change what is needed to clear the TS error
