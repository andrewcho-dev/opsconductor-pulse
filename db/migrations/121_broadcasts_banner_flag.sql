ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS is_banner BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS broadcasts_banner_idx ON broadcasts (is_banner, active) WHERE is_banner = true;
