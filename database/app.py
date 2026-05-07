"""
Heat Stress Detector Web Dashboard - Backend (Flask)
Handles all CRUD operations, database interactions, and API endpoints
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',  # Change to your MySQL password
    'database': 'heat_stress_db',
    'port': 3306
}


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


def validate_temperature(temp):
    """
    Validate temperature input.
    Returns tuple (is_valid, error_message)
    """
    if temp is None:
        return False, "Temperature value is required"
    try:
        temp_float = float(temp)
        if temp_float < -273.15:  # Absolute zero check
            return False, "Temperature cannot be below absolute zero (-273.15°C)"
        if temp_float > 200:  # Reasonable upper limit for industrial equipment
            return False, "Temperature exceeds reasonable limit (200°C)"
        return True, None
    except (ValueError, TypeError):
        return False, "Temperature must be a valid number"


def validate_equipment_id(equipment_id):
    """
    Validate that equipment ID exists in database.
    Returns tuple (is_valid, error_message)
    """
    if equipment_id is None:
        return False, "Equipment ID is required"
    try:
        eq_id = int(equipment_id)
        if eq_id <= 0:
            return False, "Equipment ID must be a positive integer"
        return True, None
    except (ValueError, TypeError):
        return False, "Equipment ID must be a valid integer"


def equipment_exists(equipment_id):
    """
    Check if equipment with given ID exists in database.
    """
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
        "max_temp_threshold": 100.5
    }
    """
    try:
        data = request.get_json()
        
        # Validation
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        name = data.get('name', '').strip()
        max_temp = data.get('max_temp_threshold')
        
        if not name:
            return jsonify({'error': 'Equipment name is required and cannot be empty'}), 400
        
        if len(name) > 100:
            return jsonify({'error': 'Equipment name must not exceed 100 characters'}), 400
        
        is_valid, error_msg = validate_temperature(max_temp)
        if not is_valid:
            return jsonify({'error': f'Invalid max_temp_threshold: {error_msg}'}), 400
        
        # Database operation
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Equipment (Name, Max_Temp_Threshold) VALUES (%s, %s)",
                (name, float(max_temp))
            )
            conn.commit()
            equipment_id = cursor.lastrowid
            cursor.close()
            
            logger.info(f"Equipment created: ID={equipment_id}, Name={name}")
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
    Expected JSON: {
        "equipment_id": 1,
        "current_temp": 85.5
    }
    """
    try:
        data = request.get_json()
        
        # Validation
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
        
        # Check if equipment exists
        if not equipment_exists(equipment_id):
            return jsonify({'error': f'Equipment with ID {equipment_id} does not exist'}), 404
        
        # Database operation
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Telemetry (Equipment_ID, Current_Temp, Timestamp) VALUES (%s, %s, NOW())",
                (int(equipment_id), float(current_temp))
            )
            conn.commit()
            log_id = cursor.lastrowid
            cursor.close()
            
            logger.info(f"Telemetry recorded: Equipment_ID={equipment_id}, Temp={current_temp}°C")
            return jsonify({
                'success': True,
                'log_id': log_id,
                'message': 'Temperature reading recorded successfully'
            }), 201
        
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
    Fetch all equipment with their latest temperature readings.
    Returns list of equipment with most recent telemetry data.
    """
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Query to get all equipment with their latest temperature reading
            query = """
                SELECT 
                    e.Equipment_ID,
                    e.Name,
                    e.Max_Temp_Threshold,
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
            cursor.close()
            
            # Convert datetime objects to strings for JSON serialization
            for eq in equipment_list:
                if eq['Timestamp']:
                    eq['Timestamp'] = eq['Timestamp'].isoformat()
            
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
            
            # Get recent telemetry (last 100 readings)
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
            
            return jsonify({
                'success': True,
                'equipment': equipment,
                'recent_telemetry': telemetry
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
    Update equipment details (max temperature threshold).
    Expected JSON: {
        "name": "New Name" (optional),
        "max_temp_threshold": 95.5
    }
    """
    try:
        is_valid, error_msg = validate_equipment_id(equipment_id)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        # Check if equipment exists
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
    # Run Flask in development mode
    # For production, use a WSGI server like Gunicorn
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
