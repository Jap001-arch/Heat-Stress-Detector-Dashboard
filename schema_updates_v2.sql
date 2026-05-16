-- =====================================================
-- HEAT STRESS DETECTOR v2.0 - Database Schema Updates
-- Adds support for all six advanced features
-- =====================================================

USE heat_stress_db;

-- =====================================================
-- Feature 5 + Feature 6: ALTER Equipment TABLE
-- Adds Location field and Overheat_Count tracking
-- =====================================================

ALTER TABLE Equipment 
ADD COLUMN Location VARCHAR(100) AFTER Max_Temp_Threshold,
ADD COLUMN Overheat_Count INT DEFAULT 0 AFTER Location;

-- Create index on Location for search performance (Feature 5)
ALTER TABLE Equipment ADD INDEX idx_location (Location);

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Verify the new columns were added
DESCRIBE Equipment;

-- Expected output:
-- Equipment_ID | int         | NO  | PRI | NULL    | auto_increment
-- Name         | varchar(100)| NO  |     | NULL    |
-- Max_Temp_... | float       | NO  |     | NULL    |
-- Location     | varchar(100)| YES |     | NULL    |
-- Overheat_... | int         | YES |     | 0       |
-- Created_At   | timestamp   | YES |     | ...     |

-- Sample data update to set locations for existing equipment
UPDATE Equipment 
SET Location = 'Not Specified' 
WHERE Location IS NULL;

-- Verify locations were set
SELECT Equipment_ID, Name, Location, Overheat_Count FROM Equipment;

-- =====================================================
-- NOTES ON FEATURES
-- =====================================================

/*
Feature 1: Interactive Historical Trend Graphs
  - Integrated via Chart.js CDN in index_v2.html
  - Backend returns last 20 readings in trend_data object
  - JavaScript creates Chart.js line graph in modal
  - No database changes needed (uses existing Telemetry table)

Feature 2: Predictive "Rapid Heating" Alerts
  - Calculated in app_v2.py detect_rapid_heating() function
  - Checks if temp increased >10°C within 60-second window
  - Returns alert in JSON response
  - No database changes needed

Feature 3: Automated Email Notifications
  - Uses Python smtplib for email delivery
  - Cooldown mechanism prevents spam (one email per 15 minutes)
  - Environment variables for SMTP config
  - No database changes needed

Feature 4: One-Click CSV Data Export
  - New route /api/export in app_v2.py
  - Exports Equipment + latest Telemetry as CSV
  - Browser downloads heat_report.csv automatically
  - No database changes needed

Feature 5: Equipment Location Tags
  - NEW COLUMN: Equipment.Location (VARCHAR 100)
  - Added index on Location for search performance
  - Frontend shows location badge on equipment cards
  - Included in add/edit forms
  - DATABASE CHANGE REQUIRED: Execute ALTER TABLE above

Feature 6: Equipment Health Score
  - Calculated in app_v2.py calculate_health_score() function
  - Formula: Start 100%, -5% per overheat event, -20% if currently hot
  - NEW COLUMN: Equipment.Overheat_Count (INT DEFAULT 0)
  - Returned in equipment API responses
  - Frontend displays with color coding (green/yellow/red)
  - DATABASE CHANGE REQUIRED: Execute ALTER TABLE above

DATABASE CHANGES SUMMARY:
  ✓ ALTER Equipment table (2 new columns)
  ✓ Add index on Location
  ✓ No changes to Telemetry table
  ✓ No changes to column constraints
  ✓ Backward compatible with existing data
*/

-- =====================================================
-- BACKUP RECOMMENDATION
-- =====================================================

-- Before running the ALTER TABLE, backup your database:
-- mysqldump -u root -p heat_stress_db > backup_before_v2.sql

-- After ALTER TABLE succeeds, verify no data loss:
-- SELECT COUNT(*) as total_equipment FROM Equipment;
-- SELECT COUNT(*) as total_telemetry FROM Telemetry;
