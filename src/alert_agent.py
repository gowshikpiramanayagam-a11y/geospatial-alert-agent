import os
import sys
import csv
import json
import math
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (for local VS Code runs)
load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
HOURS_BACK = int(os.getenv("HOURS_BACK", "24"))          # How far back to check
MIN_MAGNITUDE = float(os.getenv("MIN_MAGNITUDE", "3.0"))  # Minimum earthquake magnitude
ASSETS_FILE = Path(__file__).parent.parent / "data" / "assets.csv"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Email config (reads from environment variables / GitHub Secrets)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


# ---------------------------------------------------------------------------
# SPATIAL ANALYSIS: Haversine Formula (Point-to-Point Distance)
# This is the core of our "spatial join" — we calculate the great-circle
# distance between each asset and each earthquake epicenter.
# ---------------------------------------------------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    R = 6371.0  # Earth radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# ---------------------------------------------------------------------------
# DATA FETCHING: USGS Earthquake API (100% Free, No API Key Required)
# ---------------------------------------------------------------------------
def fetch_earthquakes(hours=24, min_magnitude=3.0):
    """
    Fetch recent earthquake data from the USGS public API.
    USGS does not require an API key — completely free.
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": min_magnitude,
        "orderby": "time"
    }

    print(f"   🌐 Calling USGS API: {url}")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()  # Stop if the API returns an error

    data = response.json()
    return data


# ---------------------------------------------------------------------------
# ASSET MANAGEMENT: Load your facilities / infrastructure from CSV
# ---------------------------------------------------------------------------
def load_assets(filepath=ASSETS_FILE):
    """
    Load asset locations from a CSV file.
    Expected columns: name, latitude, longitude, buffer_km, email
    """
    assets = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assets.append({
                "name": row["name"].strip(),
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "buffer_km": float(row["buffer_km"]),
                "email": row["email"].strip()
            })
    return assets


# ---------------------------------------------------------------------------
# SPATIAL JOIN: Match earthquakes to assets within buffer distance
# ---------------------------------------------------------------------------
def spatial_join(earthquake_data, assets):
    """
    Perform a spatial join:
    For each asset, find all earthquakes within its buffer radius.
    Returns a list of alert dictionaries.
    """
    features = earthquake_data.get("features", [])
    alerts = []

    for asset in assets:
        nearby_earthquakes = []

        for eq in features:
            props = eq["properties"]
            coords = eq["geometry"]["coordinates"]
            eq_lon, eq_lat = coords[0], coords[1]

            # CORE SPATIAL OPERATION
            distance_km = haversine_distance(
                asset["lat"], asset["lon"], eq_lat, eq_lon
            )

            if distance_km <= asset["buffer_km"]:
                nearby_earthquakes.append({
                    "place": props.get("place", "Unknown location"),
                    "magnitude": props.get("mag"),
                    "time_utc": datetime.fromtimestamp(
                        props.get("time", 0) / 1000, tz=timezone.utc
                    ).isoformat(),
                    "distance_km": round(distance_km, 2),
                    "coordinates": [eq_lat, eq_lon],
                    "details_url": props.get("url"),
                    "alert_level": "HIGH" if props.get("mag", 0) >= 6.0 else "MODERATE"
                })

        if nearby_earthquakes:
            # Sort by closest distance first
            nearby_earthquakes.sort(key=lambda x: x["distance_km"])
            alerts.append({
                "asset": asset,
                "earthquakes": nearby_earthquakes,
                "total_threats": len(nearby_earthquakes)
            })

    return alerts


# ---------------------------------------------------------------------------
# ALERTING: Send email notifications via SMTP (Gmail, Outlook, etc.)
# ---------------------------------------------------------------------------
def send_alert_email(asset, earthquakes):
    """
    Send an HTML email alert for a specific asset.
    Works with Gmail, Outlook, Yahoo, or any SMTP provider.
    """
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        print(f"   ⚠️  No email credentials found. Skipping email for {asset['name']}.")
        return False

    subject = f"🚨 GEO-ALERT: {len(earthquakes)} earthquake(s) near {asset['name']}"

    # Build HTML email body
    rows = ""
    for eq in earthquakes:
        rows += f"""
        <tr>
            <td style="padding:10px;border:1px solid #ddd;">{eq['magnitude']}</td>
            <td style="padding:10px;border:1px solid #ddd;">{eq['place']}</td>
            <td style="padding:10px;border:1px solid #ddd;">{eq['distance_km']} km</td>
            <td style="padding:10px;border:1px solid #ddd;">{eq['alert_level']}</td>
            <td style="padding:10px;border:1px solid #ddd;"><a href="{eq['details_url']}">Details</a></td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
        <h2 style="color:#d9534f;">🌍 Geospatial Alert Notification</h2>
        <p><strong>Asset:</strong> {asset['name']}</p>
        <p><strong>Asset Location:</strong> {asset['lat']}, {asset['lon']}</p>
        <p><strong>Alert Buffer:</strong> {asset['buffer_km']} km</p>
        <hr>
        <h3>Threat Summary</h3>
        <p>{len(earthquakes)} earthquake(s) detected within your buffer zone:</p>
        <table style="border-collapse:collapse;width:100%;max-width:700px;">
            <tr style="background:#f2f2f2;">
                <th style="padding:10px;border:1px solid #ddd;">Magnitude</th>
                <th style="padding:10px;border:1px solid #ddd;">Location</th>
                <th style="padding:10px;border:1px solid #ddd;">Distance</th>
                <th style="padding:10px;border:1px solid #ddd;">Level</th>
                <th style="padding:10px;border:1px solid #ddd;">Link</th>
            </tr>
            {rows}
        </table>
        <hr>
        <p style="font-size:12px;color:#777;">
            Generated by <em>Real-Time Geospatial Alerting Agent</em><br>
            Timestamp (UTC): {datetime.utcnow().isoformat()}
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USERNAME
    msg["To"] = asset["email"]
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USERNAME, asset["email"], msg.as_string())
        server.quit()
        print(f"   ✅ Email alert sent to {asset['email']} for {asset['name']}")
        return True
    except Exception as e:
        print(f"   ❌ Email failed: {e}")
        return False


# ---------------------------------------------------------------------------
# REPORTING: Save JSON logs for audit trail and portfolio proof
# ---------------------------------------------------------------------------
def save_log(alerts, total_earthquakes):
    """Save a timestamped JSON log of this run."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"alert_run_{timestamp}.json"

    log_data = {
        "run_timestamp_utc": datetime.utcnow().isoformat(),
        "total_earthquakes_checked": total_earthquakes,
        "assets_at_risk": len(alerts),
        "alerts": alerts
    }

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

    print(f"   💾 Log saved: {log_file.name}")
    return log_file


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------
def main():
    print("\n" + "=" * 60)
    print("🌍 REAL-TIME GEOSPATIAL ALERTING AGENT")
    print("=" * 60)

    if TEST_MODE:
        print("🧪 TEST MODE ENABLED — No emails will actually be sent.\n")

    # STEP 1: Fetch live earthquake data
    print("\n📡 STEP 1: Fetching live earthquake data from USGS...")
    try:
        quake_data = fetch_earthquakes(hours=HOURS_BACK, min_magnitude=MIN_MAGNITUDE)
        features = quake_data.get("features", [])
        print(f"   ✔ Retrieved {len(features)} earthquake(s) in last {HOURS_BACK}h (mag ≥ {MIN_MAGNITUDE})")
    except Exception as e:
        print(f"   ❌ Failed to fetch earthquake data: {e}")
        sys.exit(1)

    # STEP 2: Load asset inventory
    print("\n🏭 STEP 2: Loading asset inventory...")
    try:
        assets = load_assets()
        print(f"   ✔ Loaded {len(assets)} asset(s) from assets.csv")
    except Exception as e:
        print(f"   ❌ Failed to load assets: {e}")
        sys.exit(1)

    # STEP 3: Spatial Join (the GIS magic)
    print("\n🔍 STEP 3: Performing spatial join (distance analysis)...")
    alerts = spatial_join(quake_data, assets)
    print(f"   ✔ {len(alerts)} asset(s) are within threat range!")

    # STEP 4: Send alerts
    print("\n📧 STEP 4: Sending alert notifications...")
    emails_sent = 0
    for alert in alerts:
        asset = alert["asset"]
        eqs = alert["earthquakes"]

        if TEST_MODE:
            print(f"   🧪 [TEST] Would email {asset['email']} about {len(eqs)} quake(s) near {asset['name']}")
            emails_sent += 1
        else:
            success = send_alert_email(asset, eqs)
            if success:
                emails_sent += 1

    # STEP 5: Save audit log
    print("\n📊 STEP 5: Saving audit log...")
    save_log(alerts, len(features))

    # Final summary
    print("\n" + "=" * 60)
    print("✅ AGENT RUN COMPLETE")
    print(f"   Earthquakes checked : {len(features)}")
    print(f"   Assets monitored    : {len(assets)}")
    print(f"   Assets at risk      : {len(alerts)}")
    print(f"   Alerts sent         : {emails_sent}")
    print("=" * 60 + "\n")


# Needed for timezone-aware timestamps in logs
from datetime import timezone

if __name__ == "__main__":
    main()
