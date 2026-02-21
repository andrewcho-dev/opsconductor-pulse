---
phase: 208
title: Unit Test DB Stub Improvements
goal: Fix 192 failing unit tests caused by the fake DB pool returning None/[] for all queries
---

# Phase 208 — Unit Test DB Stub Improvements

## Problem

When no live DB is available, `tests/conftest.py` falls back to a `_FakePool` whose
`mock_conn.fetchrow` returns `None` and `mock_conn.fetch` returns `[]`. Route handlers
that query the DB and get `None` back raise 404 (resource not found) or similar errors,
causing 192 test failures.

## Root Cause

The `mock_conn` created inside the `db_pool` fixture exception handler is not configurable
and not accessible by individual tests. Tests have no way to tell the fake connection what
to return for their specific scenario.

## Approach

1. Refactor `_FakePool` / `mock_conn` into a proper reusable structure
2. Expose `mock_conn` as a first-class test fixture
3. Create `tests/factories.py` with fake record builders matching DB column shapes
4. Update the most common failing test files to configure mock responses properly
5. Verify improvement with a test run

## Execution Order

- 001-refactor-fake-pool.md
- 002-create-factories.md
- 003-fix-billing-tests.md
- 004-fix-remaining-tests.md
- 005-update-documentation.md
