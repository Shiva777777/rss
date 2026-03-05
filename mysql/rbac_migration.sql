-- RBAC migration for RSS Attendance System
-- Run this after taking a DB backup.

USE rss_db;

-- Expand users.role enum for RBAC.
ALTER TABLE users
MODIFY COLUMN role ENUM('super_admin', 'admin', 'moderator', 'user') NOT NULL DEFAULT 'user';

-- Optional: promote seeded bootstrap account to Super Admin.
UPDATE users
SET role = 'super_admin'
WHERE email = 'admin@rss.com' AND role = 'admin';
