
CREATE DATABASE IF NOT EXISTS heat_stress_db;
USE heat_stress_db;

CREATE TABLE IF NOT EXISTS Equipment (
    Equipment_ID INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique equipment identifier',
    Name VARCHAR(100) NOT NULL COMMENT 'Equipment name or label',
    Max_Temp_Threshold FLOAT NOT NULL COMMENT 'Maximum safe temperature threshold in Celsius',
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    INDEX idx_name (Name) COMMENT 'Index for equipment name searches'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Equipment registry for heat stress monitoring';

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

ALTER TABLE Telemetry ADD INDEX idx_equipment_timestamp (Equipment_ID, Timestamp DESC);
ALTER TABLE Equipment ADD UNIQUE INDEX uidx_name (Name);

USE heat_stress_db;

ALTER TABLE Equipment 
ADD COLUMN Location VARCHAR(100) AFTER Max_Temp_Threshold,
ADD COLUMN Overheat_Count INT DEFAULT 0 AFTER Location;

ALTER TABLE Equipment ADD INDEX idx_location (Location);

UPDATE Equipment 
SET Location = 'Not Specified' 
WHERE Location IS NULL;

SELECT Equipment_ID, Name, Location, Overheat_Count FROM Equipment;

-- Fix for Flask access:
CREATE USER 'heatstress_user'@'localhost' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON heat_stress_db.* TO 'heatstress_user'@'localhost';
FLUSH PRIVILEGES;
