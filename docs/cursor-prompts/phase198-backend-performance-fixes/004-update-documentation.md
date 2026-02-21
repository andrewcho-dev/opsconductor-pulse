# Task 4: Update Documentation

## Context

Phase 198 made internal performance improvements: statement timeout on evaluator pool, pre-fetched group memberships, and bounded batch writer buffer. No external API changes.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/services/ingest.md` (or equivalent) | Document `max_buffer_size` config option for `TimescaleBatchWriter` and the `ingest_records_dropped_total` Prometheus metric |

## For Each File

1. Read the current content.
2. If an ingest service doc exists, add or update the configuration section to mention `max_buffer_size` and what happens when the buffer is full.
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `198` to the `phases` array
4. If no ingest service doc exists, skip (do not create new files).
