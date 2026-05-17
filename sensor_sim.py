#!/usr/bin/env python3

import requests
import time
import random
import sys
from datetime import datetime
from requests.exceptions import ConnectionError, Timeout, RequestException

# CRITICAL: Flask server base URL
BASE_URL = "http://10.57.23.226:5000"
EQUIPMENT_ENDPOINT = f"{BASE_URL}/api/equipment"
TELEMETRY_ENDPOINT = f"{BASE_URL}/api/telemetry"

# Simulation parameters
LOOP_INTERVAL = 3  # seconds between updates
MIN_TEMP = 25.0    # Minimum realistic temperature (°C)
MAX_TEMP = 120.0   # Maximum realistic temperature (°C)
TEMP_FLUCTUATION_MIN = -2.0  # Cooling range
TEMP_FLUCTUATION_MAX = 2.5   # Heating range

# Equipment tracking
equipment_states = {}


def print_banner():
    """Display startup banner"""
    print("\n" + "="*80)
    print("  HEAT STRESS DETECTOR - IoT SENSOR SIMULATOR".center(80))
    print("="*80)
    print(f" Target Server: {BASE_URL}")
    print(f"  Update Interval: {LOOP_INTERVAL} seconds")
    print(f"  Temperature Range: {MIN_TEMP}°C - {MAX_TEMP}°C")
    print("="*80 + "\n")


def get_timestamp():
    """Get formatted timestamp for logging"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def discover_equipment():
    """
    Auto-discovery: Fetch all equipment from the Flask API
    Returns: List of equipment dictionaries or None on failure
    """
    print(f" [{get_timestamp()}] Discovering equipment from server...")
    
    try:
        response = requests.get(EQUIPMENT_ENDPOINT, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different JSON response structures
        equipment_list = []
        
        if isinstance(data, dict):
            # Check for common keys that might contain equipment list
            if 'equipment' in data:
                equipment_list = data['equipment']
            elif 'data' in data:
                equipment_list = data['data']
            elif 'items' in data:
                equipment_list = data['items']
            else:
                # Assume the dict itself is a single equipment item
                equipment_list = [data]
        elif isinstance(data, list):
            equipment_list = data
        
        if not equipment_list:
            print("  No equipment found on the server!")
            return None
        
        print(f" Successfully discovered {len(equipment_list)} equipment(s):")
        
        discovered = []
        for eq in equipment_list:
            # Handle different ID field variations
            eq_id = eq.get('Equipment_ID') or eq.get('equipment_id') or eq.get('id')
            eq_name = eq.get('Name') or eq.get('name') or f"Equipment #{eq_id}"
            eq_threshold = eq.get('Max_Temp_Threshold') or eq.get('max_temp_threshold') or 80.0
            eq_location = eq.get('Location') or eq.get('location') or "Unknown"
            
            if eq_id:
                discovered.append({
                    'id': eq_id,
                    'name': eq_name,
                    'threshold': float(eq_threshold),
                    'location': eq_location
                })
                print(f"   📍 ID: {eq_id} | Name: {eq_name} | Location: {eq_location} | Max: {eq_threshold}°C")
        
        return discovered
    
    except ConnectionError:
        print(f"❌ Connection Error: Cannot reach server at {BASE_URL}")
        print("    Make sure the Flask server is running!")
        return None
    
    except Timeout:
        print(f" Timeout Error: Server took too long to respond")
        return None
    
    except RequestException as e:
        print(f"❌ Request Error: {str(e)}")
        return None
    
    except Exception as e:
        print(f"❌ Unexpected Error during discovery: {str(e)}")
        return None


def initialize_equipment_states(equipment_list):
    """
    Initialize temperature states for all equipment with random starting values
    """
    global equipment_states
    
    print(f"\n Initializing random starting temperatures...")
    
    for eq in equipment_list:
        eq_id = eq['id']
        # Random starting temperature between 35-50°C (realistic warm baseline)
        starting_temp = round(random.uniform(35.0, 50.0), 2)
        
        equipment_states[eq_id] = {
            'name': eq['name'],
            'current_temp': starting_temp,
            'threshold': eq['threshold'],
            'location': eq['location'],
            'trend': 'stable'  # stable, rising, falling
        }
        
        print(f"     {eq['name']}: {starting_temp}°C")
    
    print(f" Initialized {len(equipment_states)} sensor(s)\n")


def simulate_temperature_change(current_temp, threshold):
    """
    Simulate realistic temperature fluctuation with tendency toward thermal stress
    
    Args:
        current_temp: Current temperature
        threshold: Maximum temperature threshold
        
    Returns:
        New temperature value
    """
    # Add random fluctuation
    fluctuation = random.uniform(TEMP_FLUCTUATION_MIN, TEMP_FLUCTUATION_MAX)
    
    # If approaching threshold, add occasional spike (simulate stress condition)
    if current_temp > threshold * 0.85:  # Within 15% of threshold
        if random.random() < 0.3:  # 30% chance of spike
            fluctuation += random.uniform(0.5, 2.0)
    
    new_temp = current_temp + fluctuation
    
    # Enforce realistic bounds
    new_temp = max(MIN_TEMP, min(MAX_TEMP, new_temp))
    
    return round(new_temp, 2)


def determine_trend(old_temp, new_temp):
    """Determine if temperature is rising, falling, or stable"""
    diff = new_temp - old_temp
    if diff > 0.5:
        return "rising", "📈"
    elif diff < -0.5:
        return "falling", "📉"
    else:
        return "stable", "➡️"


def get_status_emoji(temp, threshold):
    """Get status emoji based on temperature vs threshold"""
    if temp >= threshold:
        return "🔴"  # Critical
    elif temp >= threshold * 0.9:
        return "🟡"  # Warning
    else:
        return "🟢"  # Normal


def send_telemetry(equipment_id, temperature):
    """
    Send temperature reading to Flask API
    
    Args:
        equipment_id: Equipment ID
        temperature: Temperature reading in Celsius
        
    Returns:
        True if successful, False otherwise
    """
    payload = {
        "equipment_id": equipment_id,
        "current_temp": temperature
    }
    
    try:
        response = requests.post(
            TELEMETRY_ENDPOINT, 
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        return True
    
    except ConnectionError:
        print(f"   ❌ Connection Error: Cannot reach server")
        return False
    
    except Timeout:
        print(f"   ⏰ Timeout: Server took too long to respond")
        return False
    
    except RequestException as e:
        print(f"   ❌ Request Error: {str(e)}")
        return False
    
    except Exception as e:
        print(f"   ❌ Unexpected Error: {str(e)}")
        return False


def simulation_loop():
    """Main simulation loop - continuously update temperatures"""
    global equipment_states
    
    print("   Starting continuous telemetry simulation...")
    print("   Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            print(f"🔄 Cycle #{cycle_count} - {get_timestamp()}")
            print("-" * 80)
            
            success_count = 0
            fail_count = 0
            
            for eq_id, state in equipment_states.items():
                # Calculate new temperature
                old_temp = state['current_temp']
                new_temp = simulate_temperature_change(old_temp, state['threshold'])
                
                # Update state
                trend, trend_emoji = determine_trend(old_temp, new_temp)
                state['current_temp'] = new_temp
                state['trend'] = trend
                
                # Determine status
                status_emoji = get_status_emoji(new_temp, state['threshold'])
                
                # Send to API
                if send_telemetry(eq_id, new_temp):
                    print(f"   {status_emoji} {trend_emoji} [{state['name']}] "
                          f"{new_temp}°C (Δ{new_temp - old_temp:+.2f}°C) "
                          f"→ Threshold: {state['threshold']}°C ✅")
                    success_count += 1
                else:
                    print(f"   ⚠️  [{state['name']}] Failed to send telemetry")
                    fail_count += 1
            
            # Summary
            print("-" * 80)
            print(f"   📊 Summary: {success_count} successful, {fail_count} failed")
            print(f"   ⏳ Sleeping for {LOOP_INTERVAL} seconds...\n")
            
            time.sleep(LOOP_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n⛔ Simulation stopped by user (Ctrl+C)")
        print("👋 Shutting down gracefully...")
        sys.exit(0)


def main():
    """Main entry point"""
    print_banner()
    
    # Step 1: Auto-discovery
    equipment = discover_equipment()
    
    if not equipment:
        print("\n❌ Failed to discover equipment. Exiting...")
        print("💡 Troubleshooting:")
        print("   1. Ensure Flask server is running at http://10.57.23.226:5000")
        print("   2. Check if equipment exists in database")
        print("   3. Verify network connectivity")
        sys.exit(1)
    
    # Step 2: Initialize states
    initialize_equipment_states(equipment)
    
    # Step 3: Start simulation loop
    simulation_loop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n Fatal Error: {str(e)}")
        sys.exit(1)
