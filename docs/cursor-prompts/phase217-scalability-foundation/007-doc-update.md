# Task 7: Update Documentation

## Files to Update

- `docs/architecture/system-map.md` (if it exists) — add Valkey to service map
- `docs/services/evaluator.md` (if it exists) — update with sharding, cooldown,
  timer-based evaluation, Valkey dependency
- `docs/development/frontend.md` — no changes needed (frontend not modified)
- Create `docs/operations/evaluator-scaling.md` if no evaluator operations doc
  exists

## For Each File

### 1. Read the current content of each file

### 2. Update relevant sections

For any evaluator service documentation, add or update:

**New env vars introduced in Phase 217:**
| Variable | Default | Purpose |
|---|---|---|
| `VALKEY_URL` | `redis://localhost:6379` | Valkey connection string |
| `RULE_COOLDOWN_SECONDS` | `300` | Seconds before a fired rule can fire again per device |
| `TENANT_BUDGET_MS` | `500` | Max wall-clock ms per tenant per evaluation cycle |
| `EVALUATION_INTERVAL_SECONDS` | `60` | How often the evaluation loop runs |
| `MIN_EVAL_INTERVAL_SECONDS` | `10` | Minimum gap between consecutive evaluations |
| `EVALUATOR_SHARD_INDEX` | `0` | This instance's shard partition (0-based) |
| `EVALUATOR_SHARD_COUNT` | `1` | Total number of evaluator shards |

**Architecture changes:**
- Valkey is now a required dependency of the evaluator service
- Window buffer state (`wbuf:*`) and cooldown state (`cooldown:*`) stored in Valkey
- Evaluation loop is timer-driven (60s interval) not NOTIFY-driven
- NOTIFY events still received and used to populate `_pending_tenants` for
  future prioritisation
- Tenant evaluation wrapped in per-tenant exception isolation — one tenant
  failure does not abort the cycle for other tenants
- `fetch_rollup_timescaledb()` lookback reduced from 6 hours to 10 minutes
- Shard filter added to `fetch_rollup_timescaledb()` via `hashtext(tenant_id) % SHARD_COUNT`

**Running multiple evaluator shards:**
To run 2 shards, set `EVALUATOR_SHARD_COUNT=2` on both instances and
`EVALUATOR_SHARD_INDEX=0` on one and `EVALUATOR_SHARD_INDEX=1` on the other.
Both instances must share the same Valkey instance. No DB schema changes required.

### 3. Update YAML frontmatter

For every doc file touched:
```yaml
last-verified: 2026-02-22
phases: [..., 217]
```

Add `sources` if not present:
```yaml
sources:
  - services/evaluator_iot/evaluator.py
  - compose/docker-compose.yml
```

### 4. Verify no stale information remains

Check for any references to:
- "POLL_SECONDS as primary trigger" — update to note it is no longer primary
- "in-memory window buffers" — update to Valkey-backed
- "single evaluator instance" — update to note sharding is now supported
