CREATE TABLE IF NOT EXISTS broadcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'info' CHECK (type IN ('info', 'warning', 'update')),
    active BOOLEAN NOT NULL DEFAULT true,
    pinned BOOLEAN NOT NULL DEFAULT false,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS broadcasts_active_idx ON broadcasts (active, created_at DESC);
