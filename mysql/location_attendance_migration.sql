-- Location-based attendance migration
-- Run after taking a backup.

USE rss_db;

ALTER TABLE attendance
    ADD COLUMN marked_time TIME NOT NULL DEFAULT (CURRENT_TIME) AFTER date,
    ADD COLUMN latitude DECIMAL(10, 7) NULL AFTER ip_address,
    ADD COLUMN longitude DECIMAL(10, 7) NULL AFTER latitude,
    ADD COLUMN city VARCHAR(100) NULL AFTER longitude;

-- Backfill marked_time for old rows if needed
UPDATE attendance
SET marked_time = TIME(marked_at)
WHERE marked_time IS NULL;
