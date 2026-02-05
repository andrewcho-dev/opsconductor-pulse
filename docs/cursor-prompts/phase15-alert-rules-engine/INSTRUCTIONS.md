# Phase 15: Custom Alert Rules Engine

## Overview

Phase 15 lets customers define threshold-based alert rules against any device metric. Rules are evaluated by the existing evaluator service and generate `fleet_alert` entries that flow through the existing dispatcher → delivery pipeline.

## Execution Order

Execute tasks in strict order. Each builds on the previous.

| # | File | Description |
|---|------|-------------|
| 1 | `001-alert-rules-schema.md` | Create alert_rules table in evaluator DDL |
| 2 | `002-alert-rules-crud-api.md` | CRUD API endpoints + database query functions |
| 3 | `003-alert-rules-ui.md` | Customer UI page with modal form and JS CRUD |
| 4 | `004-rule-evaluation-engine.md` | Evaluator loads and evaluates rules per device |
| 5 | `005-tests-and-documentation.md` | Unit tests for evaluation logic, CRUD, and docs |

## How to Execute

For each task, paste into Cursor:

```
Read docs/cursor-prompts/phase15-alert-rules-engine/001-alert-rules-schema.md and execute the task.
```

Commit after each task passes its acceptance criteria. Do not skip ahead.
