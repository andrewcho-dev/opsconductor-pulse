# Phase 100 — Test Coverage: Protect the Critical Paths

## Problem

Current coverage threshold is 45%. The highest-risk paths have no dedicated safety net:
1. **Evaluator** — a regression silently stops alert generation
2. **Ingest** — a regression silently drops device telemetry
3. **Tenant isolation** — a regression silently exposes cross-tenant data

These are not glamorous tests. They are insurance against breaking core functionality
during future refactors.

## Goal

Add targeted unit tests for the three highest-risk paths.
Raise the coverage threshold from 45% to 65%.

## Scope — what to test

### 1. Evaluator unit tests (`tests/unit/test_evaluator.py`)
- Threshold rule fires when metric exceeds threshold
- Threshold rule does NOT fire when metric is below threshold
- NO_HEARTBEAT alert generated when last_heartbeat exceeds timeout
- Alert deduplication: second evaluation of same condition does not create duplicate alert
- Alert closes when metric returns to normal

### 2. Ingest unit tests (`tests/unit/test_ingest_core.py`)
- Valid telemetry envelope passes validation
- Missing required fields (tenant_id, device_id, ts) rejected to quarantine
- Provision token validation: correct token passes, wrong token rejected
- Metric normalization: multiplier and offset applied correctly
- Batch writer flushes at correct interval

### 3. Tenant isolation unit tests (`tests/unit/test_tenant_isolation.py`)
- `tenant_connection()` sets app.tenant_id correctly
- `operator_connection()` uses pulse_operator role
- Ingest path extracts tenant_id from topic correctly
- Ingest rejects message if device belongs to different tenant than topic claims

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-evaluator-tests.md` | Unit tests for evaluator threshold + heartbeat logic |
| `002-ingest-tests.md` | Unit tests for ingest validation + normalization |
| `003-isolation-tests.md` | Unit tests for tenant context and RLS setup |
| `004-raise-threshold.md` | Raise coverage threshold from 45% to 65% in .coveragerc + CI |
| `005-verify.md` | Run full test suite and confirm all pass |
