from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask_cors import CORS
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from io import StringIO
import csv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ==================== CRITICAL: CORS CONFIGURATION FOR SPECIFIC IP ====================
# Configure CORS to accept requests from the Linux VM at 10.57.23.226
CORS(app, 
     origins=["http://your_ip", "http://your_ip", "localhost", "127.0.0.1"],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
)

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'heatstress_user',
    'password': 'password123',  # Change to your MySQL password
    'database': 'heat_stress_db',
    'port': 3306
}

# ==================== EMAIL CONFIGURATION (Feature 3) ====================
# Store last email timestamps to prevent spam (equipment_id -> last_email_timestamp)
LAST_EMAIL_SENT = {}
EMAIL_COOLDOWN_MINUTES = 15  # Only send one email per equipment every 15 minutes

EMAIL_CONFIG = {
    'sender_email': os.getenv('ALERT_EMAIL_SENDER', 'alerts@heatdetector.local'),
    'sender_password': os.getenv('ALERT_EMAIL_PASSWORD', 'password'),
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', '587')),
    'recipient_emails': os.getenv('ALERT_RECIPIENTS', 'admin@example.com').split(','),
}


# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """
    Establish a connection to the MySQL database.
    Returns a connection object or None if connection fails.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        return None


# ==================== VALIDATION FUNCTIONS ====================

def validate_temperature(temp):
    """Validate temperature input. Returns tuple (is_valid, error_message)"""
    if temp is None:
        return False, "Temperature value is required"
    try:
        temp_float = float(temp)
        if temp_float < -273.15:
            return False, "Temperature cannot be below absolute zero (-273.15°C)"
        if temp_float > 200:
            return False, "Temperature exceeds reasonable limit (200°C)"
        return True, None
    except (ValueError, TypeError):
        return False, "Temperature must be a valid number"


def validate_equipment_id(equipment_id):
    """Validate that equipment ID exists in database. Returns tuple (is_valid, error_message)"""
    if equipment_id is None:
        return False, "Equipment ID is required"
    try:
        eq_id = int(equipment_id)
        if eq_id <= 0:
            return False, "Equipment ID must be a positive integer"
        return True, None
    except (ValueError, TypeError):
        return False, "Equipment ID must be a valid integer"


def validate_location(location):
    """Validate location string. Returns tuple (is_valid, error_message)"""
    if not location:
        return False, "Location cannot be empty"
    if len(location) > 100:
        return False, "Location must not exceed 100 characters"
    return True, None


def equipment_exists(equipment_id):
    """Check if equipment with given ID exists in database."""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Equipment_ID FROM Equipment WHERE Equipment_ID = %s", (equipment_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result is not None
    except Error as e:
        logger.error(f"Error checking equipment existence: {e}")
        return False


# ==================== FEATURE 2: RAPID HEATING DETECTION ====================

def detect_rapid_heating(equipment_id, current_temp):
    """
    Detect rapid temperature increase (Feature 2).
    Returns tuple (is_rapid_heating, rate_of_change, previous_temp)
    
    Logic: If current temp is > 10°C higher than reading from < 60 seconds ago, flag as rapid heating.
    """
    try:
        conn = get_db_connection()
        if not conn:
            return False, 0.0, None
        
        cursor = conn.cursor(dictionary=True)
        
        # Get the most recent telemetry reading from the last 60 seconds
        sixty_seconds_ago = datetime.now() - timedelta(seconds=60)
        
        cursor.execute("""
            SELECT Current_Temp, Timestamp
            FROM Telemetry
            WHERE Equipment_ID = %s
            AND Timestamp > %s
            ORDER BY Timestamp DESC
            LIMIT 1
        """, (equipment_id, sixty_seconds_ago))
        
        previous_reading = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not previous_reading:
            # No previous reading in the 60-second window
            return False, 0.0, None
        
        previous_temp = previous_reading['Current_Temp']
        temp_increase = current_temp - previous_temp
        
        # Flag as rapid heating if increase > 10°C
        if temp_increase > 10.0:
            return True, temp_increase, previous_temp
        
        return False, temp_increase, previous_temp
    
    except Error as e:
        logger.error(f"Error detecting rapid heating: {e}")
        return False, 0.0, None


# ==================== FEATURE 3: EMAIL NOTIFICATION ====================

def should_send_email(equipment_id):
    """
    Check if we should send an email for this equipment.
    Only send one email per equipment every EMAIL_COOLDOWN_MINUTES minutes.
    """
    now = datetime.now()
    
    if equipment_id not in LAST_EMAIL_SENT:
        LAST_EMAIL_SENT[equipment_id] = now
        return True
    
    time_since_last_email = now - LAST_EMAIL_SENT[equipment_id]
    if time_since_last_email >= timedelta(minutes=EMAIL_COOLDOWN_MINUTES):
        LAST_EMAIL_SENT[equipment_id] = now
        return True
    
    return False


def send_alert_email(equipment_name, alert_type, current_temp, threshold, location):
    """
    Send alert email notification (Feature 3).
    
    Args:
        equipment_name: Name of the equipment
        alert_type: 'CRITICAL' or 'RAPID_HEATING'
        current_temp: Current temperature reading
        threshold: Max temperature threshold
        location: Equipment location
    """
    try:
        # Only proceed if email config is valid (not default values)
        if EMAIL_CONFIG['sender_email'] == 'alerts@heatdetector.local':
            logger.info(f"Email config not set (using defaults). Skipping email send for {equipment_name}")
            return False
        
        subject = f"🚨 Heat Detector Alert: {alert_type} - {equipment_name}"
        
        if alert_type == 'CRITICAL':
            body = f"""
            Dear Sir/ma'am,

            This is an automated notification from the Heat Stress Monitoring System regarding a critical temperature condition detected in your equipment.

            ━━━━━━━━━━━━━━━━━━━━━━
            ALERT DETAILS
            ━━━━━━━━━━━━━━━━━━━━━━
            
            Equipment: {equipment_name}
            Location: {location}
            Current Temperature: {current_temp}°C
            Max Threshold: {threshold}°C
            Alert Type: CRITICAL (Exceeds threshold)
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            ━━━━━━━━━━━━━━━━━━━━━━

            Immediate action is strongly recommended to prevent possible equipment damage, overheating, or operational interruption.

            Please inspect the affected equipment and perform the necessary safety procedures as soon as possible.

            If the issue persists, kindly contact the system administrator or maintenance team for further assistance.

            Thank you.

            Best regards,
            Heat Stress Monitoring System Team
            """
        else:  # RAPID_HEATING
            body = f"""
            Dear Sir/ Ma'am,

            This is an automated notification from the Heat Stress Monitoring System regarding an unusual rapid increase in temperature detected in your equipment.

            ━━━━━━━━━━━━━━━━━━━━━━
            ALERT DETAILS
            ━━━━━━━━━━━━━━━━━━━━━━
            
            Equipment: {equipment_name}
            Location: {location}
            Current Temperature: {current_temp}°C
            Max Threshold: {threshold}°C
            Alert Type: RAPID_HEATING (Temperature rising quickly)
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            ━━━━━━━━━━━━━━━━━━━━━━

            The system has detected a sudden rise in temperature that may indicate abnormal equipment behavior, ventilation issues, or possible overheating risks.

            Please monitor the equipment closely and perform an inspection if necessary to prevent the condition from escalating into a critical alert.

            If the temperature continues to rise, immediate maintenance action is recommended.

            Thank you.

            Best regards,
            Heat Stress Monitoring System
            """
        
        # Create MIME message
        message = MIMEMultipart()
        message['From'] = EMAIL_CONFIG['sender_email']
        message['To'] = ', '.join(EMAIL_CONFIG['recipient_emails'])
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(message)
        
        logger.info(f"Alert email sent for {equipment_name}: {alert_type}")
        return True
    
    except Exception as e:
        logger.error(f"Error sending alert email: {e}")
        return False


# ==================== FEATURE 6: HEALTH SCORE CALCULATION ====================

def calculate_health_score(equipment_data):
    """
    Calculate equipment health score (Feature 6).
    
    Formula:
      Start at 100%
      Deduct 5% for every Overheat_Count
      Deduct 20% if currently overheating
      Floor at 0%
    
    Returns: health_score (0-100), status ('Healthy', 'Warning', 'Critical')
    """
    score = 100.0
    
    # Deduct 5% for every overheat event
    overheat_count = equipment_data.get('Overheat_Count', 0) or 0
    score -= (overheat_count * 5)
    
    # Deduct 20% if currently overheating
    # Deduct 20% if currently overheating
    current_temp = equipment_data.get('Current_Temp')
    max_threshold = equipment_data.get('Max_Temp_Threshold')
    
    if current_temp is not None and max_threshold is not None and current_temp > max_threshold:
        score -= 20
    
    # Floor at 0%
    score = max(0, score)
    
    # Determine status
    if score >= 80:
        status = 'Healthy'
    elif score >= 50:
        status = 'Warning'
    else:
        status = 'Critical'
    
    return int(score), status


# ==================== ROUTES ====================

@app.route('/')
def dashboard():
    """Render the main dashboard page."""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return jsonify({'error': 'Failed to load dashboard'}), 500


# ==================== CREATE OPERATIONS ====================

@app.route('/api/equipment', methods=['POST'])
def create_equipment():
    """
    Create a new equipment entry.
    Expected JSON: {
        "name": "Equipment Name",
        "max_temp_threshold": 100.5,
        "location": "Server Room A"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        name = data.get('name', '').strip()
        max_temp = data.get('max_temp_threshold')
        location = data.get('location', '').strip()  # Feature 5: Location support
        
        if not name:
            return jsonify({'error': 'Equipment name is required and cannot be empty'}), 400
        
        if len(name) > 100:
            return jsonify({'error': 'Equipment name must not exceed 100 characters'}), 400
        
        is_valid, error_msg = validate_temperature(max_temp)
        if not is_valid:
            return jsonify({'error': f'Invalid max_temp_threshold: {error_msg}'}), 400
        
        # Validate location (Feature 5)
        is_valid, error_msg = validate_location(location)
        if not is_valid:
            return jsonify({'error': f'Invalid location: {error_msg}'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Equipment (Name, Max_Temp_Threshold, Location) VALUES (%s, %s, %s)",
                (name, float(max_temp), location)
            )
            conn.commit()
            equipment_id = cursor.lastrowid
            cursor.close()
            
            logger.info(f"Equipment created: ID={equipment_id}, Name={name}, Location={location}")
            return jsonify({
                'success': True,
                'equipment_id': equipment_id,
                'message': f'Equipment "{name}" created successfully'
            }), 201
        
        except Error as e:
            logger.error(f"Database insert error: {e}")
            return jsonify({'error': 'Failed to create equipment'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in create_equipment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/telemetry', methods=['POST'])
def add_telemetry():
    """
    Add a telemetry (temperature reading) entry.
    Includes rapid heating detection (Feature 2) and email notifications (Feature 3).
    
    Expected JSON: {
        "equipment_id": 1,
        "current_temp": 85.5
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        equipment_id = data.get('equipment_id')
        current_temp = data.get('current_temp')
        
        is_valid, error_msg = validate_equipment_id(equipment_id)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        is_valid, error_msg = validate_temperature(current_temp)
        if not is_valid:
            return jsonify({'error': f'Invalid current_temp: {error_msg}'}), 400
        
        if not equipment_exists(equipment_id):
            return jsonify({'error': f'Equipment with ID {equipment_id} does not exist'}), 404
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get equipment details for threshold check and location (Feature 3, 5)
            cursor.execute(
                "SELECT Name, Max_Temp_Threshold, Location FROM Equipment WHERE Equipment_ID = %s",
                (equipment_id,)
            )
            equipment = cursor.fetchone()
            
            # Feature 2: Detect rapid heating
            is_rapid_heating, rate_of_change, previous_temp = detect_rapid_heating(equipment_id, current_temp)
            
            # Feature 3: Determine if we need to send alert emails
            should_email_critical = current_temp > equipment['Max_Temp_Threshold']
            should_email_rapid = is_rapid_heating
            
            response_data = {
                'success': True,
                'log_id': None,
                'message': 'Temperature reading recorded successfully',
                'alerts': {
                    'rapid_heating': is_rapid_heating,
                    'critical_temp': should_email_critical,
                    'rate_of_change': round(rate_of_change, 2)
                }
            }
            
            # Insert telemetry reading
            cursor.execute(
                "INSERT INTO Telemetry (Equipment_ID, Current_Temp, Timestamp) VALUES (%s, %s, NOW())",
                (int(equipment_id), float(current_temp))
            )
            conn.commit()
            response_data['log_id'] = cursor.lastrowid
            
            # Feature 3: Send email notifications if needed
            if should_email_critical and should_send_email(equipment_id):
                send_alert_email(
                    equipment['Name'],
                    'CRITICAL',
                    current_temp,
                    equipment['Max_Temp_Threshold'],
                    equipment['Location']
                )
            
            if should_email_rapid and should_send_email(equipment_id):
                send_alert_email(
                    equipment['Name'],
                    'RAPID_HEATING',
                    current_temp,
                    equipment['Max_Temp_Threshold'],
                    equipment['Location']
                )
            
            # Feature 1: Get last 20 readings for trend data (for Chart.js)
            cursor.execute("""
                SELECT Current_Temp, Timestamp
                FROM Telemetry
                WHERE Equipment_ID = %s
                ORDER BY Timestamp DESC
                LIMIT 20
            """, (equipment_id,))
            
            recent_readings = cursor.fetchall()
            # Reverse to get chronological order
            recent_readings = list(reversed(recent_readings))
            trend_data = {
                'temps': [float(r['Current_Temp']) for r in recent_readings],
                'timestamps': [r['Timestamp'].isoformat() for r in recent_readings]
            }
            response_data['trend_data'] = trend_data
            
            cursor.close()
            logger.info(f"Telemetry recorded: Equipment_ID={equipment_id}, Temp={current_temp}°C, RapidHeating={is_rapid_heating}")
            
            return jsonify(response_data), 201
        
        except Error as e:
            logger.error(f"Database insert error: {e}")
            return jsonify({'error': 'Failed to record telemetry'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in add_telemetry: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== READ OPERATIONS ====================

@app.route('/api/equipment', methods=['GET'])
def get_all_equipment():
    """
    Fetch all equipment with their latest temperature readings and health scores (Feature 6).
    Includes location data (Feature 5) and trend data (Feature 1).
    """
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Query to get all equipment with their latest temperature reading and location
            query = """
                SELECT 
                    e.Equipment_ID,
                    e.Name,
                    e.Max_Temp_Threshold,
                    e.Location,
                    e.Overheat_Count,
                    COALESCE(t.Current_Temp, NULL) as Current_Temp,
                    COALESCE(t.Timestamp, NULL) as Timestamp,
                    CASE 
                        WHEN t.Current_Temp > e.Max_Temp_Threshold THEN 'ALERT'
                        WHEN t.Current_Temp > (e.Max_Temp_Threshold * 0.9) THEN 'WARNING'
                        ELSE 'NORMAL'
                    END as Status
                FROM Equipment e
                LEFT JOIN (
                    SELECT Equipment_ID, Current_Temp, Timestamp
                    FROM Telemetry
                    WHERE (Equipment_ID, Timestamp) IN (
                        SELECT Equipment_ID, MAX(Timestamp)
                        FROM Telemetry
                        GROUP BY Equipment_ID
                    )
                ) t ON e.Equipment_ID = t.Equipment_ID
                ORDER BY e.Equipment_ID
            """
            
            cursor.execute(query)
            equipment_list = cursor.fetchall()
            
            # Feature 1: Get trend data (last 20 readings) for each equipment
            # Feature 6: Calculate health score for each equipment
            for eq in equipment_list:
                if eq['Timestamp']:
                    eq['Timestamp'] = eq['Timestamp'].isoformat()
                
                # Feature 6: Calculate health score
                health_score, health_status = calculate_health_score(eq)
                eq['Health_Score'] = health_score
                eq['Health_Status'] = health_status
                
                # Feature 1: Get trend data for Chart.js
                cursor.execute("""
                    SELECT Current_Temp, Timestamp
                    FROM Telemetry
                    WHERE Equipment_ID = %s
                    ORDER BY Timestamp DESC
                    LIMIT 20
                """, (eq['Equipment_ID'],))
                
                recent_readings = cursor.fetchall()
                recent_readings = list(reversed(recent_readings))
                
                eq['Trend_Data'] = {
                    'temps': [float(r['Current_Temp']) for r in recent_readings],
                    'timestamps': [r['Timestamp'].isoformat() for r in recent_readings]
                }
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'count': len(equipment_list),
                'data': equipment_list
            }), 200
        
        except Error as e:
            logger.error(f"Database query error: {e}")
            return jsonify({'error': 'Failed to fetch equipment data'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in get_all_equipment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/equipment/<int:equipment_id>', methods=['GET'])
def get_equipment_detail(equipment_id):
    """
    Fetch details of a specific equipment including recent telemetry history.
    Includes health score (Feature 6), location (Feature 5), and trend data (Feature 1).
    """
    try:
        is_valid, error_msg = validate_equipment_id(equipment_id)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get equipment details
            cursor.execute(
                "SELECT * FROM Equipment WHERE Equipment_ID = %s",
                (equipment_id,)
            )
            equipment = cursor.fetchone()
            
            if not equipment:
                cursor.close()
                conn.close()
                return jsonify({'error': f'Equipment with ID {equipment_id} not found'}), 404
            
            # Feature 1: Get recent telemetry (last 100 readings for detailed history)
            cursor.execute(
                """
                SELECT Log_ID, Equipment_ID, Current_Temp, Timestamp
                FROM Telemetry
                WHERE Equipment_ID = %s
                ORDER BY Timestamp DESC
                LIMIT 100
                """,
                (equipment_id,)
            )
            telemetry = cursor.fetchall()
            cursor.close()
            
            # Convert datetime objects to strings
            for t in telemetry:
                if t['Timestamp']:
                    t['Timestamp'] = t['Timestamp'].isoformat()
            
            # Feature 6: Calculate health score
            health_score, health_status = calculate_health_score(equipment)
            equipment['Health_Score'] = health_score
            equipment['Health_Status'] = health_status
            
            # Feature 1: Get trend data for the detailed view
            trend_temps = [float(t['Current_Temp']) for t in reversed(telemetry)]
            trend_times = [t['Timestamp'] for t in reversed(telemetry)]
            
            return jsonify({
                'success': True,
                'equipment': equipment,
                'recent_telemetry': telemetry,
                'trend_data': {
                    'temps': trend_temps,
                    'timestamps': trend_times
                }
            }), 200
        
        except Error as e:
            logger.error(f"Database query error: {e}")
            return jsonify({'error': 'Failed to fetch equipment details'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in get_equipment_detail: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== UPDATE OPERATIONS ====================

@app.route('/api/equipment/<int:equipment_id>', methods=['PUT', 'POST'])
def update_equipment(equipment_id):
    """
    Update equipment details (max temperature threshold, name, location).
    Expected JSON: {
        "name": "New Name" (optional),
        "max_temp_threshold": 95.5 (optional),
        "location": "New Location" (optional)
    }
    """
    try:
        is_valid, error_msg = validate_equipment_id(equipment_id)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        if not equipment_exists(equipment_id):
            return jsonify({'error': f'Equipment with ID {equipment_id} does not exist'}), 404
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            updates = []
            params = []
            
            # Handle name update
            if 'name' in data:
                name = data.get('name', '').strip()
                if name:
                    if len(name) > 100:
                        return jsonify({'error': 'Equipment name must not exceed 100 characters'}), 400
                    updates.append("Name = %s")
                    params.append(name)
            
            # Handle max_temp_threshold update
            if 'max_temp_threshold' in data:
                max_temp = data.get('max_temp_threshold')
                is_valid, error_msg = validate_temperature(max_temp)
                if not is_valid:
                    return jsonify({'error': f'Invalid max_temp_threshold: {error_msg}'}), 400
                updates.append("Max_Temp_Threshold = %s")
                params.append(float(max_temp))
            
            # Handle location update (Feature 5)
            if 'location' in data:
                location = data.get('location', '').strip()
                is_valid, error_msg = validate_location(location)
                if not is_valid:
                    return jsonify({'error': f'Invalid location: {error_msg}'}), 400
                updates.append("Location = %s")
                params.append(location)
            
            if not updates:
                return jsonify({'error': 'No valid fields to update'}), 400
            
            params.append(equipment_id)
            query = f"UPDATE Equipment SET {', '.join(updates)} WHERE Equipment_ID = %s"
            
            cursor.execute(query, params)
            conn.commit()
            cursor.close()
            
            logger.info(f"Equipment updated: ID={equipment_id}")
            return jsonify({
                'success': True,
                'message': 'Equipment updated successfully'
            }), 200
        
        except Error as e:
            logger.error(f"Database update error: {e}")
            return jsonify({'error': 'Failed to update equipment'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in update_equipment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== DELETE OPERATIONS ====================

@app.route('/api/telemetry/cleanup', methods=['DELETE'])
def cleanup_old_telemetry():
    """
    Delete telemetry logs older than 24 hours.
    """
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Calculate timestamp for 24 hours ago
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Delete old telemetry records
            cursor.execute(
                "DELETE FROM Telemetry WHERE Timestamp < %s",
                (cutoff_time,)
            )
            conn.commit()
            
            deleted_count = cursor.rowcount
            cursor.close()
            
            logger.info(f"Deleted {deleted_count} telemetry records older than 24 hours")
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Deleted {deleted_count} telemetry records older than 24 hours'
            }), 200
        
        except Error as e:
            logger.error(f"Database delete error: {e}")
            return jsonify({'error': 'Failed to cleanup telemetry'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in cleanup_old_telemetry: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/equipment/<int:equipment_id>', methods=['DELETE'])
def delete_equipment(equipment_id):
    """
    Delete equipment and all associated telemetry records.
    """
    try:
        is_valid, error_msg = validate_equipment_id(equipment_id)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        if not equipment_exists(equipment_id):
            return jsonify({'error': f'Equipment with ID {equipment_id} does not exist'}), 404
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Delete telemetry records first (foreign key constraint)
            cursor.execute("DELETE FROM Telemetry WHERE Equipment_ID = %s", (equipment_id,))
            
            # Delete equipment
            cursor.execute("DELETE FROM Equipment WHERE Equipment_ID = %s", (equipment_id,))
            conn.commit()
            
            cursor.close()
            
            logger.info(f"Equipment deleted: ID={equipment_id}")
            return jsonify({
                'success': True,
                'message': f'Equipment {equipment_id} and its telemetry records deleted'
            }), 200
        
        except Error as e:
            logger.error(f"Database delete error: {e}")
            return jsonify({'error': 'Failed to delete equipment'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in delete_equipment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== FEATURE 4: CSV EXPORT ====================

@app.route('/api/export', methods=['GET'])
def export_csv():
    """
    Export all equipment and telemetry data as CSV (Feature 4).
    Returns a downloadable CSV file with columns:
      Equipment_ID, Equipment_Name, Location, Max_Threshold, 
      Overheat_Count, Health_Score, Current_Temp, Timestamp
    """
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Query joined equipment and latest telemetry
            query = """
                SELECT 
                    e.Equipment_ID,
                    e.Name as Equipment_Name,
                    e.Location,
                    e.Max_Temp_Threshold,
                    e.Overheat_Count,
                    t.Current_Temp,
                    t.Timestamp
                FROM Equipment e
                LEFT JOIN (
                    SELECT Equipment_ID, Current_Temp, Timestamp
                    FROM Telemetry
                    WHERE (Equipment_ID, Timestamp) IN (
                        SELECT Equipment_ID, MAX(Timestamp)
                        FROM Telemetry
                        GROUP BY Equipment_ID
                    )
                ) t ON e.Equipment_ID = t.Equipment_ID
                ORDER BY e.Equipment_ID
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            
            # Create CSV in memory
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Equipment_ID',
                'Equipment_Name',
                'Location',
                'Max_Threshold_°C',
                'Overheat_Count',
                'Health_Score',
                'Current_Temp_°C',
                'Last_Reading_Timestamp'
            ])
            
            # Write data rows
            for row in rows:
                # Calculate health score, handling None values
                health_score, _ = calculate_health_score(row)
                
                # Handle None values for CSV
                current_temp = row['Current_Temp'] if row['Current_Temp'] is not None else 'N/A'
                timestamp = row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['Timestamp'] else 'N/A'
                location = row['Location'] if row['Location'] else 'Not Specified'
                
                writer.writerow([
                    row['Equipment_ID'],
                    row['Equipment_Name'],
                    location,
                    row['Max_Temp_Threshold'],
                    row['Overheat_Count'] or 0,
                    health_score,
                    current_temp,
                    timestamp
                ])
            
            # Convert to response
            csv_data = output.getvalue()
            output.close()
            
            # Create response with proper headers
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=heat_stress_report.csv'
            
            return response
        
        except Error as e:
            logger.error(f"Database query error during export: {e}")
            return jsonify({'error': 'Failed to export data'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Unexpected error in export_csv: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({'error': 'Method not allowed'}), 405


# ==================== MAIN ====================

if __name__ == '__main__':
    """
    Run Flask in development mode.
    For production, use a WSGI server like Gunicorn with proper configuration.
    
    IMPORTANT: The CORS configuration explicitly allows requests from:
      - http://10.57.23.226:5000 (Linux VM)
      - http://10.57.23.226
      - localhost and 127.0.0.1 (for local development)
    """
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
