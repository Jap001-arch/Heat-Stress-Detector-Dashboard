-- =====================================================
-- HEAT STRESS DETECTOR - MySQL Database Schema
-- Database Name: heat_stress_db
-- =====================================================

-- Create Database
CREATE DATABASE IF NOT EXISTS heat_stress_db;
USE heat_stress_db;

-- =====================================================
-- EQUIPMENT TABLE
-- =====================================================
-- Stores information about monitored equipment
-- Columns:
--   Equipment_ID: Primary Key, Auto-increment identifier
--   Name: Equipment name/label
--   Max_Temp_Threshold: Maximum acceptable temperature in °C

CREATE TABLE IF NOT EXISTS Equipment (
    Equipment_ID INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique equipment identifier',
    Name VARCHAR(100) NOT NULL COMMENT 'Equipment name or label',
    Max_Temp_Threshold FLOAT NOT NULL COMMENT 'Maximum safe temperature threshold in Celsius',
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    INDEX idx_name (Name) COMMENT 'Index for equipment name searches'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Equipment registry for heat stress monitoring';

-- =====================================================
-- TELEMETRY TABLE
-- =====================================================
-- Stores temperature readings from equipment
-- Columns:
--   Log_ID: Primary Key, Auto-increment log identifier
--   Equipment_ID: Foreign Key to Equipment table
--   Current_Temp: Current temperature reading in °C
--   Timestamp: When the reading was recorded (auto-set to current time)

CREATE TABLE IF NOT EXISTS Telemetry (
    Log_ID INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique telemetry log identifier',
    Equipment_ID INT NOT NULL COMMENT 'Reference to Equipment table',
    Current_Temp FLOAT NOT NULL COMMENT 'Current temperature reading in Celsius',
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Reading timestamp',
    
    CONSTRAINT fk_equipment_telemetry 
        FOREIGN KEY (Equipment_ID) 
        REFERENCES Equipment(Equipment_ID) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    INDEX idx_equipment_id (Equipment_ID) COMMENT 'Index for equipment queries',
    INDEX idx_timestamp (Timestamp) COMMENT 'Index for time-range queries'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Temperature telemetry readings from equipment sensors';

-- =====================================================
-- SAMPLE DATA (Optional)
-- =====================================================
-- Uncomment to insert sample equipment for testing

/*
INSERT INTO Equipment (Name, Max_Temp_Threshold) VALUES
('Industrial Motor A', 85.0),
('Industrial Motor B', 90.0),
('Compressor Unit 1', 75.0),
('Hydraulic Press', 95.0),
('Cooling System', 45.0);

INSERT INTO Telemetry (Equipment_ID, Current_Temp) VALUES
(1, 82.5),
(2, 88.3),
(3, 73.2),
(4, 92.1),
(5, 42.8);
*/

-- =====================================================
-- VIEWS AND UTILITIES
-- =====================================================

-- View: Latest Temperature Reading per Equipment
CREATE OR REPLACE VIEW latest_readings AS
SELECT 
    e.Equipment_ID,
    e.Name,
    e.Max_Temp_Threshold,
    t.Current_Temp,
    t.Timestamp,
    CASE 
        WHEN t.Current_Temp > e.Max_Temp_Threshold THEN 'ALERT'
        WHEN t.Current_Temp > (e.Max_Temp_Threshold * 0.9) THEN 'WARNING'
        ELSE 'NORMAL'
    END as Status
FROM Equipment e
LEFT JOIN Telemetry t ON e.Equipment_ID = t.Equipment_ID
WHERE (e.Equipment_ID, t.Timestamp) IN (
    SELECT Equipment_ID, MAX(Timestamp)
    FROM Telemetry
    GROUP BY Equipment_ID
)
OR t.Timestamp IS NULL;

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Create additional indexes for common queries
ALTER TABLE Telemetry ADD INDEX idx_equipment_timestamp (Equipment_ID, Timestamp DESC);
ALTER TABLE Equipment ADD UNIQUE INDEX uidx_name (Name);

-- =====================================================
-- COMMENTS AND DOCUMENTATION
-- =====================================================

/*
DATABASE DESCRIPTION:
This schema supports a real-time heat stress monitoring system for industrial equipment.

EQUIPMENT TABLE:
- Stores metadata about monitored devices
- Each equipment has a maximum safe operating temperature
- Automatically tracks when each equipment record was created

TELEMETRY TABLE:
- Records temperature readings with timestamps
- Cascade delete ensures orphaned records are cleaned up
- Timestamp defaults to current time for automatic tracking
- Foreign key constraint maintains referential integrity

KEY FEATURES:
1. Auto-increment primary keys for unique identification
2. Foreign key constraints for data integrity
3. Automatic timestamps for audit trails
4. Composite indexes for efficient querying
5. Unicode support for international equipment names
6. Views for pre-calculated status information

MAINTENANCE:
- Run periodic cleanup: DELETE FROM Telemetry WHERE Timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
- Monitor table sizes and optimize as needed
- Consider partitioning Telemetry table if it grows very large

EXAMPLE QUERIES:
-- Get all equipment with alert status
SELECT * FROM latest_readings WHERE Status = 'ALERT';

-- Get average temperature for an equipment in the last hour
SELECT Equipment_ID, AVG(Current_Temp) as avg_temp 
FROM Telemetry 
WHERE Equipment_ID = 1 
AND Timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY Equipment_ID;

-- Get equipment that has exceeded threshold
SELECT e.Name, MAX(t.Current_Temp) as max_temp, e.Max_Temp_Threshold
FROM Equipment e
JOIN Telemetry t ON e.Equipment_ID = t.Equipment_ID
WHERE t.Timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY e.Equipment_ID
HAVING max_temp > e.Max_Temp_Threshold;
*/
