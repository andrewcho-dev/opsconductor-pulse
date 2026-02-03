# Phase 9: Testing Overhaul — Cursor Execution Instructions

## How to Execute

Run each task file **one at a time, in order**. For each task, paste the following instruction into Cursor:

---

### Task 000 (run first — prerequisite for everything)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/000-fix-broken-ui.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 001 (run after 000)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/001-test-infrastructure.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 002 (run after 001)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/002-unit-tests-core.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create". Every test must be a true unit test — no database, no Keycloak, no network calls. Mock all external dependencies. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 003 (run after 001, can run parallel with 002)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/003-unit-tests-delivery.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create". Every test must be a true unit test — no database, no Keycloak, no network calls. Mock all external dependencies. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 004 (run after 001, can run parallel with 002/003)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/004-unit-tests-routes-utils.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create". Every test must be a true unit test — no database, no Keycloak, no network calls. Mock all external dependencies. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 005 (run after 000 and 001)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/005-e2e-navigation-crud.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create/Modify". These are E2E tests — the full Docker Compose stack must be running. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 006 (run after 005)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/006-e2e-visual-regression.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create/Modify". The full Docker Compose stack must be running. On first run, use --update-snapshots to generate baselines. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 007 (run after 001)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/007-performance-baselines.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create". Install pytest-benchmark if not already installed. The full Docker Compose stack must be running for page load tests. Run all commands in the "Test" section and verify every acceptance criterion. Fill in actual baseline numbers in BASELINES.md. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 008 (run after 002-007 are all complete)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/008-ci-enforcement.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Modify only the files listed in "Files to Modify". Validate the YAML syntax of the workflow file. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 009 (run last — validates everything)

```
Read and execute the file docs/cursor-prompts/phase9-testing-overhaul/009-full-validation.md

This is the final validation task. Run every step. Do not skip any. Report the exact test counts and coverage numbers. If anything fails, go back to the relevant task and fix it before marking this complete. Update docs/cursor-prompts/README.md to mark all Phase 9 tasks as [x] and set status to COMPLETE. Use the commit message provided in the "Commit" section.
```

---

## Execution Order

```
000 ──→ 001 ──→ 002 ──→ 005 ──→ 006
              ├──→ 003      │
              ├──→ 004      │
              └──→ 007 ─────┘
                             └──→ 008 ──→ 009
```

Tasks 002, 003, 004, and 007 can run in any order after 001 completes.
Tasks 005 and 006 require 000 to be done (UI fixes).
Task 008 requires all of 002-007.
Task 009 is always last.
