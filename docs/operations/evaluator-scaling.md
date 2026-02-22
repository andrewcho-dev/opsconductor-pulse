---
last-verified: 2026-02-22
sources:
  - services/evaluator_iot/evaluator.py
  - compose/docker-compose.yml
phases: [217]
---

# Evaluator Scaling and Operations

## Summary

- Timer-driven evaluation loop: runs every `EVALUATION_INTERVAL_SECONDS` (default 60s) with a minimum guard `MIN_EVAL_INTERVAL_SECONDS`.
- Per-tenant isolation and budget: each tenant is wrapped in its own try/except with `TENANT_BUDGET_MS` (default 500ms) wall-clock cap.
- Valkey-backed state:
  - Rule cooldowns (`cooldown:*`) to skip recently fired rules.
  - Sliding window buffers (`wbuf:*`) survive restarts; TTL = `window_seconds * 2`.
- Sharding: tenants filtered with `abs(hashtext(tenant_id)) % EVALUATOR_SHARD_COUNT = EVALUATOR_SHARD_INDEX`.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VALKEY_URL` | `redis://localhost:6379` | Valkey connection string |
| `RULE_COOLDOWN_SECONDS` | `300` | Cooldown per (tenant, rule, device) before re-evaluation |
| `TENANT_BUDGET_MS` | `500` | Max wall-clock ms per tenant per cycle |
| `EVALUATION_INTERVAL_SECONDS` | `60` | Timer-based evaluation interval |
| `MIN_EVAL_INTERVAL_SECONDS` | `10` | Minimum spacing between evaluations |
| `EVALUATOR_SHARD_INDEX` | `0` | Shard partition for this instance (0-based) |
| `EVALUATOR_SHARD_COUNT` | `1` | Total evaluator shards |
| `POLL_SECONDS` | `5` | Legacy notify timeout; retained for compatibility |

## Running Multiple Shards

1. Set `EVALUATOR_SHARD_COUNT` to the total number of evaluator instances.
2. Assign `EVALUATOR_SHARD_INDEX` uniquely per instance (0..count-1).
3. Point all shards to the same PostgreSQL/TimescaleDB and Valkey.
4. Example for two shards (compose style):
   - Shard 0: `EVALUATOR_SHARD_INDEX=0`, `EVALUATOR_SHARD_COUNT=2`
   - Shard 1: `EVALUATOR_SHARD_INDEX=1`, `EVALUATOR_SHARD_COUNT=2`

## Valkey Keys

- `cooldown:{tenant_id}:{rule_id}:{device_id}` — rule-level cooldown TTL = `RULE_COOLDOWN_SECONDS`
- `wbuf:{tenant_id}:{rule_id}:{device_id}` — sliding window entries `[ts, value]`, TTL = `window_seconds * 2`

## Operations

- Startup logs to confirm:
  - `valkey_connected`
  - `shard_config shard_index=... shard_count=...`
  - `evaluation_schedule interval_seconds=...`
- Health: `GET /health` and `GET /metrics` on port 8080.
- Restart safety: window buffers and cooldowns persist in Valkey; evaluator restart should not lose sliding-window context.

## Troubleshooting

- Missing Valkey: evaluator continues (cooldowns/windows fail open). Check `valkey_unavailable` log.
- Cycles too fast: increase `EVALUATION_INTERVAL_SECONDS` or `MIN_EVAL_INTERVAL_SECONDS`.
- Cooldowns not applied: ensure `VALKEY_URL` reachable; inspect keys with `valkey-cli keys "cooldown:*"`.
- Sharding imbalance: confirm identical `EVALUATOR_SHARD_COUNT` on all instances and unique `EVALUATOR_SHARD_INDEX`.
