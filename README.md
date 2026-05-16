# Heat Stress Detection Dashboard (HSDD) - Process Documentation

### We developed and implemented a cloud-based IoT telemetry system designed for monitoring, analyzing, and predicting thermal failures in industrial equipment. The system uses a Python (Flask) backend and a MySQL database, with a vanilla JavaScript frontend. It processes continuous temperature streams to dynamically assess equipment health. By applying predictive anomaly detection using the dT/dt method, the dashboard can spot rapid heating events and sends automated email alerts to prevent physical damage. The entire platform runs on a secured Linux virtual machine set up with systemd, ensuring maximum resilience and continuous operation. This documentation outlines the complete setup process for the Heat Stress Detection Dashboard system, including server configuration, frontend development, backend implementation, and security setup.
---

## Project Structure

```
heat-stress-detector/
├── app_v2.py                                    # Flask backend application
├── sensor_sim.py                                # Temp Sensor Simulator
├── allInOne.sql                                 # MySQL database schema
├── templates/
│   └── heat_stress_detector_v2.html             # Main dashboard HTML
└── static/
    ├── style_v2.css                             # Professional dark theme CSS
    └── script.js                                # Real-time dashboard JavaScript
```

---

## Requirements

- **Python 3.8+**
- **MySQL 5.7+ or MariaDB 10.3+**
- **pip** (Python package manager)
- **Git** (optional, for version control)

---

## Initial Server Setup

### 1. Create a New Server
Create a new server for the system with the following network configuration:

**Network Configuration:**
- Switch the network setting to **Bridge Adapter** to ensure both internet access and reachability from your host machine.

---

## Pre-Installation and Remote Access

### 2. Prepare for Remote Access

Update system packages:
```bash
sudo apt update
```

Install OpenSSH server for remote access:
```bash
sudo apt install openssh-server
```

Connect to the server remotely:
```bash
ssh shoiming@our_server_ip
```

---

## System Dependencies Installation

### 3. Install Core Services

Install Apache web server and MySQL database server:
```bash
sudo apt install apache2 mysql-server -y
```

**Purpose:** Prepare the installation process for the Apache server, MySQL database server, Python package manager, Flask, mysql-connector-python, and Flask-CORS.

### 4. Verify Installation

Check MySQL installation and status:
```bash
mysql --version && sudo systemctl status mysql
```

Check Apache installation and status:
```bash
apache2 -v && sudo systemctl status apache2
```

### 5. Install Python and Dependencies

Install Python pip:
```bash
sudo apt update && sudo apt install python3-pip -y
```

Install Python packages:
```bash
pip install flask mysql-connector-python flask-cors --break-system-packages
```

---

## User Configuration

### 6. Create and Configure User

Add a new user:
```bash
sudo adduser new_user
```

Set ownership for web directory:
```bash
sudo chown -R new_user:new_user /var/www/html
```

---

## Part I. Building the Frontend (HTML, CSS and Vanilla JS)

### 7. Create Frontend Files

Create the main HTML file:
```bash
sudo nano /var/www/html/heat_stress_detector_v2.html
```

Create the CSS stylesheet:
```bash
sudo nano /var/www/html/style.css
```

Create the JavaScript file:
```bash
sudo nano /var/www/html/script_v2.js
```

---

## Database Setup

### 8. Configure MySQL Database

Access MySQL:
```bash
sudo mysql -u root -p
```

---

## Part II. Choosing the Python Framework (Flask)

### 9. Setup Flask Application

Create project directory:
```bash
mkdir ~/heat_stress_detector && cd ~/heat_stress_detector
```

Create the main Flask application:
```bash
sudo nano app_v2.py
```

Create the sensor simulator:
```bash
sudo nano sensor.sim.py
```

---

## Part III. Self-Hosted Dashboard System

### 10. Configure Systemd Services

Create service file for the Heat Stress Detector:
```bash
sudo nano /etc/systemd/system/heatstressdetector.service
```

Create service file for the Sensor Simulator:
```bash
sudo nano /etc/systemd/system/sensorsimulator.service
```

### 11. Enable and Start Services

Reload systemd daemon:
```bash
sudo systemctl daemon-reload
```

Enable services to start on boot:
```bash
sudo systemctl enable heatstressdetector
sudo systemctl enable sensorsimulator
```

Start the services:
```bash
sudo systemctl start heatstressdetector
sudo systemctl start sensorsimulator
```

---

## PART IV. Security Setup

### 12. Configure Firewall (UFW)

Allow SSH access:
```bash
sudo ufw allow 22/tcp
```

Allow HTTP access:
```bash
sudo ufw allow 80/tcp
```

Allow Flask application access:
```bash
sudo ufw allow 5000/tcp
```

Enable the firewall:
```bash
sudo ufw enable
```

---

## PART V. Test Resilience

### 13. System Reboot Test

Reboot the system to test service persistence:
```bash
sudo reboot
```

After reboot, verify that all services start automatically and the system is fully operational.

---

## Notes

- Ensure all commands are executed with appropriate permissions
- Replace `our_server_ip` with your actual server IP address
- Replace `shoiming` with your actual username
- Verify service status after each major step
- Keep track of database credentials and user passwords securely

---

## Service Verification Commands

After setup, use these commands to verify services are running:

```bash
# Check Apache status
sudo systemctl status apache2

# Check MySQL status
sudo systemctl status mysql

# Check Heat Stress Detector service
sudo systemctl status heatstressdetector

# Check Sensor Simulator service
sudo systemctl status sensorsimulator

# Check firewall status
sudo ufw status
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


## Contributors
DREAM TEAM Sa Cloud members:
1. Carandang Serrano Banjo
2. Hkawng Zam Jap
3. Isid De Torres
4. Joshua Garcia
5. Reighnard Glorioso

---

