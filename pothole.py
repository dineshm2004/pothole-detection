import os
import requests
import pynmea2
import json
import re
from flask import Flask, jsonify

app = Flask(__name__)

# Get Firebase details from environment variables
FIREBASE_HOST = os.getenv("FIREBASE_HOST", "https://potholedetection-68439-default-rtdb.firebaseio.com")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "your-default-key")  # Set a default for local testing

# Fetch data from Firebase
url = f"{FIREBASE_HOST}/.json?auth={FIREBASE_AUTH}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print("✅ Data fetched from Firebase successfully!\n")
else:
    print("❌ Failed to retrieve data:", response.status_code, response.text)
    data = {}  # Avoid app crash

# Extract sensor data if available
sensor_data = data.get("sensor_data", {})

# Function to clean and extract valid $GPRMC sentence
def extract_gprmc_sentence(nmea_string):
    if not nmea_string:
        return None
    clean_nmea = re.sub(r'[^\x20-\x7E]', '', nmea_string).strip()
    matches = re.findall(r'(\$GPRMC,[^\r\n]*)', clean_nmea)
    if matches and matches[-1].count(',') >= 11:
        return matches[-1]
    return None

# Function to parse NMEA GPS data
def parse_nmea(nmea_string):
    try:
        if not nmea_string:
            return None, None
        msg = pynmea2.parse(nmea_string)
        if isinstance(msg, pynmea2.types.talker.RMC):
            latitude = convert_latitude(msg.lat, msg.lat_dir)
            longitude = convert_longitude(msg.lon, msg.lon_dir)
            return latitude, longitude
    except pynmea2.ParseError:
        return None, None
    return None, None

# Convert latitude from NMEA format to decimal degrees
def convert_latitude(lat_str, direction):
    if not lat_str:
        return None
    degrees = float(lat_str[:2])
    minutes = float(lat_str[2:]) / 60
    latitude = degrees + minutes
    return -latitude if direction == "S" else latitude

# Convert longitude from NMEA format to decimal degrees
def convert_longitude(lon_str, direction):
    if not lon_str:
        return None
    degrees = float(lon_str[:3])
    minutes = float(lon_str[3:]) / 60
    longitude = degrees + minutes
    return -longitude if direction == "W" else longitude

# Process and extract GPS locations
locations = []
for key, entry in sensor_data.items():
    if isinstance(entry, dict):
        raw_gps = entry.get("raw_gps", "")
        distances = [entry.get("distance_1", "N/A"), entry.get("distance_2", "N/A"), entry.get("distance_3", "N/A")]
        gprmc_sentence = extract_gprmc_sentence(raw_gps)
        if gprmc_sentence:
            lat, lon = parse_nmea(gprmc_sentence)
            if lat is not None and lon is not None:
                locations.append({"lat": lat, "lon": lon, "distances": distances})

# Flask route to serve pothole data
@app.route("/")
def index():
    return "Pothole Detection API is running!"

@app.route("/data")
def get_pothole_data():
    return jsonify(locations)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
