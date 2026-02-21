-- Migration: 119_stripe_webhook_idempotency.sql
-- Purpose: Durable idempotency store for Stripe webhook events.

CREATE TABLE IF NOT EXISTS stripe_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    payload_summary JSONB
);

CREATE INDEX IF NOT EXISTS idx_stripe_events_type_received
    ON stripe_events (event_type, received_at DESC);
