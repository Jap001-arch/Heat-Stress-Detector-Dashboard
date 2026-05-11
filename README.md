# Heat Stress Detector Web Dashboard

We developed and implemented a cloud-based IoT telemetry system designed for monitoring, analyzing, and predicting thermal failures in industrial equipment. The system uses a Python (Flask) backend and a MySQL database, with a vanilla JavaScript frontend. It processes continuous temperature streams to dynamically assess equipment health. By applying predictive anomaly detection using the dT/dt method, the dashboard can spot rapid heating events and sends automated email alerts to prevent physical damage. The entire platform runs on a secured Linux virtual machine set up with systemd, ensuring maximum resilience and continuous operation.

---

## Project Structure

```
heat-stress-detector/
├── app.py                      # Flask backend application
├── requirements.txt            # Python dependencies
├── schema.sql                  # MySQL database schema
├── templates/
│   └── index.html             # Main dashboard HTML
└── static/
    ├── style.css              # Professional dark theme CSS
    └── script.js              # Real-time dashboard JavaScript
```

---

## Prerequisites

- **Python 3.8+**
- **MySQL 5.7+ or MariaDB 10.3+**
- **pip** (Python package manager)
- **Git** (optional, for version control)

---

## Installation & Setup

### Step 1: Clone/Download Project Files

```bash
# Create project directory
mkdir heat-stress-detector
cd heat-stress-detector

# Copy all files from the provided source into this directory
```

### Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup MySQL Database

#### Option A: Using MySQL Command Line

```bash
# Login to MySQL
mysql -u root -p

# Run the schema script
source /path/to/schema.sql

# Or manually execute:
CREATE DATABASE IF NOT EXISTS heat_stress_db;
USE heat_stress_db;

CREATE TABLE IF NOT EXISTS Equipment (
    Equipment_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Max_Temp_Threshold FLOAT NOT NULL,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (Name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Telemetry (
    Log_ID INT AUTO_INCREMENT PRIMARY KEY,
    Equipment_ID INT NOT NULL,
    Current_Temp FLOAT NOT NULL,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_equipment_telemetry 
        FOREIGN KEY (Equipment_ID) 
        REFERENCES Equipment(Equipment_ID) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    INDEX idx_equipment_id (Equipment_ID),
    INDEX idx_timestamp (Timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Option B: Using MySQL Workbench

1. Open MySQL Workbench
2. Connect to your MySQL server
3. Go to File → Open SQL Script
4. Select `schema.sql`
5. Click Execute (⚡ icon)

### Step 5: Configure Database Connection

Edit `app.py` and update the `DB_CONFIG` dictionary:

```python
DB_CONFIG = {
    'host': 'localhost',           # Your MySQL host
    'user': 'root',                # Your MySQL username
    'password': 'your_password',   # Your MySQL password
    'database': 'heat_stress_db',  # Database name
    'port': 3306                   # MySQL port (default: 3306)
}
```

---

## Running the Application

### Development Mode

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run Flask development server
python app.py
```

The application will be available at: `http://localhost:5000`

### Production Mode (Recommended)

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or using Waitress
waitress-serve --port=5000 app:app
```

---

## API Endpoints

### Equipment Management

#### Create Equipment (POST)
```bash
curl -X POST http://localhost:5000/api/equipment \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Industrial Motor A",
    "max_temp_threshold": 85.0
  }'
```

#### Get All Equipment (GET)
```bash
curl http://localhost:5000/api/equipment
```

#### Get Equipment Details (GET)
```bash
curl http://localhost:5000/api/equipment/1
```

#### Update Equipment (PUT)
```bash
curl -X PUT http://localhost:5000/api/equipment/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Motor Name",
    "max_temp_threshold": 90.0
  }'
```

#### Delete Equipment (DELETE)
```bash
curl -X DELETE http://localhost:5000/api/equipment/1
```

### Telemetry Management

#### Add Temperature Reading (POST)
```bash
curl -X POST http://localhost:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": 1,
    "current_temp": 82.5
  }'
```

#### Cleanup Old Logs (DELETE)
```bash
curl -X DELETE http://localhost:5000/api/telemetry/cleanup
```

---

## Frontend Features

### Dashboard Interface
- **Live Equipment Tracking**: Real-time temperature monitoring with 3-second poll intervals
- **Visual Status Indicators**: 
  - 🟢 Normal (below 90% of threshold)
  - 🟡 Warning (90-100% of threshold)
  - 🔴 Critical Alert (above threshold)
- **Dark Professional Theme**: Easy on the eyes with cyan accents
- **Responsive Design**: Works on desktop, tablet, and mobile

### Interactive Features
- ➕ Add new equipment
- ⚙️ Edit equipment thresholds
- 📊 View detailed temperature history
- 🔍 Search equipment by name or ID
- 🗑️ Clean up old telemetry logs
- 📱 Responsive notifications

---

## Testing the Application

### Test with Sample Data

```sql
-- Insert sample equipment
INSERT INTO Equipment (Name, Max_Temp_Threshold) VALUES
('Motor A', 85.0),
('Motor B', 90.0),
('Compressor', 75.0);

-- Insert sample readings
INSERT INTO Telemetry (Equipment_ID, Current_Temp) VALUES
(1, 82.5),
(2, 88.3),
(3, 73.2);
```

### Manual Testing Steps

1. Open `http://localhost:5000` in your browser
2. Click "Add Equipment" and create a test device
3. Use the API to add temperature readings:
   ```bash
   curl -X POST http://localhost:5000/api/telemetry \
     -H "Content-Type: application/json" \
     -d '{"equipment_id": 1, "current_temp": 85.5}'
   ```
4. Watch the dashboard update in real-time
5. Test alert triggering by exceeding max temperature

---

## Security Considerations

### Production Deployment

1. **Database Credentials**: Use environment variables
```python
import os
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': 'heat_stress_db',
}
```

2. **HTTPS**: Use SSL/TLS in production
```python
# Use nginx or Apache as reverse proxy
# Or configure with:
# app.run(ssl_context='adhoc')
```

3. **Input Validation**: Already implemented in backend
- Temperature range validation (-273.15°C to 200°C)
- Equipment ID validation
- Equipment name length limits (100 chars)
- Missing field checks

4. **CORS**: Configure for your domain
```python
CORS(app, origins=["https://yourdomain.com"])
```

5. **Rate Limiting**: Add to production
```bash
pip install Flask-Limiter
```

---

## Database Maintenance

### Regular Cleanup

```sql
-- Delete telemetry older than 30 days
DELETE FROM Telemetry 
WHERE Timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Check database size
SELECT 
    table_name,
    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb
FROM information_schema.tables
WHERE table_schema = 'heat_stress_db';
```

### Backup

```bash
# Backup database
mysqldump -u root -p heat_stress_db > backup.sql

# Restore database
mysql -u root -p heat_stress_db < backup.sql
```

---

## Troubleshooting

### Issue: "Connection refused" error

**Solution**: 
- Verify MySQL is running
- Check DB_CONFIG credentials
- Ensure database name is correct

```bash
# Check MySQL status
mysql -u root -p -e "SELECT 1;"
```

### Issue: "No module named 'flask'"

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Table doesn't exist"

**Solution**:
```bash
# Run schema.sql again
mysql -u root -p heat_stress_db < schema.sql
```

### Issue: Port 5000 already in use

**Solution**:
```bash
# Use different port
python app.py # Edit the port in app.py, or:
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

---

## Documentation

### Backend (Flask)
- RESTful API endpoints for CRUD operations
- Automatic error handling with HTTP status codes
- Input validation for all user inputs
- Logging for debugging and monitoring
- Database transactions for data integrity

### Frontend (JavaScript)
- Fetch API for non-blocking requests
- Event-driven architecture
- Modal dialogs for user interactions
- Real-time polling (3-second intervals)
- Responsive grid layout

### Database
- Foreign key constraints for integrity
- Automatic timestamps
- Composite indexes for performance
- Unicode support for international text

---

## 🎓 Learning Resources

- Flask Documentation: https://flask.palletsprojects.com/
- MySQL Documentation: https://dev.mysql.com/doc/
- REST API Design: https://restfulapi.net/
- JavaScript Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API

---

## License

This project is provided as-is for educational purposes.

---

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review the API endpoint documentation
3. Check browser console for JavaScript errors
4. Check Flask console for backend errors

---

## Deployment Checklist

- [ ] Database created and schema loaded
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (requirements.txt)
- [ ] Database credentials configured in app.py
- [ ] MySQL service running
- [ ] Flask app runs without errors: `python app.py`
- [ ] Dashboard loads at http://localhost:5000
- [ ] Can add equipment via UI
- [ ] Can add telemetry via API
- [ ] Real-time updates working (3-second refresh)
- [ ] Alerts trigger when temp exceeds threshold
- [ ] Notifications display correctly
- [ ] Search functionality works
- [ ] Edit and delete operations work

---
