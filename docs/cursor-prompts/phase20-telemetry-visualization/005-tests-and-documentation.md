# Task 005: Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 20 Tasks 1-4 added: chart libraries (ECharts + uPlot), chart wrapper components, device telemetry hook, and the full device detail page. This task verifies everything builds, existing backend tests pass, and adds Phase 20 to the documentation.

**Read first**:
- `docs/cursor-prompts/README.md` — Phase 19 section exists, need to add Phase 20
- `frontend/src/lib/charts/` — verify all chart files exist
- `frontend/src/features/devices/` — verify all device page files exist
- `frontend/src/hooks/` — verify telemetry hooks exist

---

## Task

### 5.1 Verify all Phase 20 files exist

Run these checks. If any file is missing, the corresponding task was not completed — go back and complete it.

```bash
# Chart library config (Task 1)
ls frontend/src/lib/charts/colors.ts
ls frontend/src/lib/charts/metric-config.ts
ls frontend/src/lib/charts/transforms.ts
ls frontend/src/lib/charts/theme.ts
ls frontend/src/lib/charts/index.ts

# Chart components (Task 2)
ls frontend/src/lib/charts/EChartWrapper.tsx
ls frontend/src/lib/charts/UPlotChart.tsx
ls frontend/src/lib/charts/MetricGauge.tsx
ls frontend/src/lib/charts/TimeSeriesChart.tsx

# Device telemetry hooks (Task 3)
ls frontend/src/hooks/use-device-telemetry.ts
ls frontend/src/hooks/use-device-alerts.ts

# Device detail page components (Task 4)
ls frontend/src/features/devices/DeviceInfoCard.tsx
ls frontend/src/features/devices/MetricGaugesSection.tsx
ls frontend/src/features/devices/TelemetryChartsSection.tsx
ls frontend/src/features/devices/DeviceAlertsSection.tsx
ls frontend/src/features/devices/DeviceDetailPage.tsx

# Tabs UI component (Task 1)
ls frontend/src/components/ui/tabs.tsx
```

### 5.2 Update Phase 20 documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 20 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 19. The Phase 19 section should already exist — add Phase 20 right after it.

```markdown
## Phase 20: Telemetry Visualization — ECharts + uPlot

**Goal**: Interactive device telemetry charts with ECharts gauges and uPlot time-series, fused REST + WebSocket data.

**Directory**: `phase20-telemetry-visualization/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-chart-libraries.md` | ECharts + uPlot install, dark theme, metric config, transforms | `[x]` | None |
| 2 | `002-chart-components.md` | EChart wrapper, uPlot wrapper, gauge, time-series | `[x]` | #1 |
| 3 | `003-device-telemetry-hook.md` | useDeviceTelemetry with REST + WS fusion | `[x]` | #1 |
| 4 | `004-device-detail-page.md` | Full device detail page with charts | `[x]` | #1, #2, #3 |
| 5 | `005-tests-and-documentation.md` | Verification and documentation | `[x]` | #1-#4 |

**Exit Criteria**:
- [x] ECharts and uPlot installed as dependencies
- [x] ECharts dark theme matching Tailwind dark theme
- [x] Known metric configs (battery, temp, RSSI, SNR) with gauge zones
- [x] Auto-discovery of dynamic/custom metrics from data
- [x] MetricGauge component (ECharts gauge per metric)
- [x] TimeSeriesChart component (uPlot per metric)
- [x] useDeviceTelemetry hook fuses REST initial + WS live data
- [x] Device subscribes/unsubscribes to WS telemetry on mount/unmount
- [x] Rolling buffer (500 points max) with deduplication
- [x] Time range selector (1h, 6h, 24h, 7d) with REST refetch
- [x] LIVE badge when WebSocket telemetry streaming
- [x] Device info card with status, site, timestamps
- [x] Device-specific alerts section
- [x] ErrorBoundary isolation on all sections
- [x] npm run build succeeds
- [x] All backend tests pass

**Architecture decisions**:
- **ECharts for gauges**: Rich gauge component with color zones, animation, formatted values. Used for current metric display (<10 data points per gauge).
- **uPlot for time-series**: Ultra-fast rendering for 120-1000 historical data points. Column-major data format. Dark theme via JS options (not CSS).
- **REST + WS fusion**: Initial data from REST API (up to 500 points), live updates from WebSocket merged into rolling buffer. Deduplication by timestamp.
- **Metric auto-discovery**: `discoverMetrics()` extracts available metric names from data. Known metrics sorted first (battery, temp, RSSI, SNR), then alphabetical.
- **Warm path updates**: WebSocket telemetry flows through React state (useState in hook). Sufficient for 1Hz per-device updates. Hot path (direct chart ref updates) reserved for Phase 21 if needed.
- **Chart lifecycle**: ResizeObserver for responsive sizing. Proper dispose/destroy on unmount. React.memo on all chart components.
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 20 section |

---

## Test

### Step 1: Verify frontend build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Run ALL backend unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

ALL tests must pass. No regressions from Phase 20 (Phase 20 makes no backend changes).

### Step 4: Verify frontend file count

```bash
find /home/opsconductor/simcloud/frontend/src -name "*.ts" -o -name "*.tsx" | wc -l
```

Should be higher than Phase 19 count (Phase 19 had 68 files, Phase 20 adds ~14 more files).

### Step 5: Verify chart packages in bundle

```bash
cd /home/opsconductor/simcloud/frontend && npm ls echarts uplot
```

Both should appear as installed dependencies.

---

## Acceptance Criteria

- [ ] All Phase 20 files exist (chart libs, components, hooks, device page)
- [ ] `npm run build` succeeds
- [ ] `npx tsc --noEmit` succeeds
- [ ] All backend tests pass (395 tests)
- [ ] Phase 20 section added to cursor-prompts/README.md
- [ ] No regressions from Phase 20

---

## Commit

```
Update documentation for Phase 20 completion

Add Phase 20 section to cursor-prompts README. Verify all
chart libraries, components, hooks, and device detail page
are in place.

Phase 20 Task 5: Tests and Documentation
```
