import requests
import pynmea2
import json
import re

# Firebase details
FIREBASE_HOST = "https://potholedetection-68439-default-rtdb.firebaseio.com"
FIREBASE_AUTH = "Gy7GEvivFGwEXfTEZkTL7dzz7mEs5D191FS40vfE"

# Fetch data from Firebase
url = f"{FIREBASE_HOST}/.json?auth={FIREBASE_AUTH}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print("✅ Data fetched from Firebase successfully!\n")
else:
    print("❌ Failed to retrieve data:", response.status_code, response.text)
    exit()

# 🔥 Ensure "sensor_data" exists
if "sensor_data" not in data:
    print("❌ 'sensor_data' not found in Firebase!")
    exit()

sensor_data = data["sensor_data"]

# Function to clean and extract valid $GPRMC sentence
def extract_gprmc_sentence(nmea_string):
    if not nmea_string:
        return None

    # Remove non-printable characters and unexpected spaces
    clean_nmea = re.sub(r'[^\x20-\x7E]', '', nmea_string).strip()

    # Debugging: Print cleaned GPS string
    print(f"🔍 Cleaned NMEA Data: {repr(clean_nmea)}")

    # Find the last $GPRMC sentence (ensures complete sentence)
    matches = re.findall(r'(\$GPRMC,[^\r\n]*)', clean_nmea)

    if matches:
        last_sentence = matches[-1]

        # Ensure it has at least 11 comma-separated values (valid structure)
        if last_sentence.count(',') >= 11:
            print(f"✅ Valid $GPRMC Found: {last_sentence}")
            return last_sentence
        else:
            print(f"⚠ Ignoring incomplete $GPRMC: {last_sentence}")

    return None

# Function to parse NMEA GPS data
def parse_nmea(nmea_string):
    try:
        if not nmea_string:
            return None, None

        msg = pynmea2.parse(nmea_string)

        print(f"✅ Parsed NMEA Sentence: {msg}")  # Debugging output

        if isinstance(msg, pynmea2.types.talker.RMC):  # RMC contains lat/lon
            latitude = convert_latitude(msg.lat, msg.lat_dir)
            longitude = convert_longitude(msg.lon, msg.lon_dir)
            return latitude, longitude
    except pynmea2.ParseError as e:
        print(f"❌ NMEA Parse Error: {e} → {nmea_string}")
        return None, None
    return None, None

# Convert latitude from NMEA format to decimal degrees
def convert_latitude(lat_str, direction):
    if not lat_str:
        return None
    try:
        degrees = float(lat_str[:2])
        minutes = float(lat_str[2:]) / 60
        latitude = degrees + minutes
        if direction == "S":
            latitude = -latitude
        return latitude
    except ValueError:
        return None

# Convert longitude from NMEA format to decimal degrees
def convert_longitude(lon_str, direction):
    if not lon_str:
        return None
    try:
        degrees = float(lon_str[:3])
        minutes = float(lon_str[3:]) / 60
        longitude = degrees + minutes
        if direction == "W":
            longitude = -longitude
        return longitude
    except ValueError:
        return None

# Process and extract GPS locations
locations = []
skipped_entries = 0  # Count skipped entries for debugging

for key, entry in sensor_data.items():  # 🔥 Loop through "sensor_data" correctly
    if isinstance(entry, dict):
        raw_gps = entry.get("raw_gps", "")
        distance_1 = entry.get("distance_1", "N/A")
        distance_2 = entry.get("distance_2", "N/A")
        distance_3 = entry.get("distance_3", "N/A")

        # Debugging: Print raw GPS before cleaning
        print(f"\n🔍 Raw GPS for {key}: {repr(raw_gps)}")

        # Extract a valid $GPRMC sentence
        gprmc_sentence = extract_gprmc_sentence(raw_gps)

        if not gprmc_sentence:
            print(f"❌ Skipping {key}: No valid $GPRMC data found!\n")
            skipped_entries += 1
            continue

        print(f"🔍 Processing {key}: {gprmc_sentence}")

        lat, lon = parse_nmea(gprmc_sentence)

        if lat is not None and lon is not None:
            locations.append({
                "lat": lat,
                "lon": lon,
                "distances": [distance_1, distance_2, distance_3]
            })
        else:
            print(f"⚠ GPS data in {key} could not be parsed!")
            skipped_entries += 1

# Save locations to a JSON file
if locations:
    with open("pothole_data.json", "w") as f:
        json.dump(locations, f, indent=4)
    print("\n✅ Pothole data saved as 'pothole_data.json'! Use it in the web app.")
else:
    print("\n❌ No valid GPS data found. Nothing saved.")

# Print skipped data count
print(f"\nℹ Skipped Entries: {skipped_entries} (Check logs for details)")
