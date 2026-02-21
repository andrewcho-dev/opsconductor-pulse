# Task 2: Update Documentation

## Files to Update

1. `docs/development/frontend.md`
2. `docs/services/ui-iot.md`
3. `docs/features/device-management.md`
4. `docs/index.md`

---

## All Files

### Frontmatter (all four)

- Set `last-verified: 2026-02-20`
- Add `192` to the `phases` array

### Content Changes

**`docs/features/device-management.md`** — Update the Overview tab description. Replace the current Overview bullet:

```markdown
- **Overview** — Device properties in a 3-column card grid (Identity | Hardware | Network+Location), tags and notes side-by-side, device health diagnostics (signal, battery, CPU, memory, uptime with signal chart), latest telemetry in a 4-column metric grid, uptime availability bar, and map (GPS only).
```

With:

```markdown
- **Overview** — Device properties in a 3-column card grid (Identity | Hardware | Network+Location), tags and notes side-by-side, a compact 5-metric health strip (signal, battery, CPU temp, memory, uptime — latest values only, no charts), and map (GPS only). Telemetry data and charts are on the Data tab, not the Overview.
```

Also update the section header to include Phase 192:

```markdown
## Device Detail UI (Phases 171, 187, 188, 189, 192)
```

**Other files** — No content changes, frontmatter only.

## Verification

- All four docs have `192` in their `phases` array
- `last-verified` dates updated
- Overview tab description no longer mentions signal chart, latest telemetry grid, or uptime bar
