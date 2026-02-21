# Phase 105 — Fleet Search

## Goal

Operators currently have no way to search or filter across hundreds or thousands
of devices. Add server-side search to the device list endpoint and a search/filter
bar to the Fleet UI.

## Design

- Backend: `GET /customer/devices` gains `search`, `status`, `site_id`, `tag`
  query parameters. Filtering is done in SQL (ILIKE + indexed columns).
- DB: GIN index on `device_state.tags` for fast tag filtering. `tsvector` index
  on `name` + `device_id` for full-text search.
- Frontend: search bar + status/site/tag filter chips above the device table.

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-migration.md` | Migration 075: search indexes on device_state |
| `002-api.md` | Update GET /customer/devices with filter params |
| `003-frontend.md` | Search bar + filter chips in Fleet page |
| `004-verify.md` | Verify search returns correct results, commit |
