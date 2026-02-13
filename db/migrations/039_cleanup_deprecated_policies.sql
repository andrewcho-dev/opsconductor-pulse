-- Drop RLS policies that reference renamed raw_events table
DROP POLICY IF EXISTS raw_events_read ON raw_events;
DROP POLICY IF EXISTS raw_events_write ON raw_events;

-- If _deprecated_raw_events exists, ensure it has no active policies
DROP POLICY IF EXISTS raw_events_read ON _deprecated_raw_events;
DROP POLICY IF EXISTS raw_events_write ON _deprecated_raw_events;

-- Drop the deprecated table if it's empty and not needed
-- (Uncomment after verifying no dependencies)
-- DROP TABLE IF EXISTS _deprecated_raw_events;
