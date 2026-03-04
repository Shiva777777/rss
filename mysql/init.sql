-- ══════════════════════════════════════════════════════
--  RSS Attendance System – Host MySQL Setup Script
--  Run this in your MySQL Workbench / CLI as root
--  mysql -u root -p  →  then paste below
-- ══════════════════════════════════════════════════════

-- 1. Use the existing database
USE rss_db;

-- 2. Allow root to connect from Docker container's IP range
--    (host.docker.internal sends requests from 172.17.x.x)
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'Om7771913285';
GRANT ALL PRIVILEGES ON rss_db.* TO 'root'@'%';
FLUSH PRIVILEGES;

-- 3. Verify
SELECT User, Host FROM mysql.user WHERE User = 'root';
