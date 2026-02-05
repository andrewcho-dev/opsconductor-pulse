# Phase 12: InfluxDB Cutover — Cursor Execution Instructions

## Prerequisites

Phase 11 must be fully complete before starting Phase 12.

## How to Execute

Run each task file **one at a time, in order**. For each task, paste the following instruction into Cursor:

---

### Task 007 (run first — requires Phase 11 complete)

```
Read and execute the file docs/cursor-prompts/phase12-influxdb-cutover/007-remove-pg-dual-write.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. This task removes feature flags and PG fallback paths across multiple files. Be thorough — check all import statements after removing functions. Modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 008 (run after 007)

```
Read and execute the file docs/cursor-prompts/phase12-influxdb-cutover/008-drop-raw-events.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Create the migration SQL file and modify ingest.py to remove all raw_events code. After changes, run the grep command to verify no remaining raw_events references in Python code. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 009 (run after 008)

```
Read and execute the file docs/cursor-prompts/phase12-influxdb-cutover/009-documentation.md

Follow every instruction exactly. Read docs/cursor-prompts/README.md and add the Phase 12 section following the existing format. Do not commit until all acceptance criteria are met. Use the commit message provided in the "Commit" section.
```

---

### Task 010 (run last — validates everything)

```
Read and execute the file docs/cursor-prompts/phase12-influxdb-cutover/010-full-validation.md

This is the final validation task. Run every step. Do not skip any. Report the exact results for each of the 14 checks. If anything fails, go back to the relevant task and fix it before marking this complete. Update docs/cursor-prompts/README.md to mark all Phase 11 and 12 tasks as [x] and set status to COMPLETE. Use the commit message provided in the "Commit" section.
```

---

## Execution Order

```
007 ──→ 008 ──→ 009 ──→ 010
```

All tasks must run sequentially — each depends on the previous.
