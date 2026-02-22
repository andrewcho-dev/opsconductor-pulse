-- Add shard_index to tenants to support evaluator sharding.
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS shard_index INT NOT NULL DEFAULT 0;
