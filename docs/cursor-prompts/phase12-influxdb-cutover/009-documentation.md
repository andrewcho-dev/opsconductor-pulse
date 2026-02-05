# Task 009: Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task updates the phase tracker README with Phase 12 status.
> Do not create new documentation files — only update the existing README.

---

## Context

Phase 12 tasks (007-008) are complete. Update the project documentation to reflect the completed migration.

**Read first**:
- `docs/cursor-prompts/README.md` (full file — see how phases 1-11 are documented)

---

## Task

### 9.1 Add Phase 12 section to README.md

In `docs/cursor-prompts/README.md`, add Phase 12 section after the Phase 11 section (which was added in Task 006). Place it before the "How to Use These Prompts" section.

```markdown

## Phase 12: InfluxDB Cutover

**Goal**: Remove PostgreSQL raw_events dependency, make InfluxDB 3 Core the sole telemetry store.

**Directory**: `phase12-influxdb-cutover/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 7 | `007-remove-pg-dual-write.md` | Remove dual-write, InfluxDB primary | `[x]` | Phase 11 |
| 8 | `008-drop-raw-events.md` | Deprecate raw_events table | `[x]` | #7 |
| 9 | `009-documentation.md` | Update documentation | `[x]` | #7, #8 |
| 10 | `010-full-validation.md` | Full system validation | `[x]` | #7, #8, #9 |

**Exit Criteria**:
- [x] InfluxDB is the sole telemetry write target (PG raw_events opt-in only)
- [x] raw_events table deprecated (renamed to _deprecated_raw_events)
- [x] All Phase 11 feature flags removed
- [x] No Python code references raw_events
- [x] Evaluator reads exclusively from InfluxDB
- [x] UI reads exclusively from InfluxDB
- [x] All services healthy, all tests pass

**Architecture note**: The system now uses a two-database architecture:
- **PostgreSQL**: Transactional data (device_registry, device_state, fleet_alert, integrations, delivery_jobs, quarantine_events)
- **InfluxDB 3 Core**: Time-series telemetry (heartbeat, telemetry measurements per tenant database)

---
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `docs/cursor-prompts/README.md` |

---

## Test

```bash
# Verify README renders correctly
cat docs/cursor-prompts/README.md | head -50
# Should show all phases listed

# Verify Phase 11 and 12 sections exist
grep -c "Phase 11" docs/cursor-prompts/README.md  # Should be >= 1
grep -c "Phase 12" docs/cursor-prompts/README.md  # Should be >= 1
```

---

## Acceptance Criteria

- [ ] `docs/cursor-prompts/README.md` has Phase 12 section
- [ ] Phase 12 section follows the format of phases 1-11
- [ ] All Phase 12 tasks listed as `[x]` (complete)
- [ ] Architecture note documenting two-database design

---

## Commit

```
Update documentation for Phase 12 completion

- Add Phase 12 section to cursor-prompts README
- Document two-database architecture (PostgreSQL + InfluxDB)
- All Phase 11 and 12 tasks marked complete

Part of Phase 12: InfluxDB Cutover
```
