# Phase 152 — Sensor-Aware Fleet Views

## Overview

With sensors as first-class entities (Phase 149-151), fleet views and dashboard widgets need to become sensor-aware. Users should be able to:

- Target sensors (not just devices) in chart widgets
- View fleet-level sensor statistics
- Create alert rules targeting specific sensors
- See sensor counts in fleet overview

## Execution Order

1. `001-widget-sensor-targeting.md` — Dashboard widget config targets sensors instead of devices
2. `002-fleet-overview-sensors.md` — Fleet overview widget shows sensor counts
3. `003-alert-rules-sensor-support.md` — Alert rules can target specific sensors
4. `004-telemetry-chart-sensor-select.md` — Telemetry charts select by sensor, show sensor label/unit
