-- Add severities array column to match code expectations
ALTER TABLE integration_routes
ADD COLUMN IF NOT EXISTS severities TEXT[] DEFAULT '{}';

-- Migrate data from min_severity to severities
UPDATE integration_routes
SET severities = CASE
    WHEN min_severity = 1 THEN ARRAY['critical', 'high', 'medium', 'low', 'info']
    WHEN min_severity = 2 THEN ARRAY['critical', 'high', 'medium', 'low']
    WHEN min_severity = 3 THEN ARRAY['critical', 'high', 'medium']
    WHEN min_severity = 4 THEN ARRAY['critical', 'high']
    WHEN min_severity = 5 THEN ARRAY['critical']
    ELSE ARRAY['critical', 'high', 'medium', 'low', 'info']
END
WHERE severities = '{}' OR severities IS NULL;
