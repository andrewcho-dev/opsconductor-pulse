# Phase 11: InfluxDB Telemetry Migration — Cursor Execution Instructions

## How to Execute

Run each task file **one at a time, in order**. For each task, paste the following instruction into Cursor:

---

### Task 001 (run first — prerequisite for everything)

```
Read and execute the file docs/cursor-prompts/phase11-influxdb-migration/001-influxdb-infrastructure.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 002 (run after 001)

```
Read and execute the file docs/cursor-prompts/phase11-influxdb-migration/002-tenant-db-provisioning.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Create/modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 003 (run after 002)

```
Read and execute the file docs/cursor-prompts/phase11-influxdb-migration/003-ingest-dual-write.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. This task modifies ingest.py extensively — read the full file first. Modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 004 (run after 003)

```
Read and execute the file docs/cursor-prompts/phase11-influxdb-migration/004-evaluator-migration.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. Pay special attention to return format compatibility — the InfluxDB path must return dicts with the exact same keys as fetch_rollup(). Timestamps must be datetime objects. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 005 (run after 003, can run parallel with 004)

```
Read and execute the file docs/cursor-prompts/phase11-influxdb-migration/005-dashboard-telemetry-migration.md

Follow every instruction exactly. Read all files listed in the "Read first" section before making changes. The influx query functions must return the exact same format as the PG versions. Create/modify only the files listed in "Files to Create/Modify". Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

### Task 006 (run after 003, 004, and 005 are all complete)

```
Read and execute the file docs/cursor-prompts/phase11-influxdb-migration/006-phase11-tests.md

Follow every instruction exactly. Read all files listed in the "Read first" section before writing tests. Create only the files listed in "Files to Create/Modify". Unit tests must not require any infrastructure. Integration tests require InfluxDB running on localhost:8181. Run all commands in the "Test" section and verify every acceptance criterion. Do not commit until all tests pass. Use the commit message provided in the "Commit" section.
```

---

## Execution Order

```
001 ──→ 002 ──→ 003 ──→ 004 ──→ 006
                     └──→ 005 ─┘
```

Tasks 004 and 005 can run in any order after 003 completes.
Task 006 requires all of 003, 004, and 005.
